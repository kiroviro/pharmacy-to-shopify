"""
Source Consistency Checker

Cross-checks an ExtractedProduct against the raw HTML sources it came from.
Zero additional HTTP requests — all sources are pre-parsed by PharmacyExtractor.

For each field, two independent data sources from the same HTML are compared:
  - Price:    Vue.js discountedPrice  vs  JSON-LD offers.price
  - Title:    JSON-LD name            vs  <h1> text
  - Brand:    JSON-LD brand.name      vs  BrandMatcher.match_from_title()
  - Images:   gallery CSS selectors   vs  JSON-LD image[]
  - Category: JSON-LD BreadcrumbList  vs  HTML .breadcrumb selectors
  - Promo:    product.price           vs  product.original_price (logic check)
  - Barcode:  JSON-LD gtin fields     vs  "Баркод:" text pattern
  - Sections: tab header in HTML      →   extracted content non-empty
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from ..common.constants import EUR_TO_BGN
from ..models import ExtractedProduct

if TYPE_CHECKING:
    from .brand_matcher import BrandMatcher

logger = logging.getLogger(__name__)

_PRICE_TOLERANCE = 0.01  # 1 % — matches SpecificationValidator.price_eur threshold
_IMG_PATH_RE = re.compile(r"/images/products/.*")
_BARCODE_RE = re.compile(r"(?:Баркод|EAN|GTIN)\s*:\s*(\d{8,14})", re.IGNORECASE)

# Tab section headers: (warning_key, page-text markers, ExtractedProduct field name)
_TAB_SECTIONS = [
    ("consistency_section_details",          ["какво представлява", "описание"],            "details"),
    ("consistency_section_composition",      ["активни съставки", "състав"],                "composition"),
    ("consistency_section_usage",            ["дозировка и начин на употреба", "начин на употреба"], "usage"),
    ("consistency_section_contraindications",["противопоказания"],                          "contraindications"),
]


class SourceConsistencyChecker:
    """
    Cross-checks an ExtractedProduct against the raw HTML sources it came from.

    Checks are best-effort: if a source is missing or malformed the check is
    silently skipped. A warning is only emitted when both sides have data and
    they disagree.

    Usage::

        checker = SourceConsistencyChecker(
            soup=extractor.soup,
            json_ld=extractor.json_ld,
            vue_data=extractor._parse_vue_product_data(),
            brand_matcher=extractor.brand_matcher,
        )
        warnings = checker.check(product)
    """

    def __init__(
        self,
        soup: BeautifulSoup,
        json_ld: dict | None,
        vue_data: dict | None,
        brand_matcher: "BrandMatcher",
    ) -> None:
        self._soup = soup
        self._json_ld = json_ld or {}
        self._vue_data = vue_data
        self._brand_matcher = brand_matcher

    def check(self, product: ExtractedProduct) -> list[str]:
        """Run all consistency checks. Returns warning strings, empty list if clean."""
        warnings: list[str] = []

        # Cache page text once — shared by all tab-section checks
        page_text = self._soup.get_text(separator="\n").lower()

        for check_fn in (
            self._check_price,
            self._check_title,
            self._check_brand,
            self._check_images,
            self._check_category_path,
            self._check_promo_logic,
            self._check_barcode,
        ):
            try:
                result = check_fn(product)
                if result:
                    warnings.append(result)
            except Exception as exc:
                logger.debug("consistency check %s skipped: %s", check_fn.__name__, exc)

        for warning_key, markers, field_name in _TAB_SECTIONS:
            try:
                result = self._check_section(warning_key, markers, getattr(product, field_name, ""), page_text)
                if result:
                    warnings.append(result)
            except Exception as exc:
                logger.debug("consistency check %s skipped: %s", warning_key, exc)

        return warnings

    # ── Check 1: Price ────────────────────────────────────────────────────────

    def _check_price(self, product: ExtractedProduct) -> str | None:
        """Vue discountedPrice × EUR_TO_BGN vs JSON-LD offers.price × EUR_TO_BGN — within 1%?"""
        if not self._vue_data:
            return None
        variants = self._vue_data.get("variants", [])
        if not variants:
            return None
        vue_eur = float(variants[0].get("discountedPrice") or 0)
        if not vue_eur:
            return None
        vue_bgn = vue_eur * EUR_TO_BGN

        offers = self._json_ld.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        jld_raw = offers.get("price")
        if jld_raw is None:
            return None
        jld_eur = float(str(jld_raw).replace(",", "."))
        if not jld_eur:
            return None
        jld_bgn = jld_eur * EUR_TO_BGN

        deviation = abs(vue_bgn - jld_bgn) / vue_bgn
        if deviation > _PRICE_TOLERANCE:
            return (
                f"consistency_price: Vue={vue_bgn:.2f} BGN vs "
                f"JSON-LD={jld_bgn:.2f} BGN ({deviation:.1%} deviation)"
            )
        return None

    # ── Check 2: Title ────────────────────────────────────────────────────────

    def _check_title(self, product: ExtractedProduct) -> str | None:
        """JSON-LD name vs <h1> — is one a substring of the other?"""
        jld_name = self._json_ld.get("name", "").strip()
        if not jld_name:
            return None
        h1 = self._soup.find("h1")
        if not h1:
            return None
        h1_text = h1.get_text(strip=True)
        if not h1_text:
            return None
        jld_lower, h1_lower = jld_name.lower(), h1_text.lower()
        if jld_lower not in h1_lower and h1_lower not in jld_lower:
            return f"consistency_title: JSON-LD={jld_name!r} not substring-match of H1={h1_text!r}"
        return None

    # ── Check 3: Brand ────────────────────────────────────────────────────────

    def _check_brand(self, product: ExtractedProduct) -> str | None:
        """JSON-LD brand.name vs BrandMatcher.match_from_title(product.title) — same?"""
        brand_data = self._json_ld.get("brand")
        if not brand_data:
            return None
        jld_brand = (
            brand_data.get("name", "") if isinstance(brand_data, dict) else str(brand_data)
        ).strip()
        if not jld_brand:
            return None
        title_brand = self._brand_matcher.match_from_title(product.title)
        if not title_brand:
            return None  # matcher has no opinion — skip
        if jld_brand.lower() != title_brand.lower():
            return f"consistency_brand: JSON-LD={jld_brand!r} vs title-match={title_brand!r}"
        return None

    # ── Check 4: Images ───────────────────────────────────────────────────────

    def _check_images(self, product: ExtractedProduct) -> str | None:
        """Gallery CSS img URLs vs JSON-LD image[] — at least 1 normalized path in common?"""
        jld_images = self._json_ld.get("image")
        if not jld_images:
            return None
        if isinstance(jld_images, str):
            jld_images = [jld_images]

        jld_paths = {
            self._normalize_img_url(u) for u in jld_images
            if self._normalize_img_url(u)
        }
        if not jld_paths:
            return None

        gallery_imgs = self._soup.select(
            ".site-gallery img, .product-gallery img, .gallery img, .product-image img"
        )
        gallery_paths = set()
        for img in gallery_imgs:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy", "")
            norm = self._normalize_img_url(src)
            if norm:
                gallery_paths.add(norm)

        if not gallery_paths:
            return None  # no gallery on page — skip

        if jld_paths.isdisjoint(gallery_paths):
            return (
                f"consistency_images: no overlap between gallery ({len(gallery_paths)} URLs) "
                f"and JSON-LD image[] ({len(jld_paths)} URLs)"
            )
        return None

    # ── Check 5: Category path ────────────────────────────────────────────────

    def _check_category_path(self, product: ExtractedProduct) -> str | None:
        """JSON-LD BreadcrumbList vs HTML .breadcrumb a — same category set?"""
        jld_crumbs = self._parse_jsonld_breadcrumbs()
        if not jld_crumbs:
            return None

        html_crumbs = [
            a.get_text(strip=True)
            for a in self._soup.select(
                ".breadcrumb a, .breadcrumbs a, nav[aria-label='breadcrumb'] a"
            )
            if a.get_text(strip=True).lower() not in ("начало", "home")
        ]
        if not html_crumbs:
            return None

        if set(jld_crumbs) != set(html_crumbs):
            return (
                f"consistency_category_path: JSON-LD={jld_crumbs} vs HTML={html_crumbs}"
            )
        return None

    # ── Check 6: Promo logic ──────────────────────────────────────────────────

    def _check_promo_logic(self, product: ExtractedProduct) -> str | None:
        """If original_price is set then price must be strictly less than original_price."""
        if not product.original_price or not product.price:
            return None
        try:
            price_f = float(product.price)
            original_f = float(product.original_price)
        except (ValueError, TypeError):
            return None
        if original_f > 0 and price_f >= original_f:
            return (
                f"consistency_promo_logic: price={price_f:.2f} >= "
                f"original_price={original_f:.2f} (expected price < original_price)"
            )
        return None

    # ── Check 7: Barcode ──────────────────────────────────────────────────────

    def _check_barcode(self, product: ExtractedProduct) -> str | None:
        """JSON-LD gtin fields vs extracted barcode, and more_info text vs extracted barcode."""
        if not product.barcode:
            return None

        # Collect all valid GTIN values from JSON-LD (a document may have multiple keys)
        jld_barcodes: dict[str, str] = {}
        for key in ("gtin", "gtin13", "gtin8", "gtin12", "gtin14", "ean"):
            val = self._json_ld.get(key)
            if val and re.match(r"^\d{8,14}$", str(val).strip()):
                jld_barcodes[key] = str(val).strip()

        if jld_barcodes:
            if product.barcode in jld_barcodes.values():
                return None  # at least one key matches — no issue
            first_key, first_val = next(iter(jld_barcodes.items()))
            return (
                f"consistency_barcode: extracted={product.barcode!r} vs "
                f"JSON-LD[{first_key}]={first_val!r}"
            )

        # No JSON-LD gtin; compare against text pattern in more_info
        if product.more_info:
            m = _BARCODE_RE.search(product.more_info)
            if m and m.group(1) != product.barcode:
                return (
                    f"consistency_barcode: extracted={product.barcode!r} vs "
                    f"text-pattern={m.group(1)!r}"
                )
        return None

    # ── Checks 8–11: Content sections ─────────────────────────────────────────

    @staticmethod
    def _check_section(
        warning_key: str,
        header_markers: list[str],
        product_value: str,
        page_text: str,
    ) -> str | None:
        """If any header marker is in page text and product_value is empty → warning."""
        if any(marker in page_text for marker in header_markers):
            if not product_value:
                markers_display = "/".join(header_markers)
                return f"{warning_key}: header '{markers_display}' present but content is empty"
        return None

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_img_url(url: str) -> str | None:
        """Extract /images/products/... path segment for URL dedup comparison."""
        if not url:
            return None
        m = _IMG_PATH_RE.search(url)
        return m.group(0) if m else None

    def _parse_jsonld_breadcrumbs(self) -> list[str]:
        """Re-parse BreadcrumbList from all JSON-LD script tags."""
        for script in self._soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                breadcrumb_data = None
                if isinstance(data, dict) and data.get("@type") == "BreadcrumbList":
                    breadcrumb_data = data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "BreadcrumbList":
                            breadcrumb_data = item
                            break
                if breadcrumb_data:
                    crumbs = []
                    for item in breadcrumb_data.get("itemListElement", []):
                        name = item.get("name") or item.get("item", {}).get("name", "")
                        if name and name.lower() not in ("начало", "home"):
                            crumbs.append(name)
                    return crumbs
            except Exception:
                continue
        return []
