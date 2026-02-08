"""
Bulk Product Extractor

Extracts products from a list of URLs and outputs a combined Shopify CSV.

Features:
- Progress tracking with resume capability
- Error handling with failed URL tracking
- Rate limiting for respectful crawling
- Combined CSV output for Shopify import
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Set

from ..models import ExtractedProduct, ProductImage
from ..shopify import ShopifyCSVExporter, SHOPIFY_FIELDNAMES
from ..common.csv_utils import configure_csv

# Configure CSV for large fields
configure_csv()


class BulkExtractor:
    """Bulk product extraction with progress tracking and resume capability."""

    def __init__(
        self,
        output_csv: str,
        output_dir: str = "output",
        delay: float = 1.0,
        save_failed_html: bool = False,
        source_domain: str = "benu.bg",
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
        self.processed_urls: Set[str] = set()
        self.failed_urls: List[Dict] = []
        self.total_extracted = 0
        self.total_image_rows = 0
        self.total_images = 0
        self.start_time = None

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

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
                        print("Recalculating CSV stats...")
                        csv_stats = self.recalculate_csv_stats()
                        self.total_extracted = csv_stats["products"]
                        self.total_image_rows = csv_stats["image_rows"]
                        self.total_images = csv_stats["total_rows"]

                    print(f"Loaded state:")
                    print(f"   URLs processed:    {len(self.processed_urls)}")
                    print(f"   Unique products:   {self.total_extracted}")
                    print(f"   CSV rows:          {self.total_extracted + self.total_image_rows} (+1 header)")
                    return True
            except Exception as e:
                print(f"Could not load state: {e}")
        return False

    def save_state(self):
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

    def save_failed_urls(self):
        """Save failed URLs to a separate file for retry."""
        with open(self.failed_file, "w", encoding="utf-8") as f:
            for failure in self.failed_urls:
                f.write(f"{failure['url']}\t{failure['error']}\n")

    def recalculate_csv_stats(self) -> Dict:
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
            print(f"Could not read CSV for stats: {e}")
            return {"products": 0, "image_rows": 0, "total_rows": 0}

        return {
            "products": products,
            "image_rows": image_rows,
            "total_rows": products + image_rows
        }

    def product_to_csv_rows(self, product: ExtractedProduct) -> List[Dict]:
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
        urls: List[str],
        extractor_class,
        limit: int = 0,
        resume: bool = False,
        continue_on_error: bool = True,
    ):
        """
        Extract all products from URL list.

        Args:
            urls: List of product URLs to extract
            extractor_class: Class to use for extraction (e.g., BenuExtractor)
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

        print(f"\nExtraction Progress")
        print(f"   Total URLs in input: {total_input_urls}")
        if resume and already_processed > 0:
            print(f"   Already processed: {already_processed} ({100*already_processed/total_input_urls:.1f}%)")
        print(f"   Remaining to process: {total_urls} ({100*total_urls/total_input_urls:.1f}%)")

        # Initialize CSV file
        csv_exists = os.path.exists(self.output_csv)
        write_mode = 'a' if (resume and csv_exists) else 'w'

        with open(self.output_csv, write_mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)

            # Write header only for new file
            if write_mode == 'w':
                writer.writeheader()

            for i, url in enumerate(urls_to_process, 1):
                elapsed = (datetime.now() - self.start_time).total_seconds()

                # Show progress relative to total input URLs
                overall_progress = already_processed + i
                print(f"[{overall_progress}/{total_input_urls}] {url[:60]}...")

                try:
                    extractor = extractor_class(url)
                    extractor.fetch()
                    product = extractor.extract()

                    if product:
                        # Skip products without images
                        if not product.images:
                            print(f"  Skipped (no images): {product.title[:50]}...")
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

                        print(f"  OK: {product.title[:50]}... ({num_images} images)")
                    else:
                        raise Exception("No product extracted")

                except Exception as e:
                    error_msg = str(e)[:100]
                    print(f"  Error: {error_msg}")

                    self.failed_urls.append({
                        "url": url,
                        "error": error_msg,
                        "timestamp": datetime.now().isoformat()
                    })
                    self.processed_urls.add(url)

                    # Save failed HTML for debugging
                    if self.save_failed_html:
                        self._save_failed_html(url)

                    if not continue_on_error:
                        print("Stopping due to error (use --continue-on-error to ignore)")
                        break

                # Save state periodically (every 10 products)
                if i % 10 == 0:
                    self.save_state()
                    csvfile.flush()

                # Rate limiting
                if i < total_urls:
                    time.sleep(self.delay)

        # Final save
        self.save_state()
        self.save_failed_urls()

        # Summary
        self._print_summary(total_urls)

    def _save_failed_html(self, url: str):
        """Save HTML of failed page for debugging."""
        try:
            import requests
            response = requests.get(url, timeout=30)
            html_dir = os.path.join(self.output_dir, "failed_html")
            os.makedirs(html_dir, exist_ok=True)

            # Generate filename from URL
            filename = url.split("/")[-1][:50] + ".html"
            filepath = os.path.join(html_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)
        except Exception:
            pass

    def _print_summary(self, total_attempted: int):
        """Print extraction summary."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        total_csv_rows = self.total_extracted + self.total_image_rows

        print("\n" + "=" * 60)
        print("Extraction Summary")
        print("=" * 60)
        print(f"\n  Progress:")
        print(f"     URLs processed:     {len(self.processed_urls)}")
        print(f"     URLs failed:        {len(self.failed_urls)}")
        print(f"\n  Products:")
        print(f"     Unique products:    {self.total_extracted}")
        print(f"     Total images:       {self.total_images}")
        avg_images = self.total_images / self.total_extracted if self.total_extracted > 0 else 0
        print(f"     Avg images/product: {avg_images:.2f}")
        print(f"\n  CSV Output (Shopify format):")
        print(f"     Product rows:       {self.total_extracted} (rows with Title)")
        print(f"     Image rows:         {self.total_image_rows} (additional images)")
        print(f"     Total CSV rows:     {total_csv_rows} (+1 header)")
        print(f"\n  Performance:")
        print(f"     Time elapsed:       {elapsed:.1f} seconds")
        if self.total_extracted > 0 and elapsed > 0:
            print(f"     Rate:               {self.total_extracted / elapsed:.2f} products/sec")
        print(f"\n  Output files:")
        print(f"     CSV:    {self.output_csv}")
        print(f"     Images: Using original URLs (Shopify will fetch from source)")
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
