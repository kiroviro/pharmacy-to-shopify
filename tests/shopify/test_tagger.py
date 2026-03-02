"""Tests for src/shopify/tagger.py"""

from unittest.mock import MagicMock

from src.shopify.tagger import DiscountTagger


def _tagger(dry_run: bool = True) -> DiscountTagger:
    """Return a dry-run tagger that never touches Shopify."""
    return DiscountTagger(
        shop="test-store",
        access_token="shpat_fake",
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# classify_product (pure logic, no API)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# _mutate_tags_batch
# ---------------------------------------------------------------------------


class TestMutateTagsBatch:
    """Test batched mutation logic with mocked API."""

    def test_dry_run_returns_count_without_api(self):
        tagger = _tagger(dry_run=True)
        tagger.client.graphql_request = MagicMock()
        result = tagger._mutate_tags_batch("tagsAdd", ["gid://shopify/Product/1", "gid://shopify/Product/2"])
        assert result == 2
        tagger.client.graphql_request.assert_not_called()

    def test_empty_list_returns_zero(self):
        tagger = _tagger(dry_run=False)
        tagger.client.graphql_request = MagicMock()
        result = tagger._mutate_tags_batch("tagsAdd", [])
        assert result == 0
        tagger.client.graphql_request.assert_not_called()

    def test_successful_batch_returns_count(self):
        tagger = _tagger(dry_run=False)
        tagger.client.graphql_request = MagicMock(
            return_value={
                "t0": {"userErrors": []},
                "t1": {"userErrors": []},
            }
        )
        result = tagger._mutate_tags_batch("tagsAdd", ["gid://shopify/Product/1", "gid://shopify/Product/2"])
        assert result == 2

    def test_partial_failure_returns_success_count(self):
        tagger = _tagger(dry_run=False)
        tagger.client.graphql_request = MagicMock(
            return_value={
                "t0": {"userErrors": []},
                "t1": {"userErrors": [{"field": "id", "message": "Not found"}]},
            }
        )
        result = tagger._mutate_tags_batch("tagsAdd", ["gid://shopify/Product/1", "gid://shopify/Product/2"])
        assert result == 1

    def test_api_failure_returns_zero(self):
        tagger = _tagger(dry_run=False)
        tagger.client.graphql_request = MagicMock(return_value=None)
        result = tagger._mutate_tags_batch("tagsAdd", ["gid://shopify/Product/1"])
        assert result == 0


# ---------------------------------------------------------------------------
# _flush_batch stats tracking
# ---------------------------------------------------------------------------


class TestFlushBatch:
    """Test that _flush_batch updates stats correctly."""

    def test_add_batch_updates_added_counter(self):
        tagger = _tagger(dry_run=True)
        tagger._flush_batch("tagsAdd", ["gid://shopify/Product/1", "gid://shopify/Product/2"])
        assert tagger.added == 2
        assert tagger.failed == 0

    def test_remove_batch_updates_removed_counter(self):
        tagger = _tagger(dry_run=True)
        tagger._flush_batch("tagsRemove", ["gid://shopify/Product/1"])
        assert tagger.removed == 1
        assert tagger.failed == 0

    def test_failed_mutations_tracked(self):
        tagger = _tagger(dry_run=False)
        # Mock partial failure: 1 success, 1 failure
        tagger.client.graphql_request = MagicMock(
            return_value={
                "t0": {"userErrors": []},
                "t1": {"userErrors": [{"field": "id", "message": "error"}]},
            }
        )
        tagger._flush_batch("tagsAdd", ["gid://shopify/Product/1", "gid://shopify/Product/2"])
        assert tagger.added == 1
        assert tagger.failed == 1
