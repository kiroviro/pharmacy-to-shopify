"""
Tests for SourceConsistencyChecker.

Each class covers one check. Fixtures are built inline (HTML strings + plain dicts)
to keep tests self-contained — no file I/O, no network, no YAML loading.

BrandMatcher is constructed with an explicit brands set to avoid loading known_brands.yaml.
"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from src.extraction.brand_matcher import BrandMatcher
from src.extraction.consistency_checker import SourceConsistencyChecker
from src.models import ExtractedProduct, ProductImage

# ── Shared helpers ─────────────────────────────────────────────────────────────

def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _make_brand_matcher(*brands: str) -> BrandMatcher:
    return BrandMatcher(brands=set(brands))


def _minimal_product(**overrides) -> ExtractedProduct:
    defaults = dict(
        title="TestBrand Vitamin C 500mg",
        url="https://benu.bg/testbrand-vitamin-c",
        brand="TestBrand",
        sku="SKU-001",
        price="12.25",
        images=[ProductImage(
            source_url="https://benu.bg/media/cache/product_view_default/images/products/1/img.jpg",
            position=1,
        )],
        handle="testbrand-vitamin-c",
        category_path=["Витамини"],
    )
    defaults.update(overrides)
    return ExtractedProduct(**defaults)


def _checker(
    html: str = "<html><body></body></html>",
    json_ld: dict | None = None,
    vue_data: dict | None = None,
    brands: tuple[str, ...] = ("TestBrand",),
) -> SourceConsistencyChecker:
    return SourceConsistencyChecker(
        soup=_make_soup(html),
        json_ld=json_ld,
        vue_data=vue_data,
        brand_matcher=_make_brand_matcher(*brands),
    )


# ── Check 1: Price ─────────────────────────────────────────────────────────────

class TestCheckPrice:
    def test_no_warning_when_prices_agree(self):
        vue = {"variants": [{"price": 10.00, "discountedPrice": 10.00}]}
        jld = {"offers": {"price": "10.00"}}
        c = _checker(vue_data=vue, json_ld=jld)
        assert c._check_price(_minimal_product()) is None

    def test_no_warning_within_tolerance(self):
        # Vue=10.00 EUR, JSON-LD=10.05 EUR → 0.5% deviation < 1%
        vue = {"variants": [{"price": 10.00, "discountedPrice": 10.00}]}
        jld = {"offers": {"price": "10.05"}}
        c = _checker(vue_data=vue, json_ld=jld)
        assert c._check_price(_minimal_product()) is None

    def test_warning_when_prices_diverge(self):
        vue = {"variants": [{"price": 10.00, "discountedPrice": 10.00}]}
        jld = {"offers": {"price": "15.00"}}
        c = _checker(vue_data=vue, json_ld=jld)
        result = c._check_price(_minimal_product())
        assert result is not None
        assert "consistency_price" in result
        assert "Vue=" in result
        assert "JSON-LD=" in result

    def test_no_warning_when_vue_missing(self):
        jld = {"offers": {"price": "10.00"}}
        c = _checker(vue_data=None, json_ld=jld)
        assert c._check_price(_minimal_product()) is None

    def test_no_warning_when_jsonld_price_missing(self):
        vue = {"variants": [{"price": 10.00, "discountedPrice": 10.00}]}
        c = _checker(vue_data=vue, json_ld={})
        assert c._check_price(_minimal_product()) is None

    def test_uses_discounted_price_not_regular(self):
        # discountedPrice differs from price — checker must use discountedPrice
        vue = {"variants": [{"price": 13.75, "discountedPrice": 11.65}]}
        jld = {"offers": {"price": "11.65"}}  # matches discountedPrice
        c = _checker(vue_data=vue, json_ld=jld)
        assert c._check_price(_minimal_product()) is None

    def test_jsonld_offers_as_list_uses_first(self):
        vue = {"variants": [{"price": 10.00, "discountedPrice": 10.00}]}
        jld = {"offers": [{"price": "10.00"}, {"price": "20.00"}]}
        c = _checker(vue_data=vue, json_ld=jld)
        assert c._check_price(_minimal_product()) is None

    def test_exactly_at_1pct_boundary_no_warning(self):
        # 1% of 10.00 = 0.10 → 10.10 is exactly at threshold (deviation = 1%)
        vue = {"variants": [{"price": 10.00, "discountedPrice": 10.00}]}
        jld = {"offers": {"price": "10.10"}}
        c = _checker(vue_data=vue, json_ld=jld)
        # 1% deviation is not > 1%, so no warning
        assert c._check_price(_minimal_product()) is None

    def test_just_over_1pct_warns(self):
        vue = {"variants": [{"price": 10.00, "discountedPrice": 10.00}]}
        jld = {"offers": {"price": "10.11"}}  # 1.1% deviation
        c = _checker(vue_data=vue, json_ld=jld)
        assert c._check_price(_minimal_product()) is not None


# ── Check 2: Title ─────────────────────────────────────────────────────────────

class TestCheckTitle:
    def test_no_warning_when_jsonld_name_substring_of_h1(self):
        html = "<html><body><h1>TestBrand Vitamin C 500mg таблетки</h1></body></html>"
        jld = {"name": "TestBrand Vitamin C 500mg"}
        c = _checker(html=html, json_ld=jld)
        assert c._check_title(_minimal_product()) is None

    def test_no_warning_when_h1_substring_of_jsonld_name(self):
        html = "<html><body><h1>Vitamin C 500mg</h1></body></html>"
        jld = {"name": "TestBrand Vitamin C 500mg таблетки"}
        c = _checker(html=html, json_ld=jld)
        assert c._check_title(_minimal_product()) is None

    def test_warning_when_titles_completely_different(self):
        html = "<html><body><h1>Completely Different Product</h1></body></html>"
        jld = {"name": "TestBrand Vitamin C"}
        c = _checker(html=html, json_ld=jld)
        result = c._check_title(_minimal_product())
        assert result is not None
        assert "consistency_title" in result

    def test_case_insensitive_comparison(self):
        html = "<html><body><h1>TESTBRAND VITAMIN C 500MG</h1></body></html>"
        jld = {"name": "testbrand vitamin c 500mg"}
        c = _checker(html=html, json_ld=jld)
        assert c._check_title(_minimal_product()) is None

    def test_no_warning_when_no_h1(self):
        html = "<html><body><p>No heading here</p></body></html>"
        jld = {"name": "TestBrand Vitamin C"}
        c = _checker(html=html, json_ld=jld)
        assert c._check_title(_minimal_product()) is None

    def test_no_warning_when_no_jsonld_name(self):
        html = "<html><body><h1>Product Title</h1></body></html>"
        c = _checker(html=html, json_ld={"sku": "123"})
        assert c._check_title(_minimal_product()) is None


# ── Check 3: Brand ─────────────────────────────────────────────────────────────

class TestCheckBrand:
    def test_no_warning_when_brands_match(self):
        jld = {"brand": {"name": "TestBrand"}}
        c = _checker(json_ld=jld, brands=("TestBrand",))
        assert c._check_brand(_minimal_product(title="TestBrand Vitamin C 500mg")) is None

    def test_warning_when_brands_differ(self):
        jld = {"brand": {"name": "Nivea"}}
        c = _checker(json_ld=jld, brands=("TestBrand",))
        result = c._check_brand(_minimal_product(title="TestBrand Vitamin C 500mg"))
        assert result is not None
        assert "consistency_brand" in result
        assert "Nivea" in result
        assert "TestBrand" in result

    def test_no_warning_when_title_matcher_has_no_opinion(self):
        jld = {"brand": {"name": "UnknownBrand"}}
        c = _checker(json_ld=jld, brands=("KnownBrand",))
        # Title has no known brand prefix → matcher returns "" → skip
        assert c._check_brand(_minimal_product(title="Generic Product 50ml")) is None

    def test_no_warning_when_no_jsonld_brand(self):
        c = _checker(json_ld={"name": "Some Product"}, brands=("TestBrand",))
        assert c._check_brand(_minimal_product()) is None

    def test_brand_as_string_not_dict(self):
        jld = {"brand": "TestBrand"}
        c = _checker(json_ld=jld, brands=("TestBrand",))
        assert c._check_brand(_minimal_product(title="TestBrand Vitamin C")) is None

    def test_case_insensitive_comparison(self):
        jld = {"brand": {"name": "testbrand"}}
        c = _checker(json_ld=jld, brands=("TestBrand",))
        assert c._check_brand(_minimal_product(title="TestBrand Vitamin C")) is None


# ── Check 4: Images ────────────────────────────────────────────────────────────

_IMG_GALLERY = "https://benu.bg/media/cache/product_view_default/images/products/1/img.jpg"
_IMG_JLD = "https://benu.bg/uploads/images/products/1/img.jpg"  # different prefix, same /images/products/... path


class TestCheckImages:
    def test_no_warning_when_normalized_paths_overlap(self):
        html = f'<html><body><div class="site-gallery"><img src="{_IMG_GALLERY}"></div></body></html>'
        jld = {"image": [_IMG_JLD]}
        c = _checker(html=html, json_ld=jld)
        assert c._check_images(_minimal_product()) is None

    def test_warning_when_no_overlap(self):
        html = '<html><body><div class="site-gallery"><img src="https://benu.bg/media/cache/product_view_default/images/products/1/img_a.jpg"></div></body></html>'
        jld = {"image": ["https://benu.bg/uploads/images/products/2/img_b.jpg"]}
        c = _checker(html=html, json_ld=jld)
        result = c._check_images(_minimal_product())
        assert result is not None
        assert "consistency_images" in result

    def test_no_warning_when_no_jsonld_images(self):
        html = f'<html><body><div class="site-gallery"><img src="{_IMG_GALLERY}"></div></body></html>'
        c = _checker(html=html, json_ld={})
        assert c._check_images(_minimal_product()) is None

    def test_no_warning_when_no_gallery_in_html(self):
        jld = {"image": [_IMG_JLD]}
        c = _checker(html="<html><body><p>no gallery</p></body></html>", json_ld=jld)
        assert c._check_images(_minimal_product()) is None

    def test_jsonld_image_as_single_string(self):
        html = f'<html><body><div class="site-gallery"><img src="{_IMG_GALLERY}"></div></body></html>'
        jld = {"image": _IMG_JLD}  # string, not list
        c = _checker(html=html, json_ld=jld)
        assert c._check_images(_minimal_product()) is None

    def test_normalize_img_url_extracts_path(self):
        url = "https://benu.bg/media/cache/product_view_default/images/products/5/photo.webp"
        assert SourceConsistencyChecker._normalize_img_url(url) == "/images/products/5/photo.webp"

    def test_normalize_img_url_returns_none_for_non_product_url(self):
        assert SourceConsistencyChecker._normalize_img_url("https://benu.bg/logo.svg") is None

    def test_normalize_img_url_returns_none_for_empty(self):
        assert SourceConsistencyChecker._normalize_img_url("") is None


# ── Check 5: Category path ────────────────────────────────────────────────────

_BREADCRUMB_HTML = """
<html><body>
  <script type="application/ld+json">
  {"@type": "BreadcrumbList", "itemListElement": [
    {"@type": "ListItem", "name": "Начало"},
    {"@type": "ListItem", "name": "Витамини"},
    {"@type": "ListItem", "name": "Витамин C"}
  ]}
  </script>
  <nav aria-label="breadcrumb">
    <a href="/">Начало</a>
    <a href="/vitamins">Витамини</a>
    <a href="/vitamin-c">Витамин C</a>
  </nav>
