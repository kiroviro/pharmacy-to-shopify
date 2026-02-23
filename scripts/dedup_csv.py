#!/usr/bin/env python3
"""
Deduplicate a products CSV by SKU.

Two-pass strategy:
1. Expiry-aware: if multiple rows share a SKU and any title contains a
   "Годен до: DD.MM.YYYY г." suffix, keep only the row WITHOUT the suffix
   (or the latest expiry date if all rows have it).
2. True-duplicate: for remaining duplicate SKUs, keep the first occurrence.

Usage:
    python scripts/dedup_csv.py data/benu.bg/processed/products_cleaned.csv
    python scripts/dedup_csv.py data/benu.bg/processed/products_cleaned.csv \\
        --output data/benu.bg/processed/products_deduped.csv
    python scripts/dedup_csv.py data/benu.bg/processed/products_cleaned.csv --dry-run
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

# Matches "Годен до: 30.04.2026 г." (day and month may be 1-2 digits)
EXPIRY_PATTERN = re.compile(r"Годен до:\s*\d{1,2}\.\d{1,2}\.\d{4}\s*г\.")

# Extracts the date portion for sorting (group 1 = DD, 2 = MM, 3 = YYYY)
_DATE_PATTERN = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


def is_expiry_variant(title: str) -> bool:
    """Return True if the title contains a 'Годен до:' expiry suffix."""
    return bool(EXPIRY_PATTERN.search(title))


def _expiry_sort_key(title: str) -> tuple[int, int, int]:
    """Parse expiry date from title for sorting (latest date = highest key)."""
    m = _DATE_PATTERN.search(title)
    if not m:
        return (0, 0, 0)
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return (year, month, day)


def dedup_csv(input_path: str, output_path: str | None = None) -> dict:
    """
    Deduplicate a products CSV by SKU.

    Args:
        input_path: Path to the input CSV file.
        output_path: Path to write deduplicated output. If None, output is not
                     written (useful for dry-run / stats-only calls).

    Returns:
        Stats dict with keys:
            total            — total rows with a non-empty Title
            kept             — rows written to output
            removed          — rows removed (expiry_removed + true_dupes_removed)
            expiry_removed   — rows removed as near-expiry variants
            true_dupes_removed — rows removed as true duplicates
    """
    with open(input_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        all_rows = list(reader)

    # Split into title rows (products) and non-title rows (variant image rows etc.)
    product_rows = [r for r in all_rows if r.get("Title", "").strip()]
    non_product_rows = [r for r in all_rows if not r.get("Title", "").strip()]

    # ── Pass 1: expiry-aware deduplication ────────────────────────────────────
    # Group product rows by SKU
    sku_groups: dict[str, list[dict]] = {}
    no_sku_rows: list[dict] = []

    for row in product_rows:
        sku = row.get("SKU", "").strip()
        if not sku:
            no_sku_rows.append(row)
        else:
            sku_groups.setdefault(sku, []).append(row)

    expiry_removed = 0
    after_pass1: list[dict] = list(no_sku_rows)

    for sku, rows in sku_groups.items():
        if len(rows) == 1:
            after_pass1.append(rows[0])
            continue

        # Check if any row in this group has an expiry suffix
        expiry_rows = [r for r in rows if is_expiry_variant(r.get("Title", ""))]
        base_rows = [r for r in rows if not is_expiry_variant(r.get("Title", ""))]

        if expiry_rows and base_rows:
            # Keep only the base (non-expiry) rows; discard expiry variants
            after_pass1.extend(base_rows)
            expiry_removed += len(expiry_rows)
        elif expiry_rows and not base_rows:
            # All rows are expiry variants — keep the one with the latest date
            expiry_rows.sort(key=lambda r: _expiry_sort_key(r.get("Title", "")), reverse=True)
            after_pass1.append(expiry_rows[0])
            expiry_removed += len(expiry_rows) - 1
        else:
            # No expiry variants in this group; pass through for dedup in pass 2
            after_pass1.extend(rows)

    # ── Pass 2: true-duplicate deduplication (keep first occurrence) ──────────
    seen_skus: set[str] = set()
    true_dupes_removed = 0
    after_pass2: list[dict] = []

    for row in after_pass1:
        sku = row.get("SKU", "").strip()
        if not sku or sku not in seen_skus:
            after_pass2.append(row)
            if sku:
                seen_skus.add(sku)
        else:
            true_dupes_removed += 1

    # Reassemble: deduplicated product rows + original non-product rows
    output_rows = after_pass2 + non_product_rows

    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

    total = len(product_rows)
    removed = expiry_removed + true_dupes_removed
    return {
        "total": total,
        "kept": total - removed,
        "removed": removed,
        "expiry_removed": expiry_removed,
        "true_dupes_removed": true_dupes_removed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deduplicate a products CSV by SKU.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Input CSV file path")
    parser.add_argument(
        "--output", "-o",
        help="Output CSV path (default: <input>_deduped.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats without writing output file",
    )
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        output_path = None
    else:
        if args.output:
            output_path = args.output
        else:
            p = Path(args.input)
            output_path = str(p.parent / f"{p.stem}_deduped{p.suffix}")

    stats = dedup_csv(args.input, output_path)

    print(f"Input:              {args.input}")
    print(f"Total products:     {stats['total']:,}")
    print(f"Kept:               {stats['kept']:,}")
    print(f"Removed (total):    {stats['removed']:,}")
    print(f"  Expiry variants:  {stats['expiry_removed']:,}")
    print(f"  True duplicates:  {stats['true_dupes_removed']:,}")

    if output_path:
        print(f"\nOutput written to:  {output_path}")
    else:
        print("\n(dry run — no output written)")


if __name__ == "__main__":
    main()
