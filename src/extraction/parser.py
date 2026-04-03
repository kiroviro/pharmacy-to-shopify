"""
PharmacyParser — extracts product fields from pre-parsed HTML.

Accepts a BeautifulSoup tree and JSON-LD dict (produced by PharmacyFetcher)
and performs all product data extraction without any HTTP or I/O.

This separation makes PharmacyParser independently testable: construct it
with pre-parsed soup/json_ld objects and call extract() — no network needed.
"""

from __future__ import annotations

import html as html_module
import json
import logging
import re
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

from ..common.config_loader import load_seo_settings
from ..common.constants import EUR_TO_BGN
from ..common.transliteration import generate_handle as transliterate_handle
from ..models import ExtractedProduct, ProductImage
from .brand_matcher import BrandMatcher
from .classifier import (
    determine_google_age_group,
    determine_google_category,
    extract_application_form,
    extract_target_audience,
)

logger = logging.getLogger(__name__)

_VUE_DATA_NOT_PARSED = object()  # sentinel for _cached_vue_data


def parse_breadcrumb_jsonld(soup: BeautifulSoup, exclude_title: str | None = None) -> list[str]:
    """
    Parse BreadcrumbList from JSON-LD script tags.

    Args:
        soup: Parsed HTML tree
        exclude_title: Product title to exclude from breadcrumb (avoids
            including the product itself as a category)

    Returns:
        List of breadcrumb category names (excluding "Начало"/"home")
    """
    for script in soup.find_all("script", type="application/ld+json"):
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
                        if exclude_title and name == exclude_title:
                            continue
                        if exclude_title and (len(name) >= 50 and exclude_title in name):
                            continue
                        crumbs.append(name)
                return crumbs
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    return []


