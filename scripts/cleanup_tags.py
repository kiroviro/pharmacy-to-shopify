#!/usr/bin/env python3
"""
Tag Cleanup Script for Shopify Products CSV

Post-processes a Shopify products CSV to:
1. Normalize tag casing (fix case-sensitivity duplicates)
2. Remove brand names from tags (they're already in Vendor field)
3. Assign missing L1 category tags based on subcategory inference
4. Remove promotional/temporal tags

Usage:
    python3 cleanup_tags.py --input output/products.csv --output output/products_cleaned.csv
    python3 cleanup_tags.py --input output/products.csv --output output/products_cleaned.csv --report output/cleanup_report.txt
"""

import argparse
import logging
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cleanup import TagCleaner
from src.common.log_config import setup_logging

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Clean and normalize tags in Shopify products CSV"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input CSV file path"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output CSV file path"
    )
    parser.add_argument(
        "--report", "-r",
        default=None,
        help="Optional: Path to write detailed cleanup report"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info messages, show only warnings and errors"
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    # Validate input exists
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    print("=" * 60)
    print("Tag Cleanup Script")
    print("=" * 60)
    print(f"  Input:  {args.input}")
    print(f"  Output: {args.output}")
    if args.report:
        print(f"  Report: {args.report}")

    # Run cleanup
    cleaner = TagCleaner(
        input_path=args.input,
        output_path=args.output,
        report_path=args.report
    )
    cleaner.process()


if __name__ == "__main__":
    main()
