"""
Shopify Menu Creator

Creates hierarchical navigation menus in Shopify based on product categories.
Uses the Shopify Admin API (GraphQL) to create menus with nested items.
"""

import csv
import logging
from collections import Counter
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

from ..common.config_loader import load_categories
from ..common.csv_utils import configure_csv
from ..common.transliteration import generate_handle
from .api_client import ShopifyAPIClient

# Configure CSV for large fields
configure_csv()


class ShopifyMenuCreator:
    """
    Creates navigation menus in Shopify via GraphQL API.

    Usage:
        creator = ShopifyMenuCreator(
            shop="my-store",
            access_token="shpat_xxx",
            dry_run=True
        )
        creator.create_main_menu(csv_path="products.csv", min_products=3)
        creator.create_brands_menu(csv_path="products.csv", max_brands=50)
    """

    def __init__(self, shop: str, access_token: str, dry_run: bool = False):
        """
        Initialize the menu creator.

        Args:
            shop: Shop name (without .myshopify.com) or full domain
            access_token: Shopify Admin API access token
            dry_run: If True, only preview without creating
        """
        self.client = ShopifyAPIClient(shop, access_token)
        self.dry_run = dry_run

        # Load menu hierarchy from YAML config
        self.menu_hierarchy = load_categories()

    def get_existing_menus(self) -> Dict[str, str]:
        """Fetch existing menus and return {handle: id} mapping."""
        logger.info("Fetching existing menus...")

        query = """
        query {
            menus(first: 50) {
                edges {
                    node {
                        id
                        handle
                        title
                    }
                }
            }
        }
        """

        result = self.client.graphql_request(query)
        if not result:
            return {}

        menus = {}
        for edge in result.get("menus", {}).get("edges", []):
            node = edge["node"]
            menus[node["handle"]] = node["id"]
            logger.info("Found menu: %s (%s)", node['title'], node['handle'])

        return menus

    def get_collection_id_by_handle(self, handle: str) -> Optional[str]:
        """Get collection ID by its handle."""
        query = """
        query getCollection($handle: String!) {
            collectionByHandle(handle: $handle) {
                id
            }
        }
        """

        result = self.client.graphql_request(query, {"handle": handle})
        if result and result.get("collectionByHandle"):
            return result["collectionByHandle"]["id"]
        return None

    def create_menu(self, title: str, handle: str) -> Optional[str]:
        """Create a new menu and return its ID."""
        if self.dry_run:
            print(f"  [DRY RUN] Would create menu: {title} ({handle})")
            return f"gid://shopify/Menu/dry-run-{handle}"

        mutation = """
        mutation menuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
            menuCreate(title: $title, handle: $handle, items: $items) {
                menu {
                    id
                    handle
                    title
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        variables = {
            "title": title,
            "handle": handle,
            "items": []
        }

        result = self.client.graphql_request(mutation, variables)

        if result and result.get("menuCreate", {}).get("menu"):
            menu = result["menuCreate"]["menu"]
            logger.info("Created menu: %s (ID: %s)", menu['title'], menu['id'])
            return menu["id"]

        errors = result.get("menuCreate", {}).get("userErrors", []) if result else []
        if errors:
            logger.error("Failed to create menu: %s", errors)

        return None

    def add_menu_item(
        self,
        menu_id: str,
        title: str,
        url: str = None,
        resource_id: str = None,
        parent_item_id: str = None
    ) -> Optional[str]:
        """Add an item to a menu."""
        if self.dry_run:
            indent = "    " if parent_item_id else "  "
            target = url or resource_id or "(no link)"
            print(f"{indent}[DRY RUN] Would add: {title} -> {target}")
            return f"gid://shopify/MenuItem/dry-run-{generate_handle(title)}"

        # Build the item input
        item_input = {"title": title}

        if resource_id:
            item_input["resourceId"] = resource_id
        elif url:
            item_input["url"] = url

        mutation = """
        mutation menuItemCreate($menuId: ID!, $item: MenuItemCreateInput!) {
            menuItemCreate(menuId: $menuId, menuItem: $item) {
                menuItem {
                    id
                    title
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        variables = {
            "menuId": menu_id,
            "item": item_input
        }

        result = self.client.graphql_request(mutation, variables)

        if result and result.get("menuItemCreate", {}).get("menuItem"):
            item = result["menuItemCreate"]["menuItem"]
            indent = "    " if parent_item_id else "  "
            logger.info("%sAdded: %s", indent, item['title'])
            return item["id"]

        errors = result.get("menuItemCreate", {}).get("userErrors", []) if result else []
        if errors:
            logger.error("Failed to add menu item: %s", errors)

        return None

    def build_collection_url(self, handle: str) -> str:
        """Build collection URL from handle."""
        return f"/collections/{handle}"

    def analyze_tags_from_csv(self, csv_path: str, min_products: int = 3) -> Dict[str, int]:
        """Analyze tags from CSV and return tag counts."""
        tag_counts = Counter()

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('Title', '').strip():
                    continue
                tags_str = row.get('Tags', '')
                if tags_str:
                    tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                    tag_counts.update(tags)

        return {tag: count for tag, count in tag_counts.items() if count >= min_products}

    def analyze_vendors_from_csv(self, csv_path: str, min_products: int = 3) -> Dict[str, int]:
        """Analyze vendors from CSV and return vendor counts."""
        vendor_counts = Counter()

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('Title', '').strip():
                    continue
                vendor = row.get('Vendor', '').strip()
                if vendor:
                    vendor_counts[vendor] += 1

        return {v: c for v, c in vendor_counts.items() if c >= min_products}

    def create_main_menu(
        self,
        csv_path: str,
        menu_handle: str = "categories-menu",
        min_products: int = 3
    ):
        """
        Create the main navigation menu with category hierarchy.

        Args:
            csv_path: Path to products CSV (to verify collections exist)
            menu_handle: Handle for the menu
            min_products: Minimum products for a category to be included
        """
        print(f"\n{'='*60}")
        print("Creating Categories Navigation Menu")
        print(f"{'='*60}")

        # Analyze which tags actually exist in the data
        tag_counts = self.analyze_tags_from_csv(csv_path, min_products)
        available_tags = set(tag_counts.keys())

        logger.info("Found %d tags with %d+ products", len(available_tags), min_products)

        # Check for existing menus
        existing_menus = self.get_existing_menus()

        # Create or get menu ID
        if menu_handle in existing_menus:
            logger.warning("Menu '%s' already exists. Skipping creation.", menu_handle)
            logger.info("Note: To update an existing menu, delete it first in Shopify Admin.")
            return

        logger.info("Building menu structure...")

        # Build menu items with L1 categories (L2 as nested items)
        menu_items = []
        for l1_category, l2_subcategories in self.menu_hierarchy.items():
            # Check if L1 category has products
            if l1_category not in available_tags:
                logger.debug("Skipping %s (not in data)", l1_category)
                continue

            l1_handle = generate_handle(l1_category)
            l1_url = self.build_collection_url(l1_handle)

            # Build L2 items
            l2_items = []
            for l2_category in l2_subcategories:
                if l2_category not in available_tags:
                    continue
                l2_handle = generate_handle(l2_category)
                l2_url = self.build_collection_url(l2_handle)
                l2_items.append({
                    "title": l2_category,
                    "url": l2_url,
                    "type": "HTTP"
                })

            logger.info("%s (%d products) with %d subcategories", l1_category, tag_counts.get(l1_category, 0), len(l2_items))

            # Add L1 with nested L2 items
            menu_items.append({
                "title": l1_category,
                "url": l1_url,
                "type": "HTTP",
                "items": l2_items
            })

        # Create menu with all items
        menu_id = self.create_menu_with_items(
            title="Categories",
            handle=menu_handle,
            items=menu_items
        )

        if menu_id:
            logger.info("Main menu creation complete!")
        else:
            logger.error("Failed to create main menu")

    def create_menu_with_items(self, title: str, handle: str, items: List[Dict]) -> Optional[str]:
        """Create a menu with items in a single API call."""
        if self.dry_run:
            print(f"  [DRY RUN] Would create menu: {title} ({handle}) with {len(items)} items")
            return f"gid://shopify/Menu/dry-run-{handle}"

        mutation = """
        mutation menuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
            menuCreate(title: $title, handle: $handle, items: $items) {
                menu {
                    id
                    handle
                    title
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """

        variables = {
            "title": title,
            "handle": handle,
            "items": items
        }

        result = self.client.graphql_request(mutation, variables)

        if result and result.get("menuCreate", {}).get("menu"):
            menu = result["menuCreate"]["menu"]
            logger.info("Created menu: %s with %d items (ID: %s)", menu['title'], len(items), menu['id'])
            return menu["id"]

        errors = result.get("menuCreate", {}).get("userErrors", []) if result else []
        if errors:
            logger.error("Failed to create menu: %s", errors)

        return None

    def create_brands_menu(
        self,
        csv_path: str,
        menu_handle: str = "brands-menu",
        min_products: int = 3,
        max_brands: int = 50
    ):
        """
        Create a brands navigation menu from Vendor field.

        Args:
            csv_path: Path to products CSV
            menu_handle: Handle for the brands menu
            min_products: Minimum products for a brand to be included
            max_brands: Maximum number of brands to include in menu
        """
        print(f"\n{'='*60}")
        print("Creating Brands Menu")
        print(f"{'='*60}")

        # Get vendor counts
        vendor_counts = self.analyze_vendors_from_csv(csv_path, min_products)
        logger.info("Found %d brands with %d+ products", len(vendor_counts), min_products)

        # Sort by product count and take top N
        top_brands = sorted(vendor_counts.items(), key=lambda x: -x[1])[:max_brands]
        logger.info("Including top %d brands in menu", len(top_brands))

        # Check for existing menus
        existing_menus = self.get_existing_menus()

        if menu_handle in existing_menus:
            logger.warning("Menu '%s' already exists. Skipping creation.", menu_handle)
            return

        # Build menu items list
        logger.info("Building menu items...")
        menu_items = []
        for vendor, count in top_brands:
            # Brand collections use "brand-{handle}" pattern
            handle = generate_handle(vendor, prefix="brand-")
            url = self.build_collection_url(handle)
            logger.info("%s (%d products) -> %s", vendor, count, url)
            menu_items.append({
                "title": vendor,
                "url": url,
                "type": "HTTP"
            })

        # Create menu with all items
        menu_id = self.create_menu_with_items(
            title="Brands",
            handle=menu_handle,
            items=menu_items
        )

        if menu_id:
            logger.info("Brands menu creation complete!")
        else:
            logger.error("Failed to create brands menu")

    def preview_menu_structure(self, csv_path: str, min_products: int = 3):
        """Preview the menu structure that would be created."""
        print(f"\n{'='*60}")
        print("MENU STRUCTURE PREVIEW")
        print(f"{'='*60}")

        tag_counts = self.analyze_tags_from_csv(csv_path, min_products)
        vendor_counts = self.analyze_vendors_from_csv(csv_path, min_products)

        print(f"\nTags with {min_products}+ products: {len(tag_counts)}")
        print(f"Brands with {min_products}+ products: {len(vendor_counts)}")

        print("\n--- MAIN MENU ---")
        for l1_category, l2_subcategories in self.menu_hierarchy.items():
            if l1_category not in tag_counts:
                continue

            print(f"\n{l1_category} ({tag_counts[l1_category]} products)")
            for l2 in l2_subcategories:
                if l2 in tag_counts:
                    print(f"  - {l2} ({tag_counts[l2]} products)")

        print("\n--- TOP BRANDS ---")
        top_brands = sorted(vendor_counts.items(), key=lambda x: -x[1])[:20]
        for vendor, count in top_brands:
            print(f"  {vendor} ({count} products)")

        if len(vendor_counts) > 20:
            print(f"  ... and {len(vendor_counts) - 20} more brands")
