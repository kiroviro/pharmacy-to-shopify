"""
CSV Utilities

Common functions for reading and writing CSV files with proper configuration.
Handles large field sizes and encoding issues.
"""

import csv
from typing import Dict, List, Iterator, Optional
from pathlib import Path


def configure_csv(field_size_limit: int = 10 * 1024 * 1024) -> None:
    """
    Configure CSV module for large fields.

    Args:
        field_size_limit: Maximum field size in bytes (default: 10MB)
    """
    csv.field_size_limit(field_size_limit)


def read_csv(file_path: str | Path, encoding: str = 'utf-8') -> Iterator[Dict[str, str]]:
    """
    Read CSV file and yield rows as dictionaries.

    Args:
        file_path: Path to CSV file
        encoding: File encoding (default: utf-8)

    Yields:
        Dictionary for each row with column names as keys
    """
    configure_csv()

    with open(file_path, 'r', encoding=encoding) as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def write_csv(
    file_path: str | Path,
    rows: List[Dict[str, str]],
    fieldnames: Optional[List[str]] = None,
    encoding: str = 'utf-8'
) -> int:
    """
    Write rows to CSV file.

    Args:
        file_path: Path to output CSV file
        rows: List of dictionaries to write
        fieldnames: Column names (if None, uses keys from first row)
        encoding: File encoding (default: utf-8)

    Returns:
        Number of rows written
    """
    if not rows:
        return 0

    if fieldnames is None:
        fieldnames = list(rows[0].keys())

    with open(file_path, 'w', encoding=encoding, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def count_rows(file_path: str | Path) -> int:
    """
    Count rows in CSV file (excluding header).

    Args:
        file_path: Path to CSV file

    Returns:
        Number of data rows
    """
    count = 0
    for _ in read_csv(file_path):
        count += 1
    return count


# Initialize CSV configuration on module import
configure_csv()
