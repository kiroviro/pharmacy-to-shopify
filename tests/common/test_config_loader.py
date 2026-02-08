"""Tests for src/common/config_loader.py"""

import pytest

from src.common.config_loader import (
    build_subcategory_to_l1_map,
    get_brands_lowercase_map,
    get_l1_category_names,
    load_categories,
    load_config,
    load_known_brands,
    load_seo_settings,
)


class TestBuildSubcategoryToL1Map:
    def test_builds_mapping(self, sample_categories):
        result = build_subcategory_to_l1_map(sample_categories)
        assert result["козметика за лице"] == "Козметика"
        assert result["бебешка козметика"] == "Мама и бебе"
        assert result["витамин c"] == "Витамини и добавки"

    def test_keys_are_lowercase(self, sample_categories):
        result = build_subcategory_to_l1_map(sample_categories)
        for key in result:
            assert key == key.lower()

    def test_empty_categories(self):
        result = build_subcategory_to_l1_map({})
        assert result == {}


class TestGetL1CategoryNames:
    def test_returns_lowercase_set(self, sample_categories):
        result = get_l1_category_names(sample_categories)
        assert "козметика" in result
        assert "мама и бебе" in result
        assert "витамини и добавки" in result

    def test_returns_set_type(self, sample_categories):
        result = get_l1_category_names(sample_categories)
        assert isinstance(result, set)

    def test_empty_categories(self):
        result = get_l1_category_names({})
        assert result == set()


class TestGetBrandsLowercaseMap:
    def test_builds_mapping(self, sample_known_brands):
        result = get_brands_lowercase_map(sample_known_brands)
        assert result["testbrand"] == "TestBrand"
        assert result["nivea"] == "Nivea"
        assert result["abopharma"] == "AboPharma"

    def test_preserves_canonical_case(self, sample_known_brands):
        result = get_brands_lowercase_map(sample_known_brands)
        assert result["la roche-posay"] == "La Roche-Posay"
        assert result["nature's way"] == "Nature's Way"

    def test_empty_brands(self):
        result = get_brands_lowercase_map(set())
        assert result == {}


class TestLoadFromConfigFiles:
    """Tests that load real config YAML files from the repo."""

    def test_load_categories_returns_dict(self):
        categories = load_categories()
        assert isinstance(categories, dict)
        assert len(categories) > 0

    def test_load_known_brands_returns_set(self):
        brands = load_known_brands()
        assert isinstance(brands, set)
        assert len(brands) > 0

    def test_load_seo_settings_has_store_name(self):
        settings = load_seo_settings()
        assert "store_name" in settings

    def test_load_config_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("nonexistent_file.yaml")
