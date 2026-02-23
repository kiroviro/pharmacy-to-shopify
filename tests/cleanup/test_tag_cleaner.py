"""Tests for TagCleaner — tag normalization, brand removal, L1 inference, promo removal."""

from unittest.mock import patch

import pytest

# Test config data — mirrors real YAML structure but small and deterministic
CATEGORIES = {
    "Козметика": ["Козметика за лице", "Козметика за тяло", "Слънцезащита"],
    "Мама и бебе": ["Бебешка козметика", "Бебешка храна"],
    "Витамини и добавки": ["Витамин C", "Мултивитамини"],
}

TAG_NORMALIZATION = {
    "козметика за лице": "Козметика за лице",
    "козметика за тяло": "Козметика за тяло",
    "витамин c": "Витамин C",
    "мултивитамини": "Мултивитамини",
    "слънцезащита": "Слънцезащита",
    "бебешка козметика": "Бебешка козметика",
}

VENDOR_DEFAULTS = {
    "unknown brand": ["Козметика", "Козметика за лице"],
}

PROMOTIONAL_PATTERNS = [
    "промоция",
    "% отстъпка",
    "ново",
    "black friday",
]


def _make_cleaner():
    """Create a TagCleaner with mocked config (no disk I/O)."""
    with patch("src.cleanup.tag_cleaner.load_categories", return_value=CATEGORIES), \
         patch("src.cleanup.tag_cleaner.load_tag_normalization", return_value=TAG_NORMALIZATION), \
         patch("src.cleanup.tag_cleaner.load_vendor_defaults", return_value=VENDOR_DEFAULTS), \
         patch("src.cleanup.tag_cleaner.load_promotional_patterns", return_value=PROMOTIONAL_PATTERNS):
        from src.cleanup.tag_cleaner import TagCleaner
        cleaner = TagCleaner(
            input_path="/dev/null",
            output_path="/dev/null",
        )
    # Pre-set vendor names (normally loaded from CSV by _load_vendors)
    cleaner.vendor_names = {"nivea", "la roche-posay", "testbrand"}
    return cleaner


class TestNormalizeTag:
    """Tag casing normalization via the normalization map."""

    def test_normalizes_lowercase_to_canonical(self):
        cleaner = _make_cleaner()
        assert cleaner._normalize_tag("козметика за лице") == "Козметика за лице"

    def test_already_canonical_unchanged(self):
        cleaner = _make_cleaner()
        assert cleaner._normalize_tag("Козметика за лице") == "Козметика за лице"

    def test_unknown_tag_passes_through(self):
        cleaner = _make_cleaner()
        assert cleaner._normalize_tag("Непозната категория") == "Непозната категория"

    def test_strips_whitespace(self):
        cleaner = _make_cleaner()
        assert cleaner._normalize_tag("  козметика за лице  ") == "Козметика за лице"

    def test_tracks_normalization_stat(self):
        cleaner = _make_cleaner()
        cleaner._normalize_tag("витамин c")
        assert sum(cleaner.stats["tags_normalized"].values()) == 1

    def test_no_stat_when_already_canonical(self):
        cleaner = _make_cleaner()
        cleaner._normalize_tag("Витамин C")
        assert sum(cleaner.stats["tags_normalized"].values()) == 0


class TestIsPromotional:
    """Detection of promotional/temporal tags."""

    def test_exact_promotional_pattern(self):
        cleaner = _make_cleaner()
        assert cleaner._is_promotional("Промоция") is True

    def test_promotional_substring(self):
        cleaner = _make_cleaner()
        assert cleaner._is_promotional("20% отстъпка") is True

    def test_case_insensitive(self):
        cleaner = _make_cleaner()
        assert cleaner._is_promotional("BLACK FRIDAY") is True

    def test_regular_tag_not_promotional(self):
        cleaner = _make_cleaner()
        assert cleaner._is_promotional("Козметика за лице") is False

    def test_empty_tag_not_promotional(self):
        cleaner = _make_cleaner()
        assert cleaner._is_promotional("") is False


class TestIsBrandTag:
    """Brand tag detection against vendor name."""

    def test_exact_vendor_match(self):
        cleaner = _make_cleaner()
        assert cleaner._is_brand_tag("Nivea", "Nivea") is True

    def test_vendor_in_known_set(self):
        cleaner = _make_cleaner()
        assert cleaner._is_brand_tag("La Roche-Posay", "SomeOtherVendor") is True

    def test_case_insensitive_vendor_match(self):
        cleaner = _make_cleaner()
        assert cleaner._is_brand_tag("nivea", "NIVEA") is True

    def test_non_brand_tag(self):
        cleaner = _make_cleaner()
        assert cleaner._is_brand_tag("Козметика за лице", "Nivea") is False


