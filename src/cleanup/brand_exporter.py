"""
Brand Exporter for Shopify Products CSV

Exports products by brand for selective Shopify import.

Features:
- List all brands with product counts
- Export products from selected brands only
- Auto-split into multiple files under size limit (default 14MB for Shopify's 15MB limit)
- Keep brands complete (never split a brand across files)
- Copy associated images to separate folder
- Support include/exclude brand lists
"""

from __future__ import annotations

import csv
import io
import logging
import os
import shutil
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

DEFAULT_MAX_SIZE_MB = 14  # 14MB to stay safely under Shopify's 15MB limit


class BrandExporter:
    """Exports products by brand with file size splitting."""

    def __init__(
        self,
        input_csv: str,
        images_dir: str = "output/images",
        max_size_mb: float = DEFAULT_MAX_SIZE_MB,
    ):
        """
        Initialize the BrandExporter.

        Args:
            input_csv: Path to input CSV file
            images_dir: Directory containing product images
            max_size_mb: Maximum file size in MB (default: 14MB)
        """
        self.input_csv = input_csv
        self.images_dir = images_dir
        self.max_size_mb = max_size_mb

    def get_brand_stats(self) -> Counter:
        """Get brand statistics from products CSV."""
        brands = Counter()
        with open(self.input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Title', '').strip():
                    brand = row.get('Vendor', '').strip() or '(No Brand)'
                    brands[brand] += 1
        return brands

    def list_brands(self, show_all: bool = False) -> str:
        """
        List all brands with product counts.

        Args:
            show_all: If True, show all brands; otherwise show top 50

        Returns:
            Formatted string with brand statistics
        """
        brands = self.get_brand_stats()
        total = sum(brands.values())

        lines = []
        lines.append("=" * 70)
        lines.append("Brand Summary")
        lines.append("=" * 70)
        lines.append(f"Total unique brands: {len(brands)}")
        lines.append(f"Total products: {total}")
        lines.append("")

        limit = len(brands) if show_all else 50
        lines.append(f"{'Rank':<5} {'Brand':<40} {'Products':>8} {'Cumul.':>8} {'%':>6}")
        lines.append("-" * 70)

        cumulative = 0
        for i, (brand, count) in enumerate(brands.most_common(limit), 1):
            cumulative += count
            pct = 100 * cumulative / total
            lines.append(f"{i:<5} {brand[:40]:<40} {count:>8} {cumulative:>8} {pct:>5.1f}%")

        if not show_all and len(brands) > 50:
            lines.append(f"\n... and {len(brands) - 50} more brands")
            lines.append("Use show_all=True to see all brands")

        lines.append("\n" + "=" * 70)
        lines.append("Quick stats:")
        top10 = sum(c for _, c in brands.most_common(10))
        top20 = sum(c for _, c in brands.most_common(20))
        top50 = sum(c for _, c in brands.most_common(50))
        lines.append(f"  Top 10 brands: {top10} products ({100*top10/total:.1f}%)")
        lines.append(f"  Top 20 brands: {top20} products ({100*top20/total:.1f}%)")
        lines.append(f"  Top 50 brands: {top50} products ({100*top50/total:.1f}%)")
        lines.append("=" * 70)

        return "\n".join(lines)

    def _get_products_by_brand(
        self, selected_brands: set[str]
    ) -> tuple[dict[str, list[dict]], list]:
        """
        Load products grouped by brand.

        Returns:
            Tuple of (products_by_brand dict, fieldnames list)
        """
        products_by_brand = defaultdict(list)
        fieldnames = None

        with open(self.input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            current_brand = None

            for row in reader:
                title = row.get('Title', '').strip()

                if title:  # Product row
                    current_brand = row.get('Vendor', '').strip() or '(No Brand)'

                if current_brand in selected_brands:
                    products_by_brand[current_brand].append(row)

        return products_by_brand, fieldnames

    def _estimate_brand_size(self, brand_rows: list[dict], fieldnames: list) -> int:
        """Estimate CSV size for a brand's rows (without header)."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        for row in brand_rows:
            writer.writerow(row)
        return len(output.getvalue().encode('utf-8'))

    def _get_header_size(self, fieldnames: list) -> int:
        """Get the size of CSV header in bytes."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        return len(output.getvalue().encode('utf-8'))

    def _split_brands_into_chunks(
        self,
        products_by_brand: dict[str, list[dict]],
        fieldnames: list,
        max_size_bytes: int,
    ) -> list[list[str]]:
        """
        Split brands into chunks that fit within max_size_bytes.

        Returns list of lists, where each inner list contains brand names for one file.
        """
        header_size = self._get_header_size(fieldnames)
        chunks = []
        current_chunk = []
        current_size = header_size

        # Calculate sizes
        brand_sizes = {
            brand: self._estimate_brand_size(rows, fieldnames)
            for brand, rows in products_by_brand.items()
        }

        # Sort by product count (largest brands first)
        sorted_brands = sorted(
            products_by_brand.keys(),
            key=lambda b: len(products_by_brand[b]),
            reverse=True
        )

        for brand in sorted_brands:
            brand_size = brand_sizes[brand]

            # Check if brand alone exceeds max size
            if brand_size + header_size > max_size_bytes:
                logger.warning("Brand '%s' (%.1fMB) exceeds max file size, placing in its own file",
                               brand, brand_size / 1024 / 1024)
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_size = header_size
                chunks.append([brand])
                continue

            # Check if adding this brand would exceed limit
            if current_size + brand_size > max_size_bytes:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = [brand]
                current_size = header_size + brand_size
            else:
                current_chunk.append(brand)
                current_size += brand_size

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _write_chunk_csv(
        self,
        chunk_brands: list[str],
        products_by_brand: dict[str, list[dict]],
        fieldnames: list,
        output_path: str,
    ) -> tuple[int, int]:
        """
        Write a chunk of brands to CSV file.

        Returns (products_count, image_rows_count)
        """
        products_count = 0
        image_rows_count = 0

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for brand in chunk_brands:
                for row in products_by_brand[brand]:
                    writer.writerow(row)
                    if row.get('Title', '').strip():
                        products_count += 1
                    else:
                        image_rows_count += 1

        return products_count, image_rows_count

    def export(
        self,
        brands_to_include: set[str] | None = None,
        brands_to_exclude: set[str] | None = None,
        top_n: int | None = None,
        output_csv: str = "output/export.csv",
        copy_images: bool = True,
        all_brands: bool = False,
    ) -> list[dict]:
        """
        Export products from selected brands, splitting into multiple files if needed.

        Args:
            brands_to_include: Set of brand names to include
            brands_to_exclude: Set of brand names to exclude
            top_n: Export only top N brands by product count
            output_csv: Output CSV file path
            copy_images: Whether to copy associated images
            all_brands: If True, export all brands

        Returns:
            List of file statistics dictionaries
        """
        # Determine which brands to include
        all_brand_stats = self.get_brand_stats()

        if all_brands:
            brands_to_include = set(all_brand_stats.keys())
            logger.info("Exporting all %d brands...", len(brands_to_include))
        elif top_n:
            brands_to_include = {brand for brand, _ in all_brand_stats.most_common(top_n)}
            logger.info("Selected top %d brands: %s", top_n, ', '.join(sorted(brands_to_include)))

        if brands_to_include:
            selected_brands = brands_to_include
        else:
            selected_brands = set(all_brand_stats.keys())

        if brands_to_exclude:
            selected_brands = selected_brands - brands_to_exclude
            logger.info("Excluding %d brands", len(brands_to_exclude))

        logger.info("Processing %d brands...", len(selected_brands))

        # Load all products by brand
        products_by_brand, fieldnames = self._get_products_by_brand(selected_brands)

        total_products = sum(
            1 for rows in products_by_brand.values()
            for row in rows if row.get('Title', '').strip()
        )
        logger.info("Found %d products", total_products)

        # Guard: warn if image URLs contain a placeholder domain
        bad_urls = [
            row.get('Product image URL', '')
            for rows in products_by_brand.values()
            for row in rows
            if 'example.com' in row.get('Product image URL', '')
            or 'localhost' in row.get('Product image URL', '')
        ]
        if bad_urls:
            logger.warning(
                "%d image URL(s) contain a placeholder domain (e.g. %s). "
                "Shopify will fail to fetch these images. "
                "Re-run extraction with the correct source domain.",
                len(bad_urls), bad_urls[0],
            )

        # Calculate max size in bytes
        max_size_bytes = int(self.max_size_mb * 1024 * 1024)

        # Split into chunks
        logger.info("Splitting into files (max %.0fMB each, keeping brands together)...", self.max_size_mb)
        chunks = self._split_brands_into_chunks(products_by_brand, fieldnames, max_size_bytes)

        logger.info("Created %d file(s)", len(chunks))

        # Prepare output paths
        output_dir = os.path.dirname(output_csv) or '.'
        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.basename(output_csv)
        name_part, ext = os.path.splitext(base_name)

        # Write files
        file_stats = []
        all_images = set()

        for i, chunk_brands in enumerate(chunks, 1):
            # Generate filename
            if len(chunks) == 1:
                file_path = output_csv
            else:
                file_path = os.path.join(output_dir, f"{name_part}_{i:03d}{ext}")

            products_count, image_rows_count = self._write_chunk_csv(
                chunk_brands, products_by_brand, fieldnames, file_path
            )

            file_size = os.path.getsize(file_path)
            file_stats.append({
                'path': file_path,
                'brands': len(chunk_brands),
                'products': products_count,
                'image_rows': image_rows_count,
                'size_mb': file_size / 1024 / 1024,
            })

            # Collect images
            for brand in chunk_brands:
                for row in products_by_brand[brand]:
                    img_url = row.get('Product image URL', '').strip()
                    if img_url and not img_url.startswith('http'):
                        img_name = os.path.basename(img_url)
                        all_images.add(img_name)

        # Copy images if requested
        images_copied = 0
        images_output_dir = os.path.join(output_dir, 'images')
        if copy_images and all_images and os.path.exists(self.images_dir):
            os.makedirs(images_output_dir, exist_ok=True)
            for img_name in all_images:
                src = os.path.join(self.images_dir, img_name)
                dst = os.path.join(images_output_dir, img_name)
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    images_copied += 1

        # Print summary
        self._print_summary(
            selected_brands, total_products, chunks, file_stats,
            copy_images, images_copied
        )

        return file_stats

    def _print_summary(
        self,
        selected_brands: set[str],
        total_products: int,
        chunks: list[list[str]],
        file_stats: list[dict],
        copy_images: bool,
        images_copied: int,
    ) -> None:
        """Print export summary to console."""
        print("\n" + "=" * 70)
        print("Export Summary")
        print("=" * 70)
        print(f"  Total brands:      {len(selected_brands)}")
        print(f"  Total products:    {total_products}")
        print(f"  Files created:     {len(chunks)}")
        print(f"  Max file size:     {self.max_size_mb}MB")
        if copy_images and images_copied:
            print(f"  Images copied:     {images_copied}")

        print("\n" + "-" * 70)
        print(f"{'File':<40} {'Brands':>8} {'Products':>10} {'Size':>10}")
        print("-" * 70)

        for stat in file_stats:
            filename = os.path.basename(stat['path'])
            print(f"{filename:<40} {stat['brands']:>8} {stat['products']:>10} {stat['size_mb']:>9.1f}MB")

        print("-" * 70)
        total_size = sum(s['size_mb'] for s in file_stats)
        print(f"{'TOTAL':<40} {len(selected_brands):>8} {total_products:>10} {total_size:>9.1f}MB")
        print("=" * 70)

        if len(chunks) > 1:
            print("\nImport files to Shopify in order:")
            for stat in file_stats:
                print(f"  {stat['path']}")
