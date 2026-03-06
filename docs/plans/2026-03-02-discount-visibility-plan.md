# Discount Visibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make ~4,691 discounted products visible via a "Намаления" collection, menu item, product tags, and an updated sale badge style.

**Architecture:** Four independent changes: (1) extend `ShopifyCollectionCreator` to support compare_at_price-based collections, (2) add a top-level "Намаления" menu item to the mega menu, (3) create a tagger script that adds/removes a "Намаление" tag via Shopify GraphQL API, (4) switch the theme badge from "On Sale" text to "Спести X лв" format.

**Tech Stack:** Python, Shopify REST + GraphQL Admin API, pytest, Liquid theme config

---

### Task 1: Extend ShopifyCollectionCreator with sale collection support

**Files:**
- Modify: `src/shopify/collections.py:84-127` (`_create_collection` + new method)
- Test: `tests/shopify/test_collections.py`

**Step 1: Write the failing tests**

Add to `tests/shopify/test_collections.py`:

```python
# ---------------------------------------------------------------------------
# Sale collection (compare_at_price-based)
# ---------------------------------------------------------------------------

class TestCreateSaleCollection:
    def test_dry_run_returns_true(self):
        creator = _creator(dry_run=True)
        result = creator.create_sale_collection(title="Намаления")
        assert result is True

    def test_dry_run_prints_preview(self, capsys):
        creator = _creator(dry_run=True)
        creator.create_sale_collection(title="Намаления")
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Намаления" in captured.out
        assert "variant_compare_at_price" in captured.out

    def test_dry_run_does_not_call_api(self):
        creator = _creator(dry_run=True)
        calls = []
        creator.client.rest_request = lambda *a, **kw: calls.append((a, kw))
        creator.create_sale_collection(title="Намаления")
        assert len(calls) == 0

    def test_custom_relation_in_create_collection(self, capsys):
        creator = _creator(dry_run=True)
        creator._create_collection(
            title="Test",
            column="variant_compare_at_price",
            condition="0",
            relation="greater_than",
        )
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/shopify/test_collections.py::TestCreateSaleCollection -v`
Expected: FAIL — `create_sale_collection` and `relation` parameter don't exist yet

**Step 3: Implement the changes**

In `src/shopify/collections.py`, modify `_create_collection` to accept a `relation` parameter:

```python
def _create_collection(
    self,
    title: str,
    column: str,
    condition: str,
    handle_prefix: str = "",
    relation: str = "equals",
) -> bool:
    """
    Create a smart collection with a single rule.

    Args:
        title: Collection title
        column: Rule column (e.g. "tag", "vendor", "variant_compare_at_price")
        condition: Rule condition value
        handle_prefix: Optional prefix for the handle (e.g., "brand-")
        relation: Rule relation (e.g. "equals", "greater_than")

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
                    "relation": relation,
                    "condition": condition
                }
            ],
            "disjunctive": False,
            "published": True,
        }
    }

    if self.dry_run:
        print(f"  [DRY RUN] Would create: {title} ({column}: {relation} {condition})")
        return True

    result = self.client.rest_request("POST", "smart_collections.json", data)

    if result and "smart_collection" in result:
        collection_id = result["smart_collection"]["id"]
        logger.info("Created: %s (ID: %s)", title, collection_id)
        return True

    logger.error("Failed to create: %s", title)
    return False
```

Then add the convenience method:

```python
def create_sale_collection(self, title: str = "Намаления") -> bool:
    """Create a smart collection for products with compare_at_price set."""
    return self._create_collection(
        title=title,
        column="variant_compare_at_price",
        condition="0",
        relation="greater_than",
    )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/shopify/test_collections.py -v`
Expected: ALL PASS (existing tests still pass, new tests pass)

**Step 5: Commit**

```bash
git add src/shopify/collections.py tests/shopify/test_collections.py
git commit -m "feat: add sale collection support to ShopifyCollectionCreator"
```

---

### Task 2: Create sale collection script