class TestGetL1Category:
    """L1 category inference from tag list."""

    def test_direct_l1_match(self):
        cleaner = _make_cleaner()
        result = cleaner._get_l1_category(["Козметика", "Козметика за лице"])
        assert result == "Козметика"

    def test_infer_from_subcategory(self):
        cleaner = _make_cleaner()
        result = cleaner._get_l1_category(["Козметика за лице"])
        assert result == "Козметика"

    def test_infer_from_baby_subcategory(self):
        cleaner = _make_cleaner()
        result = cleaner._get_l1_category(["Бебешка козметика"])
        assert result == "Мама и бебе"

    def test_no_match_returns_none(self):
        cleaner = _make_cleaner()
        result = cleaner._get_l1_category(["Непозната категория"])
        assert result is None

    def test_empty_tags_returns_none(self):
        cleaner = _make_cleaner()
        result = cleaner._get_l1_category([])
        assert result is None

    def test_first_matching_tag_wins(self):
        """When multiple tags match, the first one is used."""
        cleaner = _make_cleaner()
        result = cleaner._get_l1_category(["Бебешка козметика", "Козметика за лице"])
        assert result == "Мама и бебе"


class TestHasL1Category:
    """L1 category presence check in tag list."""

    def test_has_l1(self):
        cleaner = _make_cleaner()
        assert cleaner._has_l1_category(["Козметика", "Козметика за лице"]) is True

    def test_missing_l1(self):
        cleaner = _make_cleaner()
        assert cleaner._has_l1_category(["Козметика за лице"]) is False

    def test_empty_list(self):
        cleaner = _make_cleaner()
        assert cleaner._has_l1_category([]) is False


class TestCleanTags:
    """Integration tests for _clean_tags — the main transformation pipeline."""

    def test_empty_tags(self):
        cleaner = _make_cleaner()
        result, l1_added = cleaner._clean_tags("", "Nivea")
        assert result == ""
        assert l1_added is False

    def test_whitespace_only_tags(self):
        cleaner = _make_cleaner()
        result, l1_added = cleaner._clean_tags("   ", "Nivea")
        assert result == ""
        assert l1_added is False

    def test_removes_promotional_tag(self):
        cleaner = _make_cleaner()
        result, _ = cleaner._clean_tags("Козметика, Промоция, Козметика за лице", "SomeBrand")
        assert "Промоция" not in result
        assert "Козметика" in result

    def test_removes_brand_tag(self):
        cleaner = _make_cleaner()
        result, _ = cleaner._clean_tags("Козметика, Nivea, Козметика за лице", "Nivea")
        assert "Nivea" not in result
        assert "Козметика" in result

    def test_normalizes_casing(self):
        cleaner = _make_cleaner()
        result, _ = cleaner._clean_tags("Козметика, козметика за лице", "SomeBrand")
        assert "Козметика за лице" in result
        assert "козметика за лице" not in result

    def test_infers_l1_when_missing(self):
        """When only subcategory tags present, L1 is inferred and prepended."""
        cleaner = _make_cleaner()
        result, l1_added = cleaner._clean_tags("козметика за лице", "SomeBrand")
        assert l1_added is True
        tags = [t.strip() for t in result.split(",")]
        assert tags[0] == "Козметика"  # L1 prepended
        assert "Козметика за лице" in tags

    def test_no_l1_added_when_already_present(self):
        cleaner = _make_cleaner()
        result, l1_added = cleaner._clean_tags("Козметика, козметика за лице", "SomeBrand")
        assert l1_added is False

    def test_vendor_defaults_applied_when_no_l1(self):
        """Vendor default tags applied when no L1 can be inferred."""
        cleaner = _make_cleaner()
        result, _ = cleaner._clean_tags("Непозната категория", "Unknown Brand")
        tags = [t.strip() for t in result.split(",")]
        assert "Козметика" in tags
        assert "Козметика за лице" in tags

    def test_vendor_defaults_not_applied_when_l1_present(self):
        cleaner = _make_cleaner()
        result, _ = cleaner._clean_tags("Козметика, козметика за лице", "Unknown Brand")
        assert cleaner.stats["vendor_defaults_applied"]["Unknown Brand"] == 0

    def test_all_transformations_combined(self):
        """Brand removed, promo removed, casing normalized, L1 inferred."""
        cleaner = _make_cleaner()
        result, l1_added = cleaner._clean_tags(
            "Nivea, козметика за лице, Промоция, слънцезащита",
            "Nivea",
        )
        tags = [t.strip() for t in result.split(",")]
        assert "Nivea" not in tags
        assert "Промоция" not in tags
        assert "Козметика за лице" in tags  # normalized
        assert "Слънцезащита" in tags  # normalized
        assert "Козметика" in tags  # L1 inferred
        assert l1_added is True

    def test_no_duplicate_l1_when_vendor_default_matches_inferred(self):
        """Vendor defaults should not add duplicate tags."""
        cleaner = _make_cleaner()
        # "Unknown Brand" has defaults ["Козметика", "Козметика за лице"]
        # If L1 inference already added "Козметика", vendor defaults should not duplicate
        result, _ = cleaner._clean_tags("козметика за лице", "Unknown Brand")
        tags = [t.strip() for t in result.split(",")]
        # Count occurrences — "Козметика за лице" should appear only once
        assert tags.count("Козметика за лице") == 1

    def test_stats_tracked_correctly(self):
        cleaner = _make_cleaner()
        cleaner._clean_tags("Nivea, козметика за лице, Промоция", "Nivea")
        assert sum(cleaner.stats["brands_removed"].values()) == 1
        assert sum(cleaner.stats["promotional_removed"].values()) == 1
        assert sum(cleaner.stats["tags_normalized"].values()) == 1
        assert sum(cleaner.stats["l1_categories_added"].values()) == 1
