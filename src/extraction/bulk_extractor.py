"""
Bulk Product Extractor

Extracts products from a list of URLs and outputs a combined Shopify CSV.

Features:
- Progress tracking with resume capability
- Error handling with failed URL tracking
- Rate limiting for respectful crawling
- Combined CSV output for Shopify import
"""

from __future__ import annotations

import csv
import json
import logging
import os
import time
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

from ..models import ExtractedProduct
from ..shopify import SHOPIFY_FIELDNAMES, ShopifyCSVExporter


class BulkExtractor:
    """Bulk product extraction with progress tracking and resume capability."""

    def __init__(
        self,
        output_csv: str,
        output_dir: str = "output",
        delay: float = 1.0,
        save_failed_html: bool = False,
        source_domain: str = "pharmacy.example.com",
    ):
        """
        Initialize the bulk extractor.

        Args:
            output_csv: Path to output CSV file
            output_dir: Directory for output files and state
            delay: Delay between requests in seconds
            save_failed_html: Whether to save HTML of failed pages
            source_domain: Source domain for cleaning references from text
        """
        self.output_csv = output_csv
        self.output_dir = output_dir
        self.delay = delay
        self.save_failed_html = save_failed_html

        # Progress tracking
        self.state_file = os.path.join(output_dir, "extraction_state.json")
        self.failed_file = os.path.join(output_dir, "failed_urls.txt")

        # State
        self.processed_urls: set[str] = set()
        self.failed_urls: list[dict] = []
        self.total_extracted = 0
        self.total_image_rows = 0
        self.total_images = 0
        self.start_time = None

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        self.source_domain = source_domain

        # CSV exporter (single source of truth for row generation)
        self._csv_exporter = ShopifyCSVExporter(source_domain=source_domain)
        self.fieldnames = SHOPIFY_FIELDNAMES

    def load_state(self) -> bool:
        """Load previous extraction state for resume."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.processed_urls = set(state.get("processed_urls", []))
                    self.failed_urls = state.get("failed_urls", [])
                    self.total_extracted = state.get("total_extracted", 0)
                    self.total_image_rows = state.get("total_image_rows", 0)
                    self.total_images = state.get("total_images", 0)

                    # If image metrics are missing, recalculate from CSV
                    if self.total_image_rows == 0 and self.total_extracted > 0:
                        logger.info("Recalculating CSV stats...")
                        csv_stats = self.recalculate_csv_stats()
                        self.total_extracted = csv_stats["products"]
                        self.total_image_rows = csv_stats["image_rows"]
                        self.total_images = csv_stats["total_rows"]

                    logger.info("Loaded state: URLs processed=%d, products=%d, CSV rows=%d",
                                len(self.processed_urls), self.total_extracted,
                                self.total_extracted + self.total_image_rows)
                    return True
            except Exception as e:
                logger.warning("Could not load state: %s", e)
        return False

    def save_state(self) -> None:
        """Save current extraction state."""
        state = {
            "processed_urls": list(self.processed_urls),
            "failed_urls": self.failed_urls,
            "total_extracted": self.total_extracted,
            "total_image_rows": self.total_image_rows,
            "total_images": self.total_images,
            "total_csv_rows": self.total_extracted + self.total_image_rows,
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def save_failed_urls(self) -> None:
        """Save failed URLs to a separate file for retry."""
        with open(self.failed_file, "w", encoding="utf-8") as f:
            for failure in self.failed_urls:
                f.write(f"{failure['url']}\t{failure['error']}\n")

    def recalculate_csv_stats(self) -> dict:
        """Recalculate stats from existing CSV file."""
        if not os.path.exists(self.output_csv):
            return {"products": 0, "image_rows": 0, "total_rows": 0}

        products = 0
        image_rows = 0

        try:
            with open(self.output_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Title', '').strip():
                        products += 1
                    else:
                        image_rows += 1
        except Exception as e:
            logger.warning("Could not read CSV for stats: %s", e)
            return {"products": 0, "image_rows": 0, "total_rows": 0}

        return {
            "products": products,
            "image_rows": image_rows,
            "total_rows": products + image_rows
        }

    def product_to_csv_rows(self, product: ExtractedProduct) -> list[dict]:
        """
        Convert product to CSV rows (1 main row + N-1 image rows).

        Delegates to ShopifyCSVExporter for the single source of truth
        on CSV column layout.

        Args:
            product: Product to convert

        Returns:
            List of row dictionaries
        """
        self._csv_exporter.clean_product(product)
        return self._csv_exporter.product_to_rows(product)

    def extract_all(
        self,
        urls: list[str],
        extractor_class,
        limit: int = 0,
        resume: bool = False,
        continue_on_error: bool = True,
    ) -> None:
        """
        Extract all products from URL list.

        Args:
            urls: List of product URLs to extract
            extractor_class: Class to use for extraction (e.g., PharmacyExtractor)
            limit: Maximum number of products to extract (0 = no limit)
            resume: Whether to resume from previous state
            continue_on_error: Whether to continue if extraction fails
        """
        self.start_time = datetime.now()

        # Load previous state if resuming
        if resume:
            self.load_state()

        # Filter out already processed URLs
        urls_to_process = [u for u in urls if u not in self.processed_urls]

        if limit > 0:
            urls_to_process = urls_to_process[:limit]

        total_urls = len(urls_to_process)
        total_input_urls = len(urls)
        already_processed = len(self.processed_urls)

        logger.info("Extraction Progress: total=%d, remaining=%d", total_input_urls, total_urls)
        if resume and already_processed > 0:
            logger.info("Already processed: %d (%.1f%%)", already_processed, 100*already_processed/total_input_urls)

        # Initialize CSV file
        csv_exists = os.path.exists(self.output_csv)
        write_mode = 'a' if (resume and csv_exists) else 'w'

        # Shared session for TCP connection reuse across products
        session = requests.Session()

        with open(self.output_csv, write_mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)

            # Write header only for new file
            if write_mode == 'w':
                writer.writeheader()

            for i, url in enumerate(urls_to_process, 1):
                # Show progress relative to total input URLs
                overall_progress = already_processed + i
                logger.info("[%d/%d] %s...", overall_progress, total_input_urls, url[:60])

                extractor = None
                try:
                    extractor = extractor_class(url, session=session, site_domain=self.source_domain)
                    extractor.fetch()
                    product = extractor.extract()

                    if product:
                        # Skip products without images
                        if not product.images:
                            logger.info("Skipped (no images): %s...", product.title[:50])
                            self.processed_urls.add(url)
                            continue

                        rows = self.product_to_csv_rows(product)
                        for row in rows:
                            writer.writerow(row)

                        # Track metrics
                        num_images = len(product.images)
                        self.total_extracted += 1
                        self.total_images += num_images
                        self.total_image_rows += max(0, num_images - 1)
                        self.processed_urls.add(url)

                        logger.info("OK: %s... (%d images)", product.title[:50], num_images)
                    else:
                        raise ValueError("No product extracted")

                except (requests.RequestException, ValueError, KeyError,
                        TypeError, AttributeError, json.JSONDecodeError) as e:
                    error_msg = f"{type(e).__name__}: {str(e)[:100]}"
                    logger.error("Error: %s", error_msg)

                    self.failed_urls.append({
                        "url": url,
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    })
                    self.processed_urls.add(url)

                    # Save failed HTML for debugging
                    if self.save_failed_html and extractor is not None:
                        self._save_failed_html(url, extractor.html)

                    if not continue_on_error:
                        logger.error("Stopping due to error (use --continue-on-error to ignore)")
                        break

                # Save state periodically (every 10 products)
                if i % 10 == 0:
                    self.save_state()
                    csvfile.flush()

                # Rate limiting
                if i < total_urls:
                    time.sleep(self.delay)

        session.close()

        # Final save
        self.save_state()
        self.save_failed_urls()

        # Summary
        self._print_summary(total_urls)

    def _save_failed_html(self, url: str, html: str | None = None) -> None:
        """Save HTML of failed page for debugging.

        Args:
            url: Product URL (used for filename generation)
            html: Already-fetched HTML content. If None, skips saving.
        """
        if not html:
            return
        try:
            html_dir = os.path.join(self.output_dir, "failed_html")
            os.makedirs(html_dir, exist_ok=True)

            # Generate filename from URL
            filename = url.split("/")[-1][:50] + ".html"
            filepath = os.path.join(html_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

    def _print_summary(self, total_attempted: int) -> None:
        """Print extraction summary."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        total_csv_rows = self.total_extracted + self.total_image_rows

        print("\n" + "=" * 60)
        print("Extraction Summary")
        print("=" * 60)
        print("\n  Progress:")
        print(f"     URLs processed:     {len(self.processed_urls)}")
        print(f"     URLs failed:        {len(self.failed_urls)}")
        print("\n  Products:")
        print(f"     Unique products:    {self.total_extracted}")
        print(f"     Total images:       {self.total_images}")
        avg_images = self.total_images / self.total_extracted if self.total_extracted > 0 else 0
        print(f"     Avg images/product: {avg_images:.2f}")
        print("\n  CSV Output (Shopify format):")
        print(f"     Product rows:       {self.total_extracted} (rows with Title)")
        print(f"     Image rows:         {self.total_image_rows} (additional images)")
        print(f"     Total CSV rows:     {total_csv_rows} (+1 header)")
        print("\n  Performance:")
        print(f"     Time elapsed:       {elapsed:.1f} seconds")
        if self.total_extracted > 0 and elapsed > 0:
            print(f"     Rate:               {self.total_extracted / elapsed:.2f} products/sec")
        print("\n  Output files:")
        print(f"     CSV:    {self.output_csv}")
        print("     Images: Using original URLs (Shopify will fetch from source)")
        if self.failed_urls:
            print(f"     Failed: {self.failed_file}")
        print("=" * 60)

    def get_stats(self) -> dict:
        """Return extraction statistics."""
        return {
            'total_extracted': self.total_extracted,
            'total_images': self.total_images,
            'total_image_rows': self.total_image_rows,
            'processed_urls': len(self.processed_urls),
            'failed_urls': len(self.failed_urls),
        }
