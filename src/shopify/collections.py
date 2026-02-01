"""
Shopify Collection Creator

Creates smart collections in Shopify based on tags from a product CSV.
Each unique tag becomes a smart collection with rule: "tag equals [tag_name]"
"""

import csv
import time
from collections import Counter
from typing import Dict, List, Set, Optional

from .api_client import ShopifyAPIClient
from ..common.transliteration import generate_handle
from ..common.csv_utils import configure_csv

# Configure CSV for large fields
configure_csv()


class ShopifyCollectionCreator:
    """
    Creates smart collections in Shopify via Admin API.

    Usage:
        creator = ShopifyCollectionCreator(
            shop="my-store",
            access_token="shpat_xxx",
            dry_run=True
        )
        creator.create_collections_from_csv(
            csv_path="products.csv",
            min_products=3,
            skip_brands=True
        )
    """

    def __init__(self, shop: str, access_token: str, dry_run: bool = False):
        """
        Initialize the creator.

        Args:
            shop: Shop name (without .myshopify.com) or full domain
            access_token: Shopify Admin API access token
            dry_run: If True, only preview without creating
        """
        self.client = ShopifyAPIClient(shop, access_token)
        self.dry_run = dry_run

        # Track created collections
        self.created_collections: List[str] = []
        self.skipped_collections: List[str] = []
        self.failed_collections: List[Dict] = []

    def get_existing_collections(self) -> Set[str]:
        """Fetch existing collection titles to avoid duplicates."""
        print("Fetching existing collections...")

        existing = set()
        endpoint = "smart_collections.json?limit=250"

        while endpoint:
            result = self.client.rest_request("GET", endpoint)
            if not result:
                break

            for collection in result.get("smart_collections", []):
                existing.add(collection.get("title", "").lower())

            # Simple implementation - just get first page
            endpoint = None

        print(f"  Found {len(existing)} existing smart collections")
        return existing

    def create_smart_collection(self, title: str, tag: str) -> bool:
        """
        Create a smart collection with tag-based rule.

        Args:
            title: Collection title
            tag: Tag to match

        Returns:
            True if created successfully
        """
        handle = generate_handle(title)

        data = {
            "smart_collection": {
                "title": title,
                "handle": handle,
                "rules": [
                    {
                        "column": "tag",
                        "relation": "equals",
                        "condition": tag
                    }
                ],
                "disjunctive": False,
                "published": True,
            }
        }

        if self.dry_run:
            print(f"  [DRY RUN] Would create: {title} (tag: {tag})")
            return True

        result = self.client.rest_request("POST", "smart_collections.json", data)

        if result and "smart_collection" in result:
            collection_id = result["smart_collection"]["id"]
            print(f"  Created: {title} (ID: {collection_id})")
            return True
        else:
            print(f"  Failed to create: {title}")
            return False

    def create_vendor_collection(self, vendor: str) -> bool:
        """
        Create a smart collection based on vendor (brand).

        Args:
            vendor: Vendor name to match

        Returns:
            True if created successfully
        """
        title = vendor
        handle = generate_handle(vendor, prefix="brand-")

        data = {
            "smart_collection": {
                "title": title,
                "handle": handle,
                "rules": [
                    {
                        "column": "vendor",
                        "relation": "equals",
                        "condition": vendor
                    }
                ],
                "disjunctive": False,
                "published": True,
            }
        }

        if self.dry_run:
            print(f"  [DRY RUN] Would create brand collection: {title} (vendor: {vendor})")
            return True

        result = self.client.rest_request("POST", "smart_collections.json", data)

        if result and "smart_collection" in result:
            collection_id = result["smart_collection"]["id"]
            print(f"  Created brand collection: {title} (ID: {collection_id})")
            return True
        else:
            print(f"  Failed to create brand collection: {title}")
            return False

    def _load_vendors_from_csv(self, csv_path: str) -> Set[str]:
        """Load all unique vendor names from CSV (lowercase)."""
        vendors = set()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vendor = row.get("Vendor", "").strip()
                if vendor:
                    vendors.add(vendor.lower())
        return vendors

    def _count_vendors(self, csv_path: str) -> Counter:
        """Count products per vendor."""
        vendor_counter = Counter()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("Title", "").strip():
                    continue
                vendor = row.get("Vendor", "").strip()
                if vendor:
                    vendor_counter[vendor] += 1
        return vendor_counter

    def _count_tags(self, csv_path: str) -> Counter:
        """Count products per tag."""
        tags_counter = Counter()
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("Title", "").strip():
                    continue
                tags_str = row.get("Tags", "")
                if tags_str:
                    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                    tags_counter.update(tags)
        return tags_counter

    def create_collections_from_csv(
        self,
        csv_path: str,
        min_products: int = 3,
        skip_existing: bool = True,
        skip_brands: bool = False,
        vendors_only: bool = False
    ):
        """
        Create collections from all unique tags in CSV.

        Args:
            csv_path: Path to Shopify CSV file
            min_products: Minimum products for a tag to become a collection
            skip_existing: Skip collections that already exist
            skip_brands: Skip tags that match vendor names (brand duplicates)
            vendors_only: Only create collections from Vendor field (not tags)
        """
        # Load vendor names for brand detection
        known_vendors = self._load_vendors_from_csv(csv_path)
        print(f"\nLoaded {len(known_vendors)} unique vendors from CSV")

        if vendors_only:
            self._create_vendor_collections(csv_path, min_products, skip_existing)
            return

        print(f"\nReading tags from: {csv_path}")

        # Count tags
        tags_counter = self._count_tags(csv_path)

        # Filter by minimum products
        eligible_tags = {tag: count for tag, count in tags_counter.items() if count >= min_products}

        print(f"  Total unique tags: {len(tags_counter)}")
        print(f"  Tags with {min_products}+ products: {len(eligible_tags)}")

        # Filter out brand tags if requested
        brand_tags_skipped = 0
        if skip_brands:
            filtered_tags = {}
            for tag, count in eligible_tags.items():
                if tag.lower() in known_vendors:
                    brand_tags_skipped += 1
                else:
                    filtered_tags[tag] = count
            eligible_tags = filtered_tags
            print(f"  Brand tags skipped: {brand_tags_skipped}")
            print(f"  Tags after brand filter: {len(eligible_tags)}")

        # Get existing collections
        existing = set()
        if skip_existing and not self.dry_run:
            existing = self.get_existing_collections()

        # Create collections
        total = len(eligible_tags)
        print(f"\nCreating {total} collections...")

        for i, (tag, count) in enumerate(sorted(eligible_tags.items()), 1):
            progress = f"[{i}/{total}]"
            print(f"{progress} {tag} ({count} products)")

            # Check if exists
            if tag.lower() in existing:
                print(f"  Skipped (already exists)")
                self.skipped_collections.append(tag)
                continue

            # Create collection
            if self.create_smart_collection(title=tag, tag=tag):
                self.created_collections.append(tag)
            else:
                self.failed_collections.append({"tag": tag, "count": count})

            # Small delay between creations
            if not self.dry_run:
                time.sleep(0.3)

        self._print_summary()

    def _create_vendor_collections(
        self,
        csv_path: str,
        min_products: int = 3,
        skip_existing: bool = True
    ):
        """Create collections from Vendor field (brand collections)."""
        print(f"\nCreating brand collections from Vendor field")

        # Count products per vendor
        vendor_counter = self._count_vendors(csv_path)

        # Filter by minimum products
        eligible_vendors = {v: c for v, c in vendor_counter.items() if c >= min_products}

        print(f"  Total unique vendors: {len(vendor_counter)}")
        print(f"  Vendors with {min_products}+ products: {len(eligible_vendors)}")

        # Get existing collections
        existing = set()
        if skip_existing and not self.dry_run:
            existing = self.get_existing_collections()

        # Create collections
        total = len(eligible_vendors)
        print(f"\nCreating {total} brand collections...")

        for i, (vendor, count) in enumerate(sorted(eligible_vendors.items()), 1):
            progress = f"[{i}/{total}]"
            print(f"{progress} {vendor} ({count} products)")

            # Check if exists
            if vendor.lower() in existing or f"brand-{vendor}".lower() in existing:
                print(f"  Skipped (already exists)")
                self.skipped_collections.append(vendor)
                continue

            # Create collection
            if self.create_vendor_collection(vendor=vendor):
                self.created_collections.append(vendor)
            else:
                self.failed_collections.append({"vendor": vendor, "count": count})

            # Small delay between creations
            if not self.dry_run:
                time.sleep(0.3)

        self._print_summary()

    def _print_summary(self):
        """Print creation summary."""
        print("\n" + "=" * 60)
        print("COLLECTION CREATION SUMMARY")
        print("=" * 60)

        if self.dry_run:
            print("  DRY RUN - No collections were actually created")
            print(f"  Would create: {len(self.created_collections)} collections")
        else:
            print(f"  Created: {len(self.created_collections)}")
            print(f"  Skipped (existing): {len(self.skipped_collections)}")
            print(f"  Failed: {len(self.failed_collections)}")

        if self.failed_collections:
            print("\n  Failed collections:")
            for fail in self.failed_collections[:10]:
                tag = fail.get('tag') or fail.get('vendor', 'Unknown')
                print(f"    - {tag}")

        print("=" * 60)
