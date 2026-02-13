"""
Tag Cleaner for Shopify Products CSV

Post-processes a Shopify products CSV to:
1. Normalize tag casing (fix case-sensitivity duplicates)
2. Remove brand names from tags (they're already in Vendor field)
3. Assign missing L1 category tags based on subcategory inference
4. Remove promotional/temporal tags
"""

from __future__ import annotations

import csv
import logging
import os
from collections import Counter

logger = logging.getLogger(__name__)

from ..common.config_loader import (
    build_subcategory_to_l1_map,
    get_l1_category_names,
    load_categories,
    load_promotional_patterns,
    load_tag_normalization,
    load_vendor_defaults,
)


class TagCleaner:
    """Cleans and normalizes tags in a Shopify products CSV."""

    def __init__(self, input_path: str, output_path: str, report_path: str = None):
        """
        Initialize the TagCleaner.

        Args:
            input_path: Path to input CSV file
            output_path: Path to output CSV file
            report_path: Optional path to write detailed cleanup report
        """
        self.input_path = input_path
        self.output_path = output_path
        self.report_path = report_path

        # Load configuration from YAML files
        self.l1_categories = load_categories()
        self.tag_normalization = load_tag_normalization()
        self.vendor_default_tags = load_vendor_defaults()
        self.promotional_patterns = load_promotional_patterns()

        # Build derived mappings
        self.subcategory_to_l1 = build_subcategory_to_l1_map(self.l1_categories)
        self.l1_category_names = get_l1_category_names(self.l1_categories)

        # Statistics tracking
        self.stats = {
            'total_products': 0,
            'products_with_tags': 0,
            'tags_normalized': Counter(),
            'brands_removed': Counter(),
            'l1_categories_added': Counter(),
            'promotional_removed': Counter(),
            'vendor_defaults_applied': Counter(),
            'products_missing_l1_before': 0,
            'products_missing_l1_after': 0,
        }

        # Cache vendor names (brands) for removal
        self.vendor_names: set[str] = set()

    def _load_vendors(self):
        """Load all unique vendor names from CSV."""
        logger.info("Loading vendor names...")
        with open(self.input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                vendor = row.get('Vendor', '').strip()
                if vendor:
                    self.vendor_names.add(vendor.lower())

        logger.info("Found %d unique vendors", len(self.vendor_names))

    def _normalize_tag(self, tag: str) -> str:
        """Normalize tag casing using the normalization map."""
        tag_lower = tag.lower().strip()

        if tag_lower in self.tag_normalization:
            normalized = self.tag_normalization[tag_lower]
            if tag != normalized:
                self.stats['tags_normalized'][f"{tag} -> {normalized}"] += 1
            return normalized

        return tag.strip()

    def _is_promotional(self, tag: str) -> bool:
        """Check if tag is promotional/temporal."""
        tag_lower = tag.lower()
        return any(pattern in tag_lower for pattern in self.promotional_patterns)

    def _is_brand_tag(self, tag: str, vendor: str) -> bool:
        """Check if tag is the brand name (matches vendor)."""
        tag_lower = tag.lower().strip()
        vendor_lower = vendor.lower().strip()
        return tag_lower == vendor_lower or tag_lower in self.vendor_names

    def _get_l1_category(self, tags: list[str]) -> str:
        """Determine L1 category from existing tags."""
        for tag in tags:
            tag_lower = tag.lower().strip()

            # Direct L1 match
            if tag_lower in self.l1_category_names:
                return tag

            # Infer from subcategory
            if tag_lower in self.subcategory_to_l1:
                return self.subcategory_to_l1[tag_lower]

        return None

    def _has_l1_category(self, tags: list[str]) -> bool:
        """Check if tags include an L1 category."""
        return any(tag.lower().strip() in self.l1_category_names for tag in tags)

    def _clean_tags(self, tags_str: str, vendor: str) -> tuple[str, bool]:
        """
        Clean tags string and return cleaned version.

        Returns:
            Tuple of (cleaned_tags_string, l1_was_added)
        """
        if not tags_str.strip():
            return '', False

        # Parse tags
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        cleaned_tags = []
        l1_added = False

        for tag in tags:
            # Skip empty tags
            if not tag.strip():
                continue

            # Remove promotional tags
            if self._is_promotional(tag):
                self.stats['promotional_removed'][tag] += 1
                continue

            # Remove brand tags (they're in Vendor field)
            if self._is_brand_tag(tag, vendor):
                self.stats['brands_removed'][tag] += 1
                continue

            # Normalize casing
            normalized = self._normalize_tag(tag)
            cleaned_tags.append(normalized)

        # Infer and add missing L1 category
        if not self._has_l1_category(cleaned_tags):
            l1_category = self._get_l1_category(cleaned_tags)
            if l1_category:
                # Insert L1 at the beginning
                cleaned_tags.insert(0, l1_category)
                self.stats['l1_categories_added'][l1_category] += 1
                l1_added = True

        # If still no tags or no L1, apply vendor default tags
        vendor_lower = vendor.lower().strip()
        if vendor_lower in self.vendor_default_tags:
            if not cleaned_tags or not self._has_l1_category(cleaned_tags):
                default_tags = self.vendor_default_tags[vendor_lower]
                # Add default tags (avoid duplicates)
                for tag in default_tags:
                    if tag not in cleaned_tags:
                        cleaned_tags.insert(0, tag)
                self.stats['vendor_defaults_applied'][vendor] += 1

        return ', '.join(cleaned_tags), l1_added

    def process(self):
        """Process the CSV file and write cleaned output."""
        self._load_vendors()

        logger.info("Processing: %s", self.input_path)
        logger.info("Output: %s", self.output_path)

        # Create output directory if needed
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        rows_processed = 0

        with open(self.input_path, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames

            with open(self.output_path, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    self.stats['total_products'] += 1

                    # Only process main product rows (have Title)
                    if not row.get('Title', '').strip():
                        # Write variant rows unchanged
                        writer.writerow(row)
                        continue

                    original_tags = row.get('Tags', '')
                    vendor = row.get('Vendor', '')

                    if original_tags.strip():
                        self.stats['products_with_tags'] += 1

                        # Track L1 category stats before cleaning
                        if not self._has_l1_category(
                            [t.strip() for t in original_tags.split(',') if t.strip()]
                        ):
                            self.stats['products_missing_l1_before'] += 1

                    # Clean tags
                    cleaned_tags, l1_added = self._clean_tags(original_tags, vendor)

                    # Track L1 category stats after cleaning
                    if cleaned_tags and not self._has_l1_category(
                        [t.strip() for t in cleaned_tags.split(',') if t.strip()]
                    ):
                        self.stats['products_missing_l1_after'] += 1

                    # Update row
                    row['Tags'] = cleaned_tags
                    writer.writerow(row)

                    rows_processed += 1
                    if rows_processed % 1000 == 0:
                        logger.info("Processed %d products...", rows_processed)

        logger.info("Completed! Processed %d products", rows_processed)
        self._print_summary()

        if self.report_path:
            self._write_report()

    def _print_summary(self):
        """Print cleanup summary to console."""
        print("\n" + "=" * 60)
        print("TAG CLEANUP SUMMARY")
        print("=" * 60)

        print(f"\nProducts processed: {self.stats['total_products']}")
        print(f"Products with tags: {self.stats['products_with_tags']}")

        print("\nL1 Category Coverage:")
        print(f"  Missing L1 before: {self.stats['products_missing_l1_before']}")
        print(f"  Missing L1 after:  {self.stats['products_missing_l1_after']}")
        print(f"  L1 categories added: {sum(self.stats['l1_categories_added'].values())}")

        print(f"\nTags normalized (case fixes): {sum(self.stats['tags_normalized'].values())}")
        if self.stats['tags_normalized']:
            print("  Top normalizations:")
            for tag, count in self.stats['tags_normalized'].most_common(10):
                print(f"    {tag}: {count}")

        print(f"\nBrand tags removed: {sum(self.stats['brands_removed'].values())}")
        if self.stats['brands_removed']:
            print("  Top removed brands:")
            for tag, count in self.stats['brands_removed'].most_common(10):
                print(f"    {tag}: {count}")

        print(f"\nPromotional tags removed: {sum(self.stats['promotional_removed'].values())}")
        if self.stats['promotional_removed']:
            print("  Removed:")
            for tag, count in self.stats['promotional_removed'].most_common(10):
                print(f"    {tag}: {count}")

        print(f"\nVendor default tags applied: {sum(self.stats['vendor_defaults_applied'].values())}")
        if self.stats['vendor_defaults_applied']:
            print("  By vendor:")
            for vendor, count in self.stats['vendor_defaults_applied'].most_common(10):
                print(f"    {vendor}: {count}")

        print("=" * 60)

    def _write_report(self):
        """Write detailed cleanup report to file."""
        logger.info("Writing report to: %s", self.report_path)

        # Create report directory if needed
        report_dir = os.path.dirname(self.report_path)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)

        with open(self.report_path, 'w', encoding='utf-8') as f:
            f.write("TAG CLEANUP REPORT\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"Input file: {self.input_path}\n")
            f.write(f"Output file: {self.output_path}\n\n")

            f.write(f"Products processed: {self.stats['total_products']}\n")
            f.write(f"Products with tags: {self.stats['products_with_tags']}\n\n")

            f.write("L1 CATEGORY COVERAGE\n")
            f.write("-" * 40 + "\n")
            f.write(f"Missing L1 before cleanup: {self.stats['products_missing_l1_before']}\n")
            f.write(f"Missing L1 after cleanup:  {self.stats['products_missing_l1_after']}\n")
            f.write(f"L1 categories added: {sum(self.stats['l1_categories_added'].values())}\n\n")

            if self.stats['l1_categories_added']:
                f.write("L1 categories added by count:\n")
                for cat, count in self.stats['l1_categories_added'].most_common():
                    f.write(f"  {cat}: {count}\n")
                f.write("\n")

            f.write("TAGS NORMALIZED (case fixes)\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total: {sum(self.stats['tags_normalized'].values())}\n\n")
            for tag, count in self.stats['tags_normalized'].most_common():
                f.write(f"  {tag}: {count}\n")
            f.write("\n")

            f.write("BRAND TAGS REMOVED\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total: {sum(self.stats['brands_removed'].values())}\n\n")
            for tag, count in self.stats['brands_removed'].most_common():
                f.write(f"  {tag}: {count}\n")
            f.write("\n")

            f.write("PROMOTIONAL TAGS REMOVED\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total: {sum(self.stats['promotional_removed'].values())}\n\n")
            for tag, count in self.stats['promotional_removed'].most_common():
                f.write(f"  {tag}: {count}\n")

        logger.info("Report written successfully.")

    def get_stats(self) -> dict:
        """Return the statistics dictionary."""
        return self.stats
