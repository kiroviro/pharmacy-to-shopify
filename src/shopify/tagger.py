"""
Shopify Discount Tagger

Tags products as discounted based on compare_at_price vs price.
Uses Shopify GraphQL Admin API with batched mutations for efficiency.
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

BATCH_SIZE = 10  # mutations per GraphQL request


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
        self.failed = 0
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

    def _mutate_tags_batch(self, operation: str, product_ids: list[str]) -> int:
        """
        Execute a batched tag mutation for multiple products.

        Args:
            operation: "tagsAdd" or "tagsRemove"
            product_ids: list of Shopify product GIDs

        Returns:
            Number of successfully mutated products.
        """
        if self.dry_run or not product_ids:
            return len(product_ids)

        _VALID_OPS = ("tagsAdd", "tagsRemove")
        if operation not in _VALID_OPS:
            raise ValueError(f"Invalid tag operation: {operation!r} (expected one of {_VALID_OPS})")

        # Build aliased mutations: t0: tagsAdd(...), t1: tagsAdd(...), ...
        fragments = []
        for i, pid in enumerate(product_ids):
            escaped_id = pid.replace("\\", "\\\\").replace('"', '\\"')
            escaped_tag = self.tag.replace("\\", "\\\\").replace('"', '\\"')
            fragments.append(
                f't{i}: {operation}(id: "{escaped_id}", tags: ["{escaped_tag}"]) {{ userErrors {{ field message }} }}'
            )

        query = "mutation {\n" + "\n".join(fragments) + "\n}"
        result = self.client.graphql_request(query)

        if not result:
            logger.error("Batch %s failed entirely (%d products)", operation, len(product_ids))
            return 0

        success = 0
        for i, pid in enumerate(product_ids):
            alias = f"t{i}"
            entry = result.get(alias, {})
            errors = entry.get("userErrors", [])
            if errors:
                logger.error("Failed %s on %s: %s", operation, pid, errors)
            else:
                success += 1

        return success

    def run(self) -> None:
        """Process all products and update tags."""
        # Reset stats for re-runs
        self.total = 0
        self.added = 0
        self.removed = 0
        self.failed = 0
        self.already_correct = 0

        cursor = None
        page = 0
        add_batch: list[str] = []
        remove_batch: list[str] = []

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
                    add_batch.append(product["id"])
                elif action == "remove":
                    remove_batch.append(product["id"])
                else:
                    self.already_correct += 1

                # Flush add batch when full
                if len(add_batch) >= BATCH_SIZE:
                    self._flush_batch("tagsAdd", add_batch)
                    add_batch = []

                # Flush remove batch when full
                if len(remove_batch) >= BATCH_SIZE:
                    self._flush_batch("tagsRemove", remove_batch)
                    remove_batch = []

            page_info = products_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info["endCursor"]

        # Flush remaining
        if add_batch:
            self._flush_batch("tagsAdd", add_batch)
        if remove_batch:
            self._flush_batch("tagsRemove", remove_batch)

        self._print_summary()

    def _flush_batch(self, operation: str, product_ids: list[str]) -> None:
        """Flush a batch of tag mutations and update stats."""
        is_add = operation == "tagsAdd"
        success = self._mutate_tags_batch(operation, product_ids)
        failed = len(product_ids) - success

        if is_add:
            self.added += success
        else:
            self.removed += success
        self.failed += failed

        if success:
            verb = "Added" if is_add else "Removed"
            logger.debug("%s tag on %d products", verb, success)
        if failed:
            verb = "add" if is_add else "remove"
            logger.error("Failed to %s tag on %d products", verb, failed)

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
        if self.failed:
            print(f"  Failed:                 {self.failed}")
        print("=" * 60)
