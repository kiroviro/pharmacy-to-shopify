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
