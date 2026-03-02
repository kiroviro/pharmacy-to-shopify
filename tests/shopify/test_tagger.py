"""Tests for src/shopify/tagger.py"""

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
