"""
CrawlQualityTracker

Tracks data quality metrics across the whole crawl and prints summaries.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import ExtractedProduct


class CrawlQualityTracker:
    """
    Aggregate quality tracker for a bulk extraction run.

    Records per-product validation results, detects duplicate handles,
    tracks price outliers, and prints periodic and final quality reports.

    Usage::

        tracker = CrawlQualityTracker()
        # inside extraction loop:
        result = SpecificationValidator(product).validate()
        tracker.record(product, result)
        tracker.print_periodic_summary(n_processed)
        # after loop:
        tracker.print_final_report()
        if tracker.has_critical_failures():
            sys.exit(1)
    """

    def __init__(self) -> None:
        self.total: int = 0
        self.valid: int = 0          # no errors
        self.warnings_only: int = 0  # warnings but no errors
        self.errors: int = 0         # at least one error

        # Per-field error counter: field_name -> count
        self.field_error_counts: dict[str, int] = defaultdict(int)

        # Duplicate handle and SKU tracking
        self.seen_handles: set[str] = set()
        self.duplicate_handles: list[str] = []
        self.seen_skus: set[str] = set()
        self.duplicate_skus: list[str] = []

        # Price range tracking
        self.price_min: float | None = None
        self.price_max: float | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def record(self, product: "ExtractedProduct", validation_result: dict) -> None:
        """Record a product's validation result."""
        self.total += 1

        errs = validation_result.get("errors", [])
        warns = validation_result.get("warnings", [])

        if errs:
            self.errors += 1
        elif warns:
            self.warnings_only += 1
        else:
            self.valid += 1

        # Tally per-field issues by extracting the field name prefix.
        # Errors and warnings are both counted so that consistency_* warnings
        # (which are never blocking) still appear in the per-field report.
        for msg in errs + warns:
            field = self._extract_field(msg)
            self.field_error_counts[field] += 1

        # Duplicate handle detection
        if product.handle:
            if product.handle in self.seen_handles:
                self.duplicate_handles.append(product.handle)
                self.field_error_counts["handle_duplicate"] += 1
            else:
                self.seen_handles.add(product.handle)

        # Duplicate SKU detection
        if product.sku:
            if product.sku in self.seen_skus:
                self.duplicate_skus.append(product.sku)
                self.field_error_counts["sku_duplicate"] += 1
            else:
                self.seen_skus.add(product.sku)

        # Price outlier tracking
        try:
            price_f = float(product.price)
            if self.price_min is None or price_f < self.price_min:
                self.price_min = price_f
            if self.price_max is None or price_f > self.price_max:
                self.price_max = price_f
        except (ValueError, TypeError):
            pass

    def print_periodic_summary(self, n_processed: int) -> None:
        """Print a one-line quality summary (call every 100 products)."""
        if self.total == 0:
            return

        valid_pct = self.valid / self.total * 100
        warn_pct = self.warnings_only / self.total * 100
        err_pct = self.errors / self.total * 100

        top_issues = self._top_issues(n=3)
        top_str = ", ".join(f"{f} ({c})" for f, c in top_issues) if top_issues else "none"

        print(
            f"[Progress {n_processed}] Quality: "
            f"✅ {valid_pct:.1f}% valid | "
            f"⚠️  {warn_pct:.1f}% warnings | "
            f"❌ {err_pct:.1f}% errors"
        )
        if top_issues:
            print(f"  Top issues: {top_str}")

    def print_final_report(self) -> None:
        """Print a full quality report table at the end of the crawl."""
        if self.total == 0:
            print("\n[Quality] No products processed.")
            return

        valid_pct = self.valid / self.total * 100
        warn_pct = self.warnings_only / self.total * 100
        err_pct = self.errors / self.total * 100
        gate = "PASS" if not self.has_critical_failures() else "FAIL"

        print("\n" + "=" * 60)
        print(f"Quality Report  [{gate}]")
        print("=" * 60)
        print(f"  Total products:   {self.total}")
        print(f"  Valid (no issues):{self.valid:>6}  ({valid_pct:.1f}%)")
        print(f"  Warnings only:    {self.warnings_only:>6}  ({warn_pct:.1f}%)")
        print(f"  Errors:           {self.errors:>6}  ({err_pct:.1f}%)")

        if self.field_error_counts:
            print("\n  Per-field failure rates (top 10):")
            for field, count in sorted(
                self.field_error_counts.items(), key=lambda x: -x[1]
            )[:10]:
                pct = count / self.total * 100
                print(f"    {field:<30} {count:>5}  ({pct:.1f}%)")

        if self.duplicate_handles:
            print(
                f"\n  Duplicate handles: {len(self.duplicate_handles)} "
                f"(e.g. {self.duplicate_handles[0]!r})"
            )

        if self.duplicate_skus:
            print(
                f"  Duplicate SKUs:    {len(self.duplicate_skus)} "
                f"(e.g. {self.duplicate_skus[0]!r})"
            )

        if self.price_min is not None:
            print(
                f"\n  Price range: {self.price_min:.2f} – {self.price_max:.2f} BGN"
            )

        print("\n  Gate (>5% errors = FAIL):", gate)
        print("=" * 60)

    def has_critical_failures(self, threshold_pct: float = 5.0) -> bool:
        """Return True if the error rate exceeds threshold_pct."""
        if self.total == 0:
            return False
        return (self.errors / self.total * 100) > threshold_pct

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_field(message: str) -> str:
        """Extract the field name from an error message like 'brand: missing'."""
        match = re.match(r"^([a-z_A-Z][a-z_A-Z0-9 ]+?):", message)
        return match.group(1).strip() if match else "unknown"

    def _top_issues(self, n: int = 3) -> list[tuple[str, int]]:
        """Return the top-N fields by error count."""
        return sorted(self.field_error_counts.items(), key=lambda x: -x[1])[:n]