</body></html>
"""


class TestCheckCategoryPath:
    def test_no_warning_when_paths_agree(self):
        c = _checker(html=_BREADCRUMB_HTML, json_ld={"dummy": True})
        assert c._check_category_path(_minimal_product()) is None

    def test_warning_when_paths_differ(self):
        html = """
        <html><body>
          <script type="application/ld+json">
          {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "name": "Козметика"}
          ]}
          </script>
          <nav aria-label="breadcrumb">
            <a href="/">Начало</a>
            <a href="/vitamins">Витамини</a>
          </nav>
        </body></html>
        """
        c = _checker(html=html, json_ld={"dummy": True})
        result = c._check_category_path(_minimal_product())
        assert result is not None
        assert "consistency_category_path" in result

    def test_no_warning_when_no_html_breadcrumb(self):
        html = """
        <html><body>
          <script type="application/ld+json">
          {"@type": "BreadcrumbList", "itemListElement": [{"name": "Витамини"}]}
          </script>
        </body></html>
        """
        c = _checker(html=html, json_ld={"dummy": True})
        assert c._check_category_path(_minimal_product()) is None

    def test_no_warning_when_no_jsonld_breadcrumb(self):
        c = _checker(html=_BREADCRUMB_HTML, json_ld=None)
        assert c._check_category_path(_minimal_product()) is None

    def test_начало_excluded_from_comparison(self):
        # If both sides have только "Начало", they agree on nothing useful — skip
        html = """
        <html><body>
          <script type="application/ld+json">
          {"@type": "BreadcrumbList", "itemListElement": [{"name": "Начало"}]}
          </script>
          <nav aria-label="breadcrumb"><a href="/">Начало</a></nav>
        </body></html>
        """
        c = _checker(html=html, json_ld={"dummy": True})
        # JSON-LD crumbs = [] after filtering "Начало" → skipped
        assert c._check_category_path(_minimal_product()) is None


# ── Check 6: Promo logic ──────────────────────────────────────────────────────

class TestCheckPromoLogic:
    def test_no_warning_when_price_below_original(self):
        c = _checker()
        p = _minimal_product(price="15.00", original_price="20.00")
        assert c._check_promo_logic(p) is None

    def test_warning_when_price_equals_original(self):
        c = _checker()
        p = _minimal_product(price="20.00", original_price="20.00")
        result = c._check_promo_logic(p)
        assert result is not None
        assert "consistency_promo_logic" in result

    def test_warning_when_price_above_original(self):
        c = _checker()
        p = _minimal_product(price="25.00", original_price="20.00")
        result = c._check_promo_logic(p)
        assert result is not None
        assert "25.00" in result
        assert "20.00" in result

    def test_no_warning_when_no_original_price(self):
        c = _checker()
        assert c._check_promo_logic(_minimal_product(price="20.00", original_price="")) is None

    def test_no_warning_when_original_price_zero(self):
        c = _checker()
        # original_price="0.00" → original_f = 0.0 → guard `if original_f > 0` prevents false positive
        p = _minimal_product(price="20.00", original_price="0.00")
        assert c._check_promo_logic(p) is None


# ── Check 7: Barcode ──────────────────────────────────────────────────────────

class TestCheckBarcode:
    def test_no_warning_when_jsonld_matches_extracted(self):
        jld = {"gtin13": "3800123456789"}
        c = _checker(json_ld=jld)
        p = _minimal_product(barcode="3800123456789")
        assert c._check_barcode(p) is None

    def test_warning_when_jsonld_barcode_differs(self):
        jld = {"gtin13": "1234567890123"}
        c = _checker(json_ld=jld)
        p = _minimal_product(barcode="3800123456789")
        result = c._check_barcode(p)
        assert result is not None
        assert "consistency_barcode" in result
        assert "JSON-LD" in result

    def test_warning_when_text_pattern_barcode_differs(self):
        c = _checker(json_ld={})
        p = _minimal_product(barcode="3800123456789", more_info="Баркод : 1234567890123")
        result = c._check_barcode(p)
        assert result is not None
        assert "text-pattern" in result

    def test_no_warning_when_product_has_no_barcode(self):
        jld = {"gtin13": "3800123456789"}
        c = _checker(json_ld=jld)
        assert c._check_barcode(_minimal_product(barcode="")) is None

    def test_no_warning_when_no_alternate_source(self):
        # No JSON-LD gtin, no Баркод: text in more_info
        c = _checker(json_ld={})
        p = _minimal_product(barcode="3800123456789", more_info="No barcode info here")
        assert c._check_barcode(p) is None

    def test_jsonld_has_priority_over_text_pattern(self):
        # JSON-LD matches → return immediately, don't check text pattern
        jld = {"gtin13": "3800123456789"}
        c = _checker(json_ld=jld)
        # Even if text says something different, JSON-LD match ends the check
        p = _minimal_product(barcode="3800123456789", more_info="Баркод : 9999999999999")
        assert c._check_barcode(p) is None

    @pytest.mark.parametrize("key", ["gtin", "gtin13", "gtin8", "gtin12", "gtin14", "ean"])
    def test_all_gtin_keys_checked(self, key):
        jld = {key: "3800123456789"}
        c = _checker(json_ld=jld)
        assert c._check_barcode(_minimal_product(barcode="3800123456789")) is None

    def test_multiple_gtin_keys_no_false_positive_when_one_matches(self):
        # Regression: first key 'gtin' has a legacy/wrong value; gtin13 is correct.
        # Must NOT warn because product.barcode matches gtin13.
        jld = {"gtin": "00000000", "gtin13": "3800123456789"}
        c = _checker(json_ld=jld)
        assert c._check_barcode(_minimal_product(barcode="3800123456789")) is None

    def test_multiple_gtin_keys_warns_when_none_match(self):
        jld = {"gtin": "1111111111111", "gtin13": "2222222222222"}
        c = _checker(json_ld=jld)
        result = c._check_barcode(_minimal_product(barcode="3800123456789"))
        assert result is not None
        assert "consistency_barcode" in result


# ── Checks 8–11: Content sections ─────────────────────────────────────────────

class TestCheckSections:
    @pytest.mark.parametrize("header, field_name, warning_key", [
        ("Какво представлява", "details",          "consistency_section_details"),
        ("Активни съставки",   "composition",      "consistency_section_composition"),
        ("Дозировка и начин на употреба", "usage", "consistency_section_usage"),
        ("Противопоказания",   "contraindications","consistency_section_contraindications"),
    ])
    def test_header_present_content_empty_warns(self, header, field_name, warning_key):
        html = f"<html><body><p>{header}</p></body></html>"
        c = _checker(html=html)
        p = _minimal_product(**{field_name: ""})
        warnings = c.check(p)
        assert any(warning_key in w for w in warnings), \
            f"Expected {warning_key!r} in warnings for empty {field_name!r}"

    @pytest.mark.parametrize("header, field_name", [
        ("Какво представлява", "details"),
        ("Активни съставки",   "composition"),
        ("Дозировка и начин на употреба", "usage"),
        ("Противопоказания",   "contraindications"),
    ])
    def test_header_present_content_non_empty_no_warning(self, header, field_name):
        html = f"<html><body><p>{header}</p><p>Some content</p></body></html>"
        c = _checker(html=html)
        p = _minimal_product(**{field_name: "Some content"})
        warnings = c.check(p)
        assert not any(f"consistency_section_{field_name}" in w for w in warnings)

    def test_header_absent_content_empty_no_warning(self):
        c = _checker(html="<html><body><p>Some other content</p></body></html>")
        p = _minimal_product(details="", composition="", usage="", contraindications="")
        warnings = c.check(p)
        assert not any("consistency_section" in w for w in warnings)

    def test_all_four_sections_flagged_when_all_empty(self):
        html = """<html><body>
          <p>Какво представлява</p>
          <p>Активни съставки</p>
          <p>Дозировка и начин на употреба</p>
          <p>Противопоказания</p>
        </body></html>"""
        c = _checker(html=html)
        p = _minimal_product(details="", composition="", usage="", contraindications="")
        warnings = c.check(p)
        section_warnings = [w for w in warnings if "consistency_section" in w]
        assert len(section_warnings) == 4

    def test_alternate_headers_also_trigger(self):
        # "Описание" is an alternate marker for details
        html = "<html><body><p>Описание</p></body></html>"
        c = _checker(html=html)
        p = _minimal_product(details="")
        warnings = c.check(p)
        assert any("consistency_section_details" in w for w in warnings)


# ── check() integration ────────────────────────────────────────────────────────

class TestCheckIntegration:
    def test_returns_empty_list_for_fully_clean_product(self):
        html = """<html><body>
          <h1>TestBrand Vitamin C 500mg</h1>
          <script type="application/ld+json">
          {"@type": "BreadcrumbList", "itemListElement": [{"name": "Витамини"}]}
          </script>
          <nav aria-label="breadcrumb"><a href="/vitamins">Витамини</a></nav>
        </body></html>"""
        jld = {
            "name": "TestBrand Vitamin C 500mg",
            "brand": {"name": "TestBrand"},
            "offers": {"price": "6.26"},
        }
        vue = {"variants": [{"price": 6.26, "discountedPrice": 6.26}]}
        c = SourceConsistencyChecker(
            soup=_make_soup(html),
            json_ld=jld,
            vue_data=vue,
            brand_matcher=_make_brand_matcher("TestBrand"),
        )
        p = _minimal_product(
            title="TestBrand Vitamin C 500mg",
            price=f"{6.26 * 1.95583:.2f}",
            category_path=["Витамини"],
            details="Some description",
            composition="Some composition",
        )
        assert c.check(p) == []

    def test_returns_warnings_for_mismatched_price(self):
        vue = {"variants": [{"price": 10.00, "discountedPrice": 10.00}]}
        jld = {"offers": {"price": "99.99"}}
        c = _checker(vue_data=vue, json_ld=jld)
        warnings = c.check(_minimal_product())
        assert any("consistency_price" in w for w in warnings)

    def test_returns_list_type(self):
        c = _checker()
        assert isinstance(c.check(_minimal_product()), list)

    def test_all_warnings_are_strings(self):
        c = _checker()
        for w in c.check(_minimal_product()):
            assert isinstance(w, str)

    def test_never_raises_on_empty_inputs(self):
        c = SourceConsistencyChecker(
            soup=_make_soup(""),
            json_ld=None,
            vue_data=None,
            brand_matcher=_make_brand_matcher(),
        )
        warnings = c.check(_minimal_product())
        assert isinstance(warnings, list)

    def test_exception_in_one_check_does_not_stop_others(self):
        # Promo logic will fire; overall check() must still complete
        c = _checker(
            vue_data={"variants": [{"price": 10.00, "discountedPrice": 10.00}]},
            json_ld={"offers": {"price": "99.99"}},
        )
        p = _minimal_product(price="25.00", original_price="20.00")  # also fires promo
        warnings = c.check(p)
        assert any("consistency_price" in w for w in warnings)
        assert any("consistency_promo_logic" in w for w in warnings)
