"""
CSV Utilities

Configures the csv module for large field sizes and provides helpers
for reading Shopify-format product CSVs.
"""

from __future__ import annotations

import csv
from collections.abc import Generator
from typing import Any


def configure_csv(field_size_limit: int = 10 * 1024 * 1024) -> None:
    """
    Configure CSV module for large fields.

    Args:
        field_size_limit: Maximum field size in bytes (default: 10MB)
    """
    csv.field_size_limit(field_size_limit)


def iter_product_rows(csv_path: str) -> Generator[dict[str, Any], None, None]:
    """
    Yield only product rows from a Shopify-format products CSV.

    Shopify CSVs contain both product rows (with a Title) and image-only
    continuation rows (empty Title). This generator yields only the former.

    Args:
        csv_path: Path to the Shopify products CSV file.

    Yields:
        Dict rows where the Title column is non-empty.
    """
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Title", "").strip():
                yield row


# Initialize CSV configuration on module import
configure_csv()
