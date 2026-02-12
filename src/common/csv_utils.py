"""
CSV Utilities

Configures the csv module for large field sizes.
"""

from __future__ import annotations

import csv


def configure_csv(field_size_limit: int = 10 * 1024 * 1024) -> None:
    """
    Configure CSV module for large fields.

    Args:
        field_size_limit: Maximum field size in bytes (default: 10MB)
    """
    csv.field_size_limit(field_size_limit)


# Initialize CSV configuration on module import
configure_csv()
