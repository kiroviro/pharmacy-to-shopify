"""
Shopify Collection Creator

Creates smart collections in Shopify based on tags from a product CSV.
Each unique tag becomes a smart collection with rule: "tag equals [tag_name]"
"""

import csv
import logging
import time
from collections import Counter
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

from ..common.csv_utils import configure_csv
from ..common.transliteration import generate_handle
from .api_client import ShopifyAPIClient

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
        logger.info("Fetching existing collections...")

        existing = set()
        endpoint = "smart_collections.json?limit=250"

        while endpoint:
            result = self.client.rest_request("GET", endpoint)
            if not result:
                break

            collections = result.get("smart_collections", [])
            if not collections:
                break

            for collection in collections:
                existing.add(collection.get("title", "").lower())

            # Paginate using since_id when a full page is returned
            if len(collections) == 250:
                last_id = collections[-1]["id"]
                endpoint = f"smart_collections.json?limit=250&since_id={last_id}"
            else:
                endpoint = None

        logger.info("Found %d existing smart collections", len(existing))
        return existing

    def _create_collection(self, title: str, column: str, condition: str, handle_prefix: str = "") -> bool:
        """
        Create a smart collection with a single rule.

        Args:
            title: Collection title
            column: Rule column ("tag" or "vendor")
            condition: Rule condition value
            handle_prefix: Optional prefix for the handle (e.g., "brand-")

        Returns:
            True if created successfully
        """
        handle = generate_handle(title, prefix=handle_prefix)

        data = {
            "smart_collection": {
                "title": title,
                "handle": handle,
                "rules": [
                    {
                        "column": column,
                        "relation": "equals",
                        "condition": condition
                    }
                ],
                "disjunctive": False,
                "published": True,
            }
        }

        if self.dry_run:
            print(f"  [DRY RUN] Would create: {title} ({column}: {condition})")
            return True

        result = self.client.rest_request("POST", "smart_collections.json", data)

        if result and "smart_collection" in result:
            collection_id = result["smart_collection"]["id"]
            logger.info("Created: %s (ID: %s)", title, collection_id)
            return True
        else:
            logger.error("Failed to create: %s", title)
            return False

    def create_smart_collection(self, title: str, tag: str) -> bool:
        """Create a smart collection with tag-based rule."""
        return self._create_collection(title, "tag", tag)

    def create_vendor_collection(self, vendor: str) -> bool:
        """Create a smart collection based on vendor (brand)."""
        return self._create_collection(vendor, "vendor", vendor, handle_prefix="brand-")

    def _load_vendors_from_csv(self, csv_path: str) -> Set[str]:
        """Load all unique vendor names from CSV (lowercase)."""
        vendors = set()
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vendor = row.get("Vendor", "").strip()
                    if vendor:
                        vendors.add(vendor.lower())
        except (OSError, csv.Error) as e:
            logger.error("Failed to read CSV %s: %s", csv_path, e)
        return vendors

    def _count_vendors(self, csv_path: str) -> Counter:
        """Count products per vendor."""
        vendor_counter = Counter()
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("Title", "").strip():
                        continue
                    vendor = row.get("Vendor", "").strip()
                    if vendor:
                        vendor_counter[vendor] += 1
        except (OSError, csv.Error) as e:
            logger.error("Failed to read CSV %s: %s", csv_path, e)
        return vendor_counter

    def _count_tags(self, csv_path: str) -> Counter:
        """Count products per tag."""
        tags_counter = Counter()
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get("Title", "").strip():
                        continue
                    tags_str = row.get("Tags", "")
                    if tags_str:
                        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                        tags_counter.update(tags)
        except (OSError, csv.Error) as e:
            logger.error("Failed to read CSV %s: %s", csv_path, e)
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
        logger.info("Loaded %d unique vendors from CSV", len(known_vendors))

        if vendors_only:
            self._create_vendor_collections(csv_path, min_products, skip_existing)
            return

        logger.info("Reading tags from: %s", csv_path)

        # Count tags
        tags_counter = self._count_tags(csv_path)

        # Filter by minimum products
        eligible_tags = {tag: count for tag, count in tags_counter.items() if count >= min_products}

        logger.info("Total unique tags: %d", len(tags_counter))
        logger.info("Tags with %d+ products: %d", min_products, len(eligible_tags))

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
            logger.info("Brand tags skipped: %d", brand_tags_skipped)
            logger.info("Tags after brand filter: %d", len(eligible_tags))

        # Get existing collections
        existing = set()
        if skip_existing and not self.dry_run:
            existing = self.get_existing_collections()

        # Create collections
        total = len(eligible_tags)
        logger.info("Creating %d collections...", total)

        for i, (tag, count) in enumerate(sorted(eligible_tags.items()), 1):
            logger.info("[%d/%d] %s (%d products)", i, total, tag, count)

            # Check if exists
            if tag.lower() in existing:
                logger.info("Skipped (already exists)")
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
        logger.info("Creating brand collections from Vendor field")

        # Count products per vendor
        vendor_counter = self._count_vendors(csv_path)

        # Filter by minimum products
        eligible_vendors = {v: c for v, c in vendor_counter.items() if c >= min_products}

        logger.info("Total unique vendors: %d", len(vendor_counter))
        logger.info("Vendors with %d+ products: %d", min_products, len(eligible_vendors))

        # Get existing collections
        existing = set()
        if skip_existing and not self.dry_run:
            existing = self.get_existing_collections()

        # Create collections
        total = len(eligible_vendors)
        logger.info("Creating %d brand collections...", total)

        for i, (vendor, count) in enumerate(sorted(eligible_vendors.items()), 1):
            logger.info("[%d/%d] %s (%d products)", i, total, vendor, count)

            # Check if exists
            if vendor.lower() in existing or f"brand-{vendor}".lower() in existing:
                logger.info("Skipped (already exists)")
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
