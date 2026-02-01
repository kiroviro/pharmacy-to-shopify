#!/usr/bin/env python3
"""
Export products by brand for selective Shopify import.

Features:
- List all brands with product counts
- Export products from selected brands only
- Auto-split into multiple files under size limit (default 14MB for Shopify's 15MB limit)
- Keep brands complete (never split a brand across files)
- Copy associated images to separate folder
- Support include/exclude brand lists

Usage:
    # List all brands
    python3 export_by_brand.py --list

    # Export ALL products, auto-split into 14MB chunks
    python3 export_by_brand.py --all-brands --output output/shopify/products.csv

    # Export specific brands
    python3 export_by_brand.py --brands "Nivea,Garnier,Dove" --output output/export.csv

    # Export top N brands by product count
    python3 export_by_brand.py --top 5 --output output/top5.csv

    # Custom max file size (in MB)
    python3 export_by_brand.py --all-brands --output output/shopify/products.csv --max-size 10

    # Exclude specific brands
    python3 export_by_brand.py --all-brands --exclude "(No Brand)" --output output/shopify/products.csv
"""

import argparse
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.cleanup import BrandExporter, DEFAULT_MAX_SIZE_MB

INPUT_CSV = "output/products.csv"
IMAGES_DIR = "output/images"


def main():
    parser = argparse.ArgumentParser(
        description="Export products by brand for selective Shopify import",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all brands
  python3 export_by_brand.py --list

  # Export ALL products, auto-split into 14MB files
  python3 export_by_brand.py --all-brands --output output/shopify/products.csv

  # Export one brand for testing
  python3 export_by_brand.py --brands "Nivea" --output output/test_nivea.csv

  # Export top 3 brands
  python3 export_by_brand.py --top 3 --output output/top3.csv

  # Export specific brands
  python3 export_by_brand.py --brands "Nivea,Garnier,Dove" --output output/selected.csv

  # Export all except certain brands
  python3 export_by_brand.py --all-brands --exclude "(No Brand)" --output output/shopify/products.csv

  # Custom max file size
  python3 export_by_brand.py --all-brands --output output/shopify/products.csv --max-size 10
"""
    )

    parser.add_argument('--list', '-l', action='store_true',
                        help='List all brands with product counts')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Show all brands (with --list)')
    parser.add_argument('--all-brands', action='store_true',
                        help='Export all brands (auto-split into multiple files)')
    parser.add_argument('--brands', '-b', type=str,
                        help='Comma-separated list of brands to include')
    parser.add_argument('--brands-file', '-f', type=str,
                        help='File with brands to include (one per line)')
    parser.add_argument('--exclude', '-e', type=str,
                        help='Comma-separated list of brands to exclude')
    parser.add_argument('--top', '-t', type=int,
                        help='Export top N brands by product count')
    parser.add_argument('--output', '-o', type=str, default='output/export.csv',
                        help='Output CSV file (default: output/export.csv)')
    parser.add_argument('--max-size', '-m', type=float, default=DEFAULT_MAX_SIZE_MB,
                        help=f'Max file size in MB (default: {DEFAULT_MAX_SIZE_MB})')
    parser.add_argument('--no-images', action='store_true',
                        help='Skip copying images')
    parser.add_argument('--input', '-i', type=str, default=INPUT_CSV,
                        help=f'Input CSV file (default: {INPUT_CSV})')

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Create exporter
    exporter = BrandExporter(
        input_csv=args.input,
        images_dir=IMAGES_DIR,
        max_size_mb=args.max_size,
    )

    if args.list:
        print(exporter.list_brands(show_all=args.all))
        return

    # Parse brands to include
    brands_to_include = None
    if args.brands:
        brands_to_include = {b.strip() for b in args.brands.split(',')}
    elif args.brands_file:
        if not os.path.exists(args.brands_file):
            print(f"Error: brands file not found: {args.brands_file}")
            sys.exit(1)
        with open(args.brands_file, 'r', encoding='utf-8') as f:
            brands_to_include = {line.strip() for line in f if line.strip()}

    # Parse brands to exclude
    brands_to_exclude = None
    if args.exclude:
        brands_to_exclude = {b.strip() for b in args.exclude.split(',')}

    # Validate we have something to do
    if not args.all_brands and not brands_to_include and not brands_to_exclude and not args.top:
        print("Error: specify --all-brands, --brands, --brands-file, --top, or --exclude")
        print("Use --list to see available brands")
        sys.exit(1)

    exporter.export(
        brands_to_include=brands_to_include,
        brands_to_exclude=brands_to_exclude,
        top_n=args.top,
        output_csv=args.output,
        copy_images=not args.no_images,
        all_brands=args.all_brands,
    )


if __name__ == "__main__":
    main()
