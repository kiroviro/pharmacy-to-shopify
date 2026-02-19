#!/usr/bin/env python3
"""
Bulk Product Extraction Script

Extracts products from a list of URLs and outputs a combined Shopify CSV.
Site is auto-detected from URLs.

Features:
- Progress tracking with resume capability
- Error handling with failed URL tracking
- Rate limiting for respectful crawling
- Combined CSV output for Shopify import
- Optional automatic export to Shopify-ready format

Usage:
    python3 bulk_extract.py --urls data/pharmacy.example.com/raw/urls.txt
    python3 bulk_extract.py --urls data/pharmacy.example.com/raw/urls.txt --limit 100
    python3 bulk_extract.py --urls urls.txt --output products.csv --resume
    python3 bulk_extract.py --urls urls.txt --export-shopify  # Auto-export after extraction
"""

import argparse
import logging
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.cleanup import DEFAULT_MAX_SIZE_MB, BrandExporter
from src.common.log_config import setup_logging
from src.extraction import (
    BulkExtractor,
    get_extractor_for_url,
    get_site_from_url,
)

logger = logging.getLogger(__name__)


def detect_site_from_urls(urls: list) -> str:
    """Detect site from the first valid URL."""
    for url in urls:
        if url.strip():
            return get_site_from_url(url)
    raise ValueError("No valid URLs found in input file")


def export_to_shopify(
    input_csv: str,
    output_dir: str = "output/shopify",
    max_size_mb: float = DEFAULT_MAX_SIZE_MB,
) -> None:
    """
    Export extracted products to Shopify-ready format with file splitting.

    Args:
        input_csv: Path to the raw products CSV file
        output_dir: Directory to write Shopify-ready CSV files (default: output/shopify)
        max_size_mb: Maximum file size in MB (default: 14MB)
    """
    logger.info("Starting Shopify export from %s", input_csv)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create exporter
    exporter = BrandExporter(
        input_csv=input_csv,
        images_dir="output/images",  # Not used when copy_images=False
        max_size_mb=max_size_mb,
    )

    # Export all brands with auto-splitting
    output_csv = os.path.join(output_dir, "products.csv")
    exporter.export(
        brands_to_include=None,
        brands_to_exclude=None,
        top_n=None,
        output_csv=output_csv,
        copy_images=False,  # Skip image copying (using remote URLs)
        all_brands=True,
    )

    logger.info("Shopify export complete. Files ready in: %s", output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Bulk extract products (site auto-detected from URLs)"
    )
    parser.add_argument(
        "--urls", "-u",
        required=True,
        help="Input file with product URLs (one per line)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output CSV file (default: data/{site}/raw/products.csv)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=0,
        help="Limit number of products to extract (0 = no limit)"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous extraction state"
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop extraction if any product fails (default: continue on error)"
    )
    parser.add_argument(
        "--save-failed-html",
        action="store_true",
        help="Save HTML of failed pages for debugging"
    )
    parser.add_argument(
        "--export-shopify",
        action="store_true",
        help="Automatically export to Shopify-ready format after extraction"
    )
    parser.add_argument(
        "--shopify-output-dir",
        default="output/shopify",
        help="Directory for Shopify export files (default: output/shopify)"
    )
    parser.add_argument(
        "--max-size",
        type=float,
        default=DEFAULT_MAX_SIZE_MB,
        help=f"Max file size in MB for Shopify export (default: {DEFAULT_MAX_SIZE_MB})"
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

    # Read URLs from file
    if not os.path.exists(args.urls):
        print(f"URL file not found: {args.urls}")
        sys.exit(1)

    with open(args.urls, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        logger.error("No URLs found in input file")
        sys.exit(1)

    # Auto-detect site from URLs
    site = detect_site_from_urls(urls)

    # Set default output path based on site
    output_csv = args.output or f"data/{site}/raw/products.csv"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    # Get appropriate extractor class
    ExtractorClass = get_extractor_for_url(urls[0])

    print("=" * 60)
    print("Bulk Product Extraction")
    print("=" * 60)
    print(f"  Site:             {site}")
    print(f"  Input file:       {args.urls}")
    print(f"  Total URLs:       {len(urls)}")
    print(f"  Output CSV:       {output_csv}")
    print(f"  Request delay:    {args.delay}s")
    print(f"  Resume mode:      {args.resume}")
    print(f"  Extractor:        {ExtractorClass.__name__}")
    if args.export_shopify:
        print(f"  Export to Shopify: YES")
        print(f"  Shopify output:   {args.shopify_output_dir}")
        print(f"  Max file size:    {args.max_size}MB")

    # Create bulk extractor
    extractor = BulkExtractor(
        output_csv=output_csv,
        delay=args.delay,
        save_failed_html=args.save_failed_html,
        source_domain=site,
    )

    # Run extraction
    extractor.extract_all(
        urls=urls,
        extractor_class=ExtractorClass,
        limit=args.limit,
        resume=args.resume,
        continue_on_error=not args.stop_on_error,
    )

    logger.info("Extraction complete. Output: %s", output_csv)

    # Optional: Export to Shopify-ready format
    if args.export_shopify:
        print("\n" + "=" * 60)
        print("Exporting to Shopify-Ready Format")
        print("=" * 60)
        try:
            export_to_shopify(
                input_csv=output_csv,
                output_dir=args.shopify_output_dir,
                max_size_mb=args.max_size,
            )
            print("\n✅ Complete! Shopify import files ready at:")
            print(f"   {args.shopify_output_dir}/")
        except Exception as e:
            logger.error("Shopify export failed: %s", e)
            print(f"\n❌ Shopify export failed: {e}")
            print("You can manually export later using:")
            print(f"   python3 scripts/export_by_brand.py --all-brands --input {output_csv}")
            sys.exit(1)


if __name__ == "__main__":
    main()