**Files:**
- Create: `scripts/create_sale_collection.py`

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""
Create a "Намаления" smart collection in Shopify.

Auto-includes all products where compare_at_price > 0 (i.e., on sale).

Usage:
    python scripts/create_sale_collection.py              # Create collection
    python scripts/create_sale_collection.py --dry-run    # Preview only
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.credentials import load_shopify_credentials
from src.common.log_config import setup_logging
from src.shopify import ShopifyCollectionCreator

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Create a sale smart collection in Shopify"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, don't create the collection",
    )
    parser.add_argument(
        "--title",
        default="Намаления",
        help="Collection title (default: Намаления)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    shop, token = load_shopify_credentials()

    print("=" * 60)
    print("Sale Collection Creator")
    print("=" * 60)
    print(f"  Shop: {shop}")
    print(f"  Title: {args.title}")
    print(f"  Dry run: {args.dry_run}")

    creator = ShopifyCollectionCreator(
        shop=shop,
        access_token=token,
        dry_run=args.dry_run,
    )

    # Check if already exists
    if not args.dry_run:
        existing = creator.get_existing_collections()
        if args.title.lower() in existing:
            print(f"\n  Collection '{args.title}' already exists. Skipping.")
            return

    if creator.create_sale_collection(title=args.title):
        print(f"\n  Created collection: {args.title}")
    else:
        print(f"\n  Failed to create collection: {args.title}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 2: Verify it runs in dry-run**

Run: `python scripts/create_sale_collection.py --dry-run`
Expected: Prints "[DRY RUN] Would create: Намаления"

**Step 3: Commit**

```bash
git add scripts/create_sale_collection.py
git commit -m "feat: add script to create sale smart collection"
```

---

### Task 3: Add "Намаления" to mega menu

**Files:**
- Modify: `scripts/setup_navigation.py:27-226` (MENU list)

**Step 1: Add the "Намаления" item to the MENU list**

Append to the end of the `MENU` list (after the last entry for "Здравословно хранене"):

```python
    {
        'title': 'Намаления',
        'url': '/collections/namaleniya',
        'columns': [],
    },
```

This is a top-level item with no sub-columns — it links directly to the sale collection.

**Step 2: Handle the edge case in `build_items`**

The `build_items` function iterates `cat['columns']`. An empty list works fine (no sub-items). But verify — read the function:

```python
def build_items(menu_def):
    items = []
    for cat in menu_def:
        col_items = []
        for col in cat['columns']:  # empty list = no iteration = no sub-items
            ...
        items.append({
            'title': cat['title'],
            'type': 'HTTP',
            'url': cat['url'],
            'items': col_items,  # empty list — top-level link only
        })
    return items
```

This works correctly — empty `columns` means no `items` sub-list, which is a direct link.

**Step 3: Commit**

```bash
git add scripts/setup_navigation.py
git commit -m "feat: add Намаления to mega menu navigation"
```

**Note:** Run `python scripts/setup_navigation.py` to push the menu update to Shopify. This modifies the live menu.

---

### Task 4: Create discount tagger script

**Files:**
- Create: `src/shopify/tagger.py`
- Create: `scripts/tag_discounted_products.py`
- Create: `tests/shopify/test_tagger.py`

**Step 1: Write the failing tests for classification logic**

Create `tests/shopify/test_tagger.py`:

```python
"""Tests for src/shopify/tagger.py"""

import pytest

from src.shopify.tagger import DiscountTagger


def _tagger(dry_run: bool = True) -> DiscountTagger:
    """Return a dry-run tagger that never touches Shopify."""
    return DiscountTagger(
        shop="test-store",
        access_token="shpat_fake",
        dry_run=dry_run,
    )


class TestClassifyProduct:
    """Test the pure classification logic (no API calls)."""

    def test_discounted_without_tag_needs_add(self):
        tagger = _tagger()
        product = {
            "id": "gid://shopify/Product/1",
            "tags": ["Козметика"],
            "variants": {
                "edges": [
                    {"node": {"compareAtPrice": "20.00", "price": "15.00"}},
                ]
            },
        }
        assert tagger.classify_product(product) == "add"

    def test_discounted_with_tag_already_correct(self):
        tagger = _tagger()
        product = {
            "id": "gid://shopify/Product/2",
            "tags": ["Козметика", "Намаление"],
            "variants": {
                "edges": [
                    {"node": {"compareAtPrice": "20.00", "price": "15.00"}},
                ]
            },
        }
        assert tagger.classify_product(product) is None

    def test_not_discounted_with_tag_needs_remove(self):
        tagger = _tagger()
        product = {
            "id": "gid://shopify/Product/3",
            "tags": ["Козметика", "Намаление"],
            "variants": {
                "edges": [
                    {"node": {"compareAtPrice": None, "price": "15.00"}},
                ]
            },
        }
        assert tagger.classify_product(product) == "remove"

    def test_not_discounted_without_tag_already_correct(self):
        tagger = _tagger()
        product = {
            "id": "gid://shopify/Product/4",
            "tags": ["Козметика"],
            "variants": {
                "edges": [
                    {"node": {"compareAtPrice": None, "price": "15.00"}},
                ]
            },
        }
        assert tagger.classify_product(product) is None

    def test_compare_at_price_zero_not_discounted(self):
        tagger = _tagger()
        product = {
            "id": "gid://shopify/Product/5",
            "tags": [],
            "variants": {
                "edges": [
                    {"node": {"compareAtPrice": "0.00", "price": "15.00"}},
                ]
            },
        }
        assert tagger.classify_product(product) is None

    def test_compare_at_price_equals_price_not_discounted(self):
        tagger = _tagger()
        product = {
            "id": "gid://shopify/Product/6",
            "tags": [],
            "variants": {
                "edges": [
                    {"node": {"compareAtPrice": "15.00", "price": "15.00"}},
                ]
            },
        }
        assert tagger.classify_product(product) is None

    def test_multiple_variants_one_discounted(self):
        tagger = _tagger()
        product = {
            "id": "gid://shopify/Product/7",
            "tags": [],
            "variants": {
                "edges": [
                    {"node": {"compareAtPrice": None, "price": "10.00"}},
                    {"node": {"compareAtPrice": "25.00", "price": "20.00"}},
                ]
            },
        }
        assert tagger.classify_product(product) == "add"

    def test_custom_tag_name(self):
        tagger = DiscountTagger(
            shop="test-store",
            access_token="shpat_fake",
            dry_run=True,
            tag="On Sale",
        )
        product = {
            "id": "gid://shopify/Product/8",
            "tags": [],
            "variants": {
                "edges": [
                    {"node": {"compareAtPrice": "20.00", "price": "15.00"}},
                ]
            },
        }
        assert tagger.classify_product(product) == "add"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/shopify/test_tagger.py -v`
Expected: FAIL — `src.shopify.tagger` does not exist

**Step 3: Write the DiscountTagger implementation**

Create `src/shopify/tagger.py`:

```python
"""
Shopify Discount Tagger

Tags products as discounted based on compare_at_price vs price.
Uses Shopify GraphQL Admin API for efficient bulk operations.
"""

from __future__ import annotations

import logging

from .api_client import ShopifyAPIClient

logger = logging.getLogger(__name__)

PRODUCTS_QUERY = """
query products($cursor: String) {
    products(first: 250, after: $cursor) {
        edges {
            node {
                id
                tags
                variants(first: 100) {
                    edges {
                        node {
                            compareAtPrice
                            price
                        }
                    }
                }
            }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

TAGS_ADD_MUTATION = """
mutation tagsAdd($id: ID!, $tags: [String!]!) {
    tagsAdd(id: $id, tags: $tags) {
        userErrors { field message }
    }
}
"""

TAGS_REMOVE_MUTATION = """
mutation tagsRemove($id: ID!, $tags: [String!]!) {
    tagsRemove(id: $id, tags: $tags) {
        userErrors { field message }
    }
}
"""


class DiscountTagger:
    """
    Tags Shopify products based on discount status.

    A product is "discounted" if any variant has
    compare_at_price > price (and compare_at_price > 0).

    Usage:
        tagger = DiscountTagger(shop="store", access_token="shpat_xxx")
        tagger.run()
    """

    def __init__(
        self,
        shop: str,
        access_token: str,
        dry_run: bool = False,
        tag: str = "Намаление",
    ):
        self.client = ShopifyAPIClient(shop, access_token)
        self.dry_run = dry_run
        self.tag = tag

        # Stats
        self.total = 0
        self.added = 0
        self.removed = 0
        self.already_correct = 0

    @staticmethod
    def _is_discounted(product: dict) -> bool:
        """Check if any variant has compare_at_price > price."""
        for edge in product.get("variants", {}).get("edges", []):
            variant = edge["node"]
            compare_at = variant.get("compareAtPrice")
            price = variant.get("price")

            if not compare_at or not price:
                continue

            try:
                compare_at_f = float(compare_at)
                price_f = float(price)
            except (ValueError, TypeError):
                continue

            if compare_at_f > price_f:
                return True

        return False

    def classify_product(self, product: dict) -> str | None:
        """
        Classify a product's tag action needed.

        Returns:
            "add" if tag should be added,
            "remove" if tag should be removed,
            None if no change needed.
        """
        is_discounted = self._is_discounted(product)
        has_tag = self.tag in product.get("tags", [])

        if is_discounted and not has_tag:
            return "add"
        elif not is_discounted and has_tag:
            return "remove"
        return None

    def _add_tag(self, product_id: str) -> bool:
        """Add discount tag to a product."""
        if self.dry_run:
            return True

        result = self.client.graphql_request(
            TAGS_ADD_MUTATION,
            {"id": product_id, "tags": [self.tag]},
        )
        if not result:
            return False

        errors = result.get("tagsAdd", {}).get("userErrors", [])
        if errors:
            logger.error("Failed to add tag to %s: %s", product_id, errors)
            return False
        return True

    def _remove_tag(self, product_id: str) -> bool:
        """Remove discount tag from a product."""
        if self.dry_run:
            return True

        result = self.client.graphql_request(
            TAGS_REMOVE_MUTATION,
            {"id": product_id, "tags": [self.tag]},
        )
        if not result:
            return False

        errors = result.get("tagsRemove", {}).get("userErrors", [])
        if errors:
            logger.error("Failed to remove tag from %s: %s", product_id, errors)
            return False
        return True

    def run(self) -> None:
        """Process all products and update tags."""
        cursor = None
        page = 0

        while True:
            page += 1
            logger.info("Fetching products page %d...", page)

            result = self.client.graphql_request(
                PRODUCTS_QUERY,
                {"cursor": cursor},
            )
            if not result:
                logger.error("Failed to fetch products")
                break

            products_data = result.get("products", {})
            edges = products_data.get("edges", [])

            if not edges:
                break

            for edge in edges:
                product = edge["node"]
                self.total += 1
                action = self.classify_product(product)

                if action == "add":
                    product_id = product["id"]
                    if self._add_tag(product_id):
                        self.added += 1
                        logger.debug("Added tag to %s", product_id)
                    else:
                        logger.error("Failed to tag %s", product_id)
                elif action == "remove":
                    product_id = product["id"]
                    if self._remove_tag(product_id):
                        self.removed += 1
                        logger.debug("Removed tag from %s", product_id)
                    else:
                        logger.error("Failed to untag %s", product_id)
                else:
                    self.already_correct += 1

            page_info = products_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info["endCursor"]

        self._print_summary()

    def _print_summary(self) -> None:
        """Print tagging summary."""
        print("\n" + "=" * 60)
        print("DISCOUNT TAGGING SUMMARY")
        print("=" * 60)
        if self.dry_run:
            print("  DRY RUN — no changes were made")
        print(f"  Total products scanned: {self.total}")
        print(f"  Tag added:              {self.added}")
        print(f"  Tag removed:            {self.removed}")
        print(f"  Already correct:        {self.already_correct}")
        print("=" * 60)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/shopify/test_tagger.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/shopify/tagger.py tests/shopify/test_tagger.py
git commit -m "feat: add DiscountTagger for tagging sale products"
```

**Step 6: Register in package __init__**

Add to `src/shopify/__init__.py`:

```python
from .tagger import DiscountTagger
```

And add `'DiscountTagger'` to `__all__`.

**Step 7: Create the CLI script**

Create `scripts/tag_discounted_products.py`:

```python
#!/usr/bin/env python3
"""
Tag discounted products in Shopify.

Scans all products and adds/removes a "Намаление" tag based on whether
any variant has compare_at_price > price.

Usage:
    python scripts/tag_discounted_products.py              # Tag products
    python scripts/tag_discounted_products.py --dry-run    # Preview only
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common.credentials import load_shopify_credentials
from src.common.log_config import setup_logging
from src.shopify.tagger import DiscountTagger

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Tag discounted products in Shopify"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, don't modify products",
    )
    parser.add_argument(
        "--tag",
        default="Намаление",
        help="Tag name to apply (default: Намаление)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    shop, token = load_shopify_credentials()

    print("=" * 60)
    print("Discount Product Tagger")
    print("=" * 60)
    print(f"  Shop: {shop}")
    print(f"  Tag: {args.tag}")
    print(f"  Dry run: {args.dry_run}")

    tagger = DiscountTagger(
        shop=shop,
        access_token=token,
        dry_run=args.dry_run,
        tag=args.tag,
    )
    tagger.run()


if __name__ == "__main__":
    main()
```

**Step 8: Commit**

```bash
git add src/shopify/__init__.py scripts/tag_discounted_products.py
git commit -m "feat: add CLI script for tagging discounted products"
```

---

### Task 5: Update badge style to show savings amount

**Files:**
- Modify: `../../viapharma.us-theme/config/settings_data.json` (line 84)

**Step 1: Change badge style**

In `settings_data.json`, change:
- Line 84: `"sale_badge_style": "sale"` → `"sale_badge_style": "saving"`

And add the text template (after the `sale_badge_style` line, or in the same settings block):
- Add: `"saving_badge_text": "Спести"`

This makes badges render as "Спести 5.40 лв" (the theme Liquid automatically appends the calculated savings via `money_without_trailing_zeros`).

**Step 2: Push to Shopify**

Run: `python scripts/push_theme.py config/settings_data.json`
Expected: Theme settings updated on live store.

**Step 3: Wait ~2 min for CDN propagation, then verify**

Take a screenshot of a discounted product card to confirm the badge shows "Спести X лв".

**Step 4: Commit theme change**

In the viapharma.us-theme repo:
```bash
cd ../../viapharma.us-theme
git add config/settings_data.json
git commit -m "feat: switch sale badge to show savings amount"
```

---

### Execution Order

Tasks 1-4 are in the pharmacy-to-shopify repo. Task 5 is in viapharma.us-theme.

Dependencies:
- Task 2 depends on Task 1 (uses `create_sale_collection` method)
- Tasks 3, 4, 5 are independent of each other and Task 1/2
- Task 3 should be run AFTER Task 2 (collection must exist before menu links to it)

Recommended order: **1 → 2 → 3 → 4 → 5** (linear, simple)

### Post-Implementation: Running the scripts

After all code is committed, run against live Shopify:

```bash
# 1. Create the sale collection
python scripts/create_sale_collection.py

# 2. Update the mega menu to include "Намаления"
python scripts/setup_navigation.py

# 3. Tag all discounted products
python scripts/tag_discounted_products.py

# 4. Push badge style change (in pharmacy-to-shopify repo)
python scripts/push_theme.py config/settings_data.json
```