class PharmacyParser:
    """Extracts product data from a pre-parsed pharmacy page."""

    _shared_brand_matcher: BrandMatcher | None = None
    _shared_seo_settings: dict | None = None

    def __init__(
        self,
        soup: BeautifulSoup,
        json_ld: dict | None,
        url: str,
        brand_matcher: BrandMatcher | None = None,
        seo_settings: dict | None = None,
        validate_images: bool = False,
    ) -> None:
        self.soup = soup
        self.json_ld = json_ld
        self.url = url
        self.site_domain = "benu.bg"
        self.validate_images = validate_images

        self._cached_title: str | None = None
        self._cached_vue_data: object = _VUE_DATA_NOT_PARSED
        self.product_type = "otc"

        if brand_matcher is not None:
            self.brand_matcher = brand_matcher
        else:
            if PharmacyParser._shared_brand_matcher is None:
                PharmacyParser._shared_brand_matcher = BrandMatcher()
            self.brand_matcher = PharmacyParser._shared_brand_matcher

        if seo_settings is not None:
            self._seo_settings = seo_settings
        else:
            if PharmacyParser._shared_seo_settings is None:
                PharmacyParser._shared_seo_settings = load_seo_settings()
            self._seo_settings = PharmacyParser._shared_seo_settings

    def extract(self) -> ExtractedProduct:
        """Extract all product data and return an ExtractedProduct."""
        title = self._extract_title()
        brand = self._extract_brand(title)
        categories = self._extract_categories(title)
        price_bgn, price_eur = self._extract_prices()
        sku = self._extract_sku()

        page_text = self.soup.get_text(separator="\n")
        details = self._extract_tab_content("Какво представлява", page_text)
        composition = self._extract_tab_content("Активни съставки", page_text)
        usage = self._extract_tab_content("Дозировка и начин на употреба", page_text)
        contraindications = self._extract_tab_content("Противопоказания", page_text)
        more_info = self._extract_tab_content("Допълнителна информация", page_text)

        sections = {
            "details": details,
            "composition": composition,
            "usage": usage,
            "contraindications": contraindications,
            "more_info": more_info,
        }

        tags = list(categories)

        images = self._extract_images()
        self._optimize_image_alt_texts(images, brand, title)

        barcode = self._extract_barcode(page_text)
        highlights = self._extract_highlights()

        return ExtractedProduct(
            title=title,
            url=self.url,
            handle=self._generate_handle(title),
            brand=brand,
            sku=sku,
            price=price_bgn,
            barcode=barcode,
            price_eur=price_eur,
            original_price="",
            availability=self._extract_availability(),
            category_path=categories,
            highlights=highlights,
            details=details,
            composition=composition,
            usage=usage,
            contraindications=contraindications,
            more_info=more_info,
            description=self._build_description(brand, highlights, sections),
            images=images,
            tags=tags,
            product_type=categories[0] if categories else "",
            application_form=extract_application_form(title),
            target_audience=extract_target_audience(categories, title),
            weight_grams=self._extract_weight(),
            seo_title=self._generate_seo_title(title, brand, categories),
            seo_description=self._generate_seo_description(title, brand, categories, sections),
            google_product_category=determine_google_category(categories, self._seo_settings),
            google_mpn=sku,
            google_age_group=determine_google_age_group(categories),
        )

    def _extract_barcode(self, page_text: str = "") -> str:
        """
        Extract barcode/GTIN from multiple sources with fallback chain.

        Checks (in order):
        1. JSON-LD structured data (gtin, gtin13, gtin8, ean)
        2. Meta tags (og:gtin, product:gtin)
        3. "Допълнителна информация" section (Баркод: pattern)

        Returns:
            Barcode string (cleaned, digits only)
        """
        barcode = ""

        if self.json_ld:
            for key in ['gtin', 'gtin13', 'gtin8', 'gtin12', 'gtin14', 'ean']:
                value = self.json_ld.get(key)
                if value and str(value).strip():
                    candidate = str(value).strip()
                    if re.match(r'^\d{8,14}$', candidate):
                        barcode = candidate
                        logger.debug(f"Barcode from JSON-LD[{key}]: {barcode}")
                        break

        if not barcode and self.soup:
            meta_tags = self.soup.find_all('meta', attrs={'property': re.compile(r'gtin|ean|barcode', re.I)})
            for meta in meta_tags:
                content = meta.get('content', '').strip()
                if content:
                    barcode = content
                    logger.debug(f"Barcode from meta tag: {barcode}")
                    break

        if not barcode:
            more_info = self._extract_tab_content(
                "Допълнителна информация",
                page_text or (self.soup.get_text(separator="\n") if self.soup else ""),
            )
            if more_info:
                patterns = [
                    r'Баркод\s*:\s*(\d{8,14})',
                    r'EAN\s*:\s*(\d{8,14})',
                    r'GTIN\s*:\s*(\d{8,14})',
                ]
                for pattern in patterns:
                    match = re.search(pattern, more_info, re.IGNORECASE)
                    if match:
                        barcode = match.group(1)
                        logger.debug(f"Barcode from pattern {pattern}: {barcode}")
                        break

        if barcode:
            cleaned = re.sub(r'[^\d]', '', barcode)
            if len(cleaned) in [8, 12, 13, 14]:
                return cleaned
            else:
                logger.warning(f"Invalid barcode length ({len(cleaned)}): {barcode}")
                return ""

        return ""

    def _extract_title(self) -> str:
        """Extract product title (cached after first call)."""
        if self._cached_title is not None:
            return self._cached_title

        title = ""
        if self.json_ld and self.json_ld.get("name"):
            title = self.json_ld["name"].strip()
        else:
            h1 = self.soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        self._cached_title = title
        return self._cached_title

    def _extract_brand(self, title: str) -> str:
        """Extract brand name."""
        if self.json_ld:
            brand_data = self.json_ld.get("brand")
            if isinstance(brand_data, dict):
                brand = brand_data.get("name", "")
            else:
                brand = brand_data or ""
            if brand:
                return brand.strip()

        return self.brand_matcher.match_from_title(title)

    def _extract_sku(self) -> str:
        """Extract SKU/product code."""
        if self.json_ld and self.json_ld.get("sku"):
            return str(self.json_ld["sku"])
        return ""

    def _parse_vue_product_data(self) -> dict | None:
        """
        Parse Vue.js component product data from <add-to-cart> element.

        Result is cached per HTML load to avoid re-parsing when called from
        multiple methods.
        """
        if self._cached_vue_data is not _VUE_DATA_NOT_PARSED:
            return self._cached_vue_data

        add_to_cart = self.soup.select_one('add-to-cart')
        if not add_to_cart or not add_to_cart.get(':product'):
            self._cached_vue_data = None
            return None

        product_json = html_module.unescape(add_to_cart.get(':product', '{}'))

        try:
            self._cached_vue_data = json.loads(product_json)
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to parse Vue product data: {e}")
            self._cached_vue_data = None

        return self._cached_vue_data

    @property
    def vue_data(self) -> dict | None:
        """Public access to parsed Vue.js product data (cached)."""
        return self._parse_vue_product_data()

    def _extract_prices(self) -> tuple[str, str]:
        """Extract current selling price in BGN and EUR.

        Strategy (in order of reliability):
        1. Vue.js component data (most reliable, always current)
        2. JSON-LD structured data (fallback, may be stale)
        3. HTML price element selectors (last resort)
        """
        price_bgn = ""
        price_eur = ""

        product_data = self._parse_vue_product_data()
        if product_data:
            variants = product_data.get('variants', [])
            if variants:
                try:
                    variant = variants[0]
                    regular_price_eur = float(variant.get('price', 0))
                    discounted_price_eur = float(variant.get('discountedPrice', 0))
                    use_price_eur = regular_price_eur if regular_price_eur > 0 else discounted_price_eur

                    if use_price_eur > 0:
                        price_eur = f"{use_price_eur:.2f}"
                        price_bgn = f"{use_price_eur * EUR_TO_BGN:.2f}"

                        if regular_price_eur != discounted_price_eur:
                            logger.debug(
                                f"Price from Vue (was on promo, using regular): "
                                f"{price_eur} EUR (discounted was: {discounted_price_eur:.2f} EUR)"
                            )
                        else:
                            logger.debug(f"Price from Vue: {price_eur} EUR / {price_bgn} BGN")

                        return price_bgn, price_eur
                except ValueError as e:
                    logger.debug(f"Failed to extract price from Vue variant data: {e}")

        if self.json_ld:
            offers = self.json_ld.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get("price")
            if price:
                try:
                    price_eur = f"{float(str(price).replace(',', '.')):.2f}"
                    price_bgn = f"{float(price_eur) * EUR_TO_BGN:.2f}"
                    logger.warning(
                        f"Price from JSON-LD (fallback): {price_eur} EUR / {price_bgn} BGN "
                        f"- may be stale, Vue data preferred"
                    )
                    return price_bgn, price_eur
                except (ValueError, TypeError):
                    pass

        price_selectors = [
            ".product-prices .price:not(.old-price)",
            ".product-info .price:not(.old-price)",
        ]
        for selector in price_selectors:
            price_elem = self.soup.select_one(selector)
            if price_elem:
                if price_elem.find_parent(class_='owl-carousel'):
                    continue
                text = price_elem.get_text()
                eur_match = re.search(r'(\d+[.,]\d{2})\s*€', text)
                if eur_match:
                    try:
                        price_eur = eur_match.group(1).replace(",", ".")
                        price_bgn = f"{float(price_eur) * EUR_TO_BGN:.2f}"
                        logger.warning(
                            f"Price from HTML selector '{selector}': {price_eur} EUR "
                            f"- Vue/JSON-LD preferred"
                        )
                        return price_bgn, price_eur
                    except (ValueError, TypeError):
                        pass

        logger.warning(f"Could not extract price for {self.url}")
        return price_bgn, price_eur

    @staticmethod
    def _extract_availability() -> str:
        """Extract availability status (not exposed by site)."""
        return ""

    def _extract_categories(self, product_title: str = "") -> list[str]:
        """Extract category breadcrumb."""
        if not product_title:
            product_title = self._extract_title()

        categories = parse_breadcrumb_jsonld(self.soup, exclude_title=product_title)
        if categories:
            return categories

        # HTML fallback
        breadcrumb = self.soup.select(".breadcrumb a, .breadcrumbs a, nav[aria-label='breadcrumb'] a")
        for crumb in breadcrumb:
            text = crumb.get_text(strip=True)
            if text and text.lower() not in ["начало", "home"] and text != product_title:
                categories.append(text)

        return categories

    @staticmethod
    def _extract_highlights() -> list[str]:
        return []

    def _extract_tab_content(self, section_name: str, page_text: str) -> str:
        """Extract content for a specific section by finding text between headings."""
        page_lower = page_text.lower()
        section_lower = section_name.lower()

        section_markers = [
            "какво представлява",
            "активни съставки",
            "противопоказания",
            "дозировка и начин на употреба",
            "допълнителна информация",
            "все още няма ревюта",
        ]

        content_area_start = page_lower.find("какво представлява")
        if content_area_start == -1:
            content_area_start = 0

        start_idx = page_lower.find(section_lower, content_area_start)
        if start_idx == -1:
            return ""

        start_idx += len(section_lower)

        end_idx = len(page_text)
        for marker in section_markers:
            if marker == section_lower:
                continue
            idx = page_lower.find(marker, start_idx)
            if idx != -1 and idx < end_idx:
                end_idx = idx

        content = page_text[start_idx:end_idx].strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        content = "\n".join(lines)

        noise_patterns = ["попитай магистър-фармацевт", "оставете твоето мнение", "бъди първият написал"]
        content_lower = content.lower()
        for noise in noise_patterns:
            idx = content_lower.find(noise)
            if idx != -1:
                content = content[:idx].strip()
                content_lower = content.lower()

        return content[:1500]

    def _extract_images(self) -> list[ProductImage]:
        """Extract product images."""
        images = []
        seen_urls: set[str] = set()

        def is_product_image(url: str) -> bool:
            if not url:
                return False
            url_lower = url.lower()
            exclude_patterns = [
                '.svg', 'icon', 'logo', 'heart', 'cart', 'arrow', 'close',
                'search', 'default.jpg', 'default.png',
                '/media/cache/product_in_category_list',
                '/media/cache/brands_nav_slider',
            ]
            if any(pattern in url_lower for pattern in exclude_patterns):
                return False
            return '/images/products/' in url or url_lower.endswith(('.webp', '.jpg', '.jpeg', '.png', '.gif'))

        def normalize_url(url: str) -> str:
            match = re.search(r'/images/products/.*', url)
            return match.group(0) if match else url

        def encode_url(url: str) -> str:
            parsed = urlparse(url)
            path_parts = parsed.path.rsplit('/', 1)
            if len(path_parts) == 2:
                directory, filename = path_parts
                encoded_filename = quote(filename, safe='%')
                encoded_path = directory + '/' + encoded_filename
                return parsed._replace(path=encoded_path).geturl()
            return url

        if self.json_ld:
            img_data = self.json_ld.get("image")
            if img_data:
                img_urls = [img_data] if isinstance(img_data, str) else (img_data if isinstance(img_data, list) else [])
                for url in img_urls:
                    if not url:
                        continue
                    url_stripped = url.lstrip('/')
                    if url_stripped.startswith('uploads/'):
                        url_stripped = url_stripped.replace('uploads/', 'media/cache/product_view_default/', 1)
                    if not url_stripped.startswith(('http://', 'https://')):
                        url = f"https://{self.site_domain}/{url_stripped}"
                    else:
                        url = url_stripped

                    if is_product_image(url):
                        normalized = normalize_url(url)
                        if normalized not in seen_urls:
                            seen_urls.add(normalized)
                            images.append(ProductImage(
                                source_url=encode_url(url),
                                position=len(images) + 1,
                                alt_text=self._extract_title()
                            ))

        gallery_imgs = self.soup.select(".site-gallery img, .product-gallery img, .gallery img, .product-image img")
        for img in gallery_imgs:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy")
            if src:
                if not src.startswith(('http://', 'https://')):
                    src = f"https://{self.site_domain}/{src.lstrip('/')}"
                if is_product_image(src):
                    normalized = normalize_url(src)
                    if normalized not in seen_urls:
                        seen_urls.add(normalized)
                        images.append(ProductImage(
                            source_url=encode_url(src),
                            position=len(images) + 1,
                            alt_text=img.get("alt", self._extract_title())
                        ))

        if self.validate_images:
            for img in images:
                try:
                    resp = requests.head(img.source_url, timeout=10, allow_redirects=True)
                    if resp.status_code != 200:
                        fallback_url = re.sub(
                            r'/uploads/',
                            '/media/cache/product_view_default/',
                            img.source_url
                        )
                        if fallback_url != img.source_url:
                            try:
                                resp2 = requests.head(fallback_url, timeout=10, allow_redirects=True)
                                if resp2.status_code == 200:
                                    logger.debug("Image fallback: %s -> product_view_default", img.source_url)
                                    img.source_url = fallback_url
                            except requests.RequestException:
                                pass
                except requests.RequestException:
                    pass

        return images

    def _extract_weight(self) -> int:
        """Extract product weight in grams."""
        info_rows = self.soup.select(".product-info tr, .additional-info tr")
        for row in info_rows:
            label = row.select_one("th, td:first-child")
            value = row.select_one("td:last-child")
            if label and value:
                label_text = label.get_text().lower()
                if "тегло" in label_text or "weight" in label_text:
                    weight_text = value.get_text()
                    return self._parse_weight(weight_text)

        title = self._extract_title()
        return self._parse_weight(title)

    def _parse_weight(self, text: str) -> int:
        """Parse weight/volume from text and convert to grams."""
        if not text:
            return 0

        text = text.lower()
        patterns = [
            (r'(\d+(?:[.,]\d+)?)\s*kg', 1000),
            (r'(\d+(?:[.,]\d+)?)\s*(?:g|гр)', 1),
            (r'(\d+(?:[.,]\d+)?)\s*(?:ml|мл)', 1),
            (r'(\d+(?:[.,]\d+)?)\s*(?:l|л)', 1000),
            (r'(\d+(?:[.,]\d+)?)\s*mg', 0.001),
        ]
        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1).replace(",", "."))
                grams = value * multiplier
                return max(1, round(grams)) if grams > 0 else 0

        return 0

    def _build_description(self, brand: str, highlights: list[str], sections: dict) -> str:
        """Build full HTML description from all sections."""
        parts = []

        if brand:
            parts.append(f"<p><strong>Марка:</strong> {brand}</p>")

        if highlights:
            parts.append("<ul>")
            for h in highlights:
                parts.append(f"<li>{h}</li>")
            parts.append("</ul>")

        section_labels = [
            ("Описание", sections.get("details", "")),
            ("Състав", sections.get("composition", "")),
            ("Начин на употреба", sections.get("usage", "")),
            ("Противопоказания", sections.get("contraindications", "")),
            ("Допълнителна информация", sections.get("more_info", "")),
        ]
        for title, content in section_labels:
            if content:
                parts.append(f"<h3>{title}</h3>")
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                for line in lines:
                    parts.append(f"<p>{line}</p>")

        return "\n".join(parts)

    def _generate_handle(self, title: str) -> str:
        """Generate URL-friendly handle from source URL slug."""
        parsed = urlparse(self.url)
        slug = parsed.path.strip('/').split('/')[-1]

        if slug:
            handle = slug.lower()
            handle = re.sub(r'[^a-z0-9-]+', '-', handle)
            handle = re.sub(r'-+', '-', handle)
            handle = handle.strip('-')
            if handle:
                return handle[:200]

        if not title:
            return ""
        return transliterate_handle(title)[:200]

    def _generate_seo_title(self, title: str, brand: str, categories: list[str]) -> str:
        """Generate SEO title with progressive fallback."""
        if not title:
            return ""

        store_name = self._seo_settings.get("store_name", "ViaPharma")
        max_len = self._seo_settings.get("title_max_length", 70)
        suffix = f" | {store_name}"

        display_title = title
        if brand and title.lower().startswith(brand.lower()):
            display_title = title[len(brand):].lstrip(" -–—")

        category = categories[0] if categories else ""

        if brand and category:
            candidate = f"{brand} {display_title} - {category}{suffix}"
            if len(candidate) <= max_len:
                return candidate

        if brand:
            candidate = f"{brand} {display_title}{suffix}"
            if len(candidate) <= max_len:
                return candidate

        candidate = f"{title}{suffix}"
        if len(candidate) <= max_len:
            return candidate

        available = max_len - len(suffix) - 3
        if available > 0:
            return f"{title[:available]}...{suffix}"

        return title[:max_len]

    @staticmethod
    def _format_product_name(title: str, brand: str) -> str:
        """Return display name with brand prepended (unless title already starts with it)."""
        if brand and title.lower().startswith(brand.lower()):
            return title
        if brand:
            return f"{brand} {title}"
        return title

    def _generate_seo_description(self, title: str, brand: str, categories: list[str], sections: dict) -> str:
        """Generate structured SEO meta description in Bulgarian."""
        store_name = self._seo_settings.get("store_name", "ViaPharma")
        max_len = self._seo_settings.get("description_max_length", 155)

        category = categories[0] if categories else ""

        product_name = self._format_product_name(title, brand)

        details = sections.get("details", "")
        first_sentence = ""
        if details:
            sentences = re.split(r'[.!?]', details)
            if sentences and sentences[0].strip():
                first_sentence = sentences[0].strip()

        if category:
            cta = f"Поръчайте в {category} на {store_name}."
        else:
            cta = f"Поръчайте на {store_name}."

        if first_sentence:
            candidate = f"Купете {product_name}. {first_sentence}. {cta}"
            if len(candidate) <= max_len:
                return candidate

        candidate = f"Купете {product_name}. {cta}"
        if len(candidate) <= max_len:
            return candidate

        candidate = f"Купете {product_name}."
        if len(candidate) <= max_len:
            return candidate

        return candidate[:max_len]

    def _optimize_image_alt_texts(self, images: list[ProductImage], brand: str, title: str) -> None:
        """Optimize image alt texts with brand and position context."""
        if not images:
            return

        base_alt = self._format_product_name(title, brand)
        total = len(images)

        for img in images:
            if total == 1:
                img.alt_text = base_alt[:125]
            else:
                position_text = f" - Снимка {img.position} от {total}"
                available = 125 - len(position_text)
                if available > 0:
                    img.alt_text = f"{base_alt[:available]}{position_text}"
                else:
                    img.alt_text = base_alt[:125]

