#!/usr/bin/env python3
"""
Split large product CSV into Shopify-compatible chunks.

Shopify Import Limits:
- Max ~5,000 products per file (or 15MB)
- Image rows must stay with their parent product

Usage:
    python3 scripts/chunk_csv.py data/benu.bg/raw/products.csv
    python3 scripts/chunk_csv.py data/benu.bg/raw/products.csv --chunk-size 4000
    python3 scripts/chunk_csv.py data/benu.bg/raw/products.csv --output-dir output/benu.bg
"""

import argparse
import csv
import os
import sys
from pathlib import Path

# Default chunk size (products per file)
DEFAULT_CHUNK_SIZE = 4000  # Conservative limit under Shopify's 5,000


def count_products(csv_path: str) -> tuple[int, int]:
    """Count products and total rows in CSV."""
    products = 0
    total_rows = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Product rows have a Title, image rows don't
            if row.get("Title", "").strip():
                products += 1

    return products, total_rows


def chunk_csv(
    input_csv: str,
    output_dir: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> list[str]:
    """
    Split CSV into chunks, keeping image rows with their parent product.

    Args:
        input_csv: Path to input CSV
        output_dir: Directory for output files
        chunk_size: Max products per chunk

    Returns:
        List of output file paths
    """
    os.makedirs(output_dir, exist_ok=True)

    # Read all rows
    with open(input_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        all_rows = list(reader)

    # Group rows by product (Title row + following image rows)
    products = []
    current_product = []

    for row in all_rows:
        if row.get("Title", "").strip():
            # New product - save previous if exists
            if current_product:
                products.append(current_product)
            current_product = [row]
        else:
            # Image row - add to current product
            current_product.append(row)

    # Don't forget last product
    if current_product:
        products.append(current_product)

    # Split into chunks
    chunks = []
    current_chunk = []
    current_chunk_size = 0

    for product_rows in products:
        if current_chunk_size >= chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_chunk_size = 0

        current_chunk.extend(product_rows)
        current_chunk_size += 1

    # Last chunk
    if current_chunk:
        chunks.append(current_chunk)

    # Write chunks to files
    output_files = []
    base_name = Path(input_csv).stem

    for i, chunk in enumerate(chunks, 1):
        output_path = os.path.join(output_dir, f"{base_name}_{i:03d}.csv")

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(chunk)

        output_files.append(output_path)

        # Count products in this chunk
        products_in_chunk = sum(1 for row in chunk if row.get("Title", "").strip())
        print(f"  {output_path}: {products_in_chunk} products, {len(chunk)} rows")

    return output_files


def main():
    parser = argparse.ArgumentParser(
        description="Split product CSV into Shopify-compatible chunks"
    )
    parser.add_argument(
        "input_csv",
        help="Input CSV file"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory (default: same as input)"
    )
    parser.add_argument(
        "--chunk-size", "-s",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Max products per chunk (default: {DEFAULT_CHUNK_SIZE})"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input_csv):
        print(f"Error: File not found: {args.input_csv}")
        sys.exit(1)

    # Default output dir
    output_dir = args.output_dir or str(Path(args.input_csv).parent)

    # Count products
    print(f"Analyzing {args.input_csv}...")
    products, total_rows = count_products(args.input_csv)
    print(f"  Total products: {products}")
    print(f"  Total rows: {total_rows}")
    print(f"  Chunk size: {args.chunk_size} products")

    # Calculate expected chunks
    expected_chunks = (products + args.chunk_size - 1) // args.chunk_size
    print(f"  Expected chunks: {expected_chunks}")

    # Chunk the CSV
    print("\nSplitting into chunks...")
    output_files = chunk_csv(args.input_csv, output_dir, args.chunk_size)

    print(f"\nDone! Created {len(output_files)} files in {output_dir}")
    print("\nTo import into Shopify:")
    print("  1. Go to Shopify Admin > Products > Import")
    print("  2. Import each file in order (001, 002, 003...)")
    print("  3. Select 'Overwrite existing products with matching handles'")


if __name__ == "__main__":
    main()
