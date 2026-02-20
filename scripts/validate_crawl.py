#!/usr/bin/env python3
"""
Post-Crawl CSV Validation Script

Validates the raw products CSV produced by bulk_extract.py.
Checks duplicate handles/SKUs, field coverage, price ranges,
image URL quality, and optionally spot-checks live URLs.

Usage:
    python3 scripts/validate_crawl.py --csv data/benu.bg/raw/products.csv
    python3 scripts/validate_crawl.py --csv data/benu.bg/raw/products.csv \\
        --spot-check 100 --report output/validation_report.json

Exit codes:
    0 = PASS (error rate <= 5%)
    1 = FAIL (error rate > 5% or critical issues found)
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from urllib.parse import urlparse

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.log_config import setup_logging

logger = logging.getLogger(__name__)

# Banned image domain suffixes — matches exact hostname AND all subdomains.
# Mirrors the same logic as src/extraction/validator._is_placeholder_domain().
_PLACEHOLDER_DOMAIN_SUFFIXES = frozenset({
    "example.com",      # catches pharmacy.example.com (commit a9b6d3b regression)
    "placeholder.com",  # catches via.placeholder.com
    "dummyimage.com",
    "placehold.it",
    "placekitten.com",
    "lorempixel.com",
    "localhost",
})


def _is_placeholder_domain(hostname: str) -> bool:
    h = hostname.lower()
    return any(h == d or h.endswith("." + d) for d in _PLACEHOLDER_DOMAIN_SUFFIXES)

# BGN/EUR fixed exchange rate
_EUR_TO_BGN = 1.95583


def read_products_from_csv(csv_path: str) -> list[dict]:
    """Read rows with a non-empty Title from the CSV."""
    products = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Title", "").strip():
                products.append(row)
    return products


def check_duplicate_handles(products: list[dict]) -> list[str]:
    """Return list of handle values that appear more than once."""
    counts = Counter(p.get("URL handle", "") for p in products if p.get("URL handle", ""))
    return [h for h, c in counts.items() if c > 1]


def check_duplicate_skus(products: list[dict]) -> list[str]:
    """Return list of SKU values that appear more than once."""
    counts = Counter(p.get("SKU", "") for p in products if p.get("SKU", ""))
    return [s for s, c in counts.items() if c > 1]


def check_image_url(url: str) -> str | None:
    """Return an issue description if the image URL is invalid, else None."""
    if not url:
        return "empty image URL"
    if not url.startswith("https://"):
        return f"image URL not https: {url[:60]!r}"
    try:
        hostname = urlparse(url).netloc.lower()
        if _is_placeholder_domain(hostname):
            return f"placeholder image domain: {hostname}"
    except Exception:
        pass
    return None


def validate_row(row: dict) -> list[str]:
    """Run field-level checks on a CSV row. Returns list of issue strings."""
    issues = []

    # Title
    title = row.get("Title", "")
    if not title.strip():
        issues.append("title: empty")
    elif len(title) < 5:
        issues.append(f"title: too short ({len(title)} chars)")
    elif len(title) > 250:
        issues.append(f"title: too long ({len(title)} chars)")

    # Handle
    handle = row.get("URL handle", "")
    if not handle:
        issues.append("handle: missing")
    elif not re.fullmatch(r"[a-z0-9-]+", handle):
        issues.append(f"handle: invalid format ({handle!r})")
    elif len(handle) > 200:
        issues.append(f"handle: too long ({len(handle)} chars)")

    # Price
    price_str = row.get("Price", "")
    price_float = None
    if not price_str:
        issues.append("price: missing")
    else:
        try:
            price_float = float(price_str)
            if price_float <= 0:
                issues.append(f"price: <= 0 (got {price_float})")
            elif price_float >= 10000:
                issues.append(f"price: suspiciously high ({price_float})")
        except (ValueError, TypeError):
            issues.append(f"price: not a number ({price_str!r})")

    # Vendor (brand)
    if not row.get("Vendor", "").strip():
        issues.append("vendor: missing")

    # SKU
    if not row.get("SKU", "").strip():
        issues.append("sku: missing")

    # Product image URL (first image)
    img_issue = check_image_url(row.get("Product image URL", ""))
    if img_issue:
        issues.append(img_issue)

    # Variant Price (should match Price if set)
    variant_price = row.get("Variant Price", "")
    if variant_price and price_float is not None:
        try:
            if abs(float(variant_price) - price_float) > 0.01:
                issues.append(
                    f"variant_price mismatch: Price={price_float}, "
                    f"Variant Price={variant_price}"
                )
        except (ValueError, TypeError):
            pass

    return issues


def spot_check_url(
    url: str, expected_title: str, expected_price: str, expected_vendor: str,
    session: requests.Session, timeout: int = 15
) -> dict:
    """
    Re-fetch a live URL and do basic title/price/vendor comparison.

    Returns a result dict with keys: url, ok, issues.
    """
    result = {"url": url, "ok": True, "issues": []}
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code != 200:
            result["ok"] = False
            result["issues"].append(f"HTTP {resp.status_code}")
            return result

        html = resp.text

        # Title check (case-insensitive substring)
        if expected_title and expected_title.lower() not in html.lower():
            result["ok"] = False
            result["issues"].append(f"title not found in page: {expected_title[:60]!r}")

        # Price check (look for price string in HTML)
        if expected_price:
            price_pattern = re.escape(expected_price.rstrip("0").rstrip("."))
            if not re.search(price_pattern, html):
                result["issues"].append(f"price not found in page: {expected_price!r}")

    except requests.exceptions.Timeout:
        result["ok"] = False
        result["issues"].append("timeout")
    except requests.exceptions.RequestException as e:
        result["ok"] = False
        result["issues"].append(f"request error: {str(e)[:80]}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate raw products CSV from a crawl"
    )
    parser.add_argument("--csv", required=True, help="Path to raw products CSV")
    parser.add_argument(
        "--spot-check",
        type=int,
        default=0,
        metavar="N",
        help="Re-fetch N sampled product URLs for live verification (0 = skip)",
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="Write JSON validation report to this file",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose, quiet=args.quiet)

    if not os.path.exists(args.csv):
        print(f"ERROR: CSV file not found: {args.csv}")
        sys.exit(1)

    print(f"\nValidating: {args.csv}")
    products = read_products_from_csv(args.csv)
    print(f"Product rows (with Title): {len(products)}")

    if not products:
        print("No products found in CSV. Exiting.")
        sys.exit(1)

    # ── Field-level validation ─────────────────────────────────────────────
    row_issues: dict[int, list[str]] = {}
    field_issue_counts: dict[str, int] = defaultdict(int)
    prices: list[float] = []

    for idx, row in enumerate(products):
        issues = validate_row(row)
        if issues:
            row_issues[idx] = issues
            for issue in issues:
                field = issue.split(":")[0]
                field_issue_counts[field] += 1
        try:
            prices.append(float(row.get("Price", "")))
        except (ValueError, TypeError):
            pass

    # ── Duplicate checks ──────────────────────────────────────────────────
    dup_handles = check_duplicate_handles(products)
    dup_skus = check_duplicate_skus(products)

    # ── Coverage rates ────────────────────────────────────────────────────
    coverage: dict[str, float] = {}
    for field_csv in ["Vendor", "SKU", "Product image URL", "URL handle", "Tags"]:
        filled = sum(1 for p in products if p.get(field_csv, "").strip())
        coverage[field_csv] = filled / len(products) * 100

    # ── Summary output ────────────────────────────────────────────────────
    error_count = len(row_issues)
    error_rate = error_count / len(products) * 100

    print("\n" + "=" * 60)
    print("Field Coverage:")
    for field_csv, pct in coverage.items():
        status = "✅" if pct >= 95 else ("⚠️ " if pct >= 80 else "❌")
        print(f"  {status} {field_csv:<20} {pct:.1f}%")

    if prices:
        print(f"\nPrice range: {min(prices):.2f} – {max(prices):.2f} BGN")

    print(f"\nField issue counts (top 10):")
    for field, count in sorted(field_issue_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {field:<30} {count}")

    if dup_handles:
        print(f"\n⚠️  Duplicate handles ({len(dup_handles)}): {dup_handles[:5]}")
    if dup_skus:
        print(f"⚠️  Duplicate SKUs ({len(dup_skus)}): {dup_skus[:5]}")

    print(f"\nProducts with issues: {error_count}/{len(products)} ({error_rate:.1f}%)")

    # ── Spot-check ────────────────────────────────────────────────────────
    spot_results: list[dict] = []
    if args.spot_check > 0:
        sample_size = min(args.spot_check, len(products))
        sample = random.sample(products, sample_size)
        print(f"\nSpot-checking {sample_size} random URLs...")

        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (validation-bot/1.0)"})

        spot_failures = 0
        for i, row in enumerate(sample, 1):
            # Raw CSV doesn't store the source URL; reconstruct from the handle.
            # The URL file has one URL per line that ends with the handle slug.
            handle = row.get("URL handle", "").strip()
            url = f"https://benu.bg/{handle}" if handle else ""
            if not url:
                continue
            res = spot_check_url(
                url=url,
                expected_title=row.get("Title", ""),
                expected_price=row.get("Price", ""),
                expected_vendor=row.get("Vendor", ""),
                session=session,
            )
            spot_results.append(res)
            status = "✅" if res["ok"] else "❌"
            print(f"  [{i}/{sample_size}] {status} {url[:70]}")
            if res["issues"]:
                for issue in res["issues"]:
                    print(f"       {issue}")
            if not res["ok"]:
                spot_failures += 1

            if i < sample_size:
                time.sleep(0.5)

        session.close()
        spot_fail_pct = spot_failures / len(spot_results) * 100 if spot_results else 0
        print(
            f"\nSpot-check: {spot_failures}/{len(spot_results)} failed "
            f"({spot_fail_pct:.1f}%)"
        )

    # ── PASS / FAIL gate ──────────────────────────────────────────────────
    gate_pass = (error_rate <= 5.0) and (not dup_handles) and (not dup_skus)

    print("\n" + "=" * 60)
    print(f"GATE: {'PASS ✅' if gate_pass else 'FAIL ❌'}")
    print(f"  Error rate: {error_rate:.1f}% (threshold: 5%)")
    if dup_handles:
        print(f"  Duplicate handles: {len(dup_handles)}")
    if dup_skus:
        print(f"  Duplicate SKUs: {len(dup_skus)}")
    print("=" * 60)

    # ── JSON report ───────────────────────────────────────────────────────
    if args.report:
        report = {
            "csv": args.csv,
            "total_products": len(products),
            "error_count": error_count,
            "error_rate_pct": round(error_rate, 2),
            "duplicate_handles": dup_handles,
            "duplicate_skus": dup_skus,
            "field_coverage": {k: round(v, 2) for k, v in coverage.items()},
            "field_issue_counts": dict(field_issue_counts),
            "price_min": min(prices) if prices else None,
            "price_max": max(prices) if prices else None,
            "spot_check_results": spot_results,
            "gate_pass": gate_pass,
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport written to: {args.report}")

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
