"""
Pharmacy Product Extractor

Extracts product data from pharmacy website.
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

from ..common.config_loader import load_seo_settings
from ..common.transliteration import generate_handle as transliterate_handle
from ..models import ExtractedProduct, ProductImage
from .brand_matcher import BrandMatcher


class PharmacyExtractor:
    """Extracts product data from a pharmacy site."""

    _shared_brand_matcher = None
    _shared_seo_settings = None

    def __init__(
        self,
        url: str,
        site_domain: str = "pharmacy.example.com",
        validate_images: bool = False,
        session: requests.Session | None = None,
    ):
        self.url = url
        self.site_domain = site_domain
        self.validate_images = validate_images
        self._session = session
        self.html = None
        self.soup = None
        self.json_ld = None
        self._cached_title = None
        self.product_type = "otc"

        if PharmacyExtractor._shared_brand_matcher is None:
            PharmacyExtractor._shared_brand_matcher = BrandMatcher()
        self.brand_matcher = PharmacyExtractor._shared_brand_matcher

        if PharmacyExtractor._shared_seo_settings is None:
            PharmacyExtractor._shared_seo_settings = load_seo_settings()
        self._seo_settings = PharmacyExtractor._shared_seo_settings

    def fetch(self) -> None:
        """Fetch the product page HTML."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
        }
        requester = self._session or requests
        response = requester.get(self.url, headers=headers, timeout=30)
        response.raise_for_status()
        self.html = response.text
        self.soup = BeautifulSoup(self.html, "lxml")
        self._parse_json_ld()

    def load_html(self, html: str) -> None:
        """Load pre-fetched HTML for extraction without a network request."""
        self.html = html
        self.soup = BeautifulSoup(self.html, "lxml")
        self._parse_json_ld()

    def _parse_json_ld(self) -> None:
        """Extract JSON-LD structured data."""
        scripts = self.soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    self.json_ld = data
                    return
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            self.json_ld = item
                            return
            except (json.JSONDecodeError, TypeError):
                continue

    def extract(self) -> ExtractedProduct:
        """Extract all product data."""
        title = self._extract_title()
        brand = self._extract_brand(title)
        categories = self._extract_categories(title)
        price_bgn, price_eur = self._extract_prices()
        sku = self._extract_sku()

        # Extract content sections once, reuse for description + SEO
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

        barcode = self._extract_barcode(more_info)
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
            original_price=self._extract_original_price(),
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
            application_form=self._extract_application_form(title),
            target_audience=self._extract_target_audience(categories, title),
            weight_grams=self._extract_weight(),
            seo_title=self._generate_seo_title(title, brand, categories),
            seo_description=self._generate_seo_description(title, brand, categories, sections),
            google_product_category=self._determine_google_category(categories),
            google_mpn=sku,
            google_age_group=self._determine_google_age_group(categories),
        )

    @staticmethod
    def _extract_barcode(more_info: str) -> str:
        """Extract barcode from 'Допълнителна информация' text."""
        if not more_info:
            return ""
        match = re.search(r'Баркод\s*:\s*(\S+)', more_info)
        return match.group(1) if match else ""

    def _extract_title(self) -> str:
        """Extract product title (cached after first call)."""
        if self._cached_title is not None:
            return self._cached_title

        title = ""

        # Try JSON-LD first
        if self.json_ld and self.json_ld.get("name"):
            title = self.json_ld["name"].strip()
        else:
            # Fallback to H1
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

    def _extract_prices(self) -> tuple[str, str]:
        """Extract regular prices in BGN and EUR (ignoring promotions)."""
        price_bgn = ""
        price_eur = ""

        # Primary: Get price from main product area (.product-info .product-prices)
        # This contains the regular price (shown as old-price when on promotion)
        price_area = self.soup.select_one(".product-info .product-prices")
        if price_area:
            text = price_area.get_text()
            bgn_match = re.search(r'(\d+[.,]\d{2})\s*лв', text)
            eur_match = re.search(r'(\d+[.,]\d{2})\s*€', text)
            if bgn_match:
                price_bgn = bgn_match.group(1).replace(",", ".")
            if eur_match:
                price_eur = eur_match.group(1).replace(",", ".")

        # Fallback: Use JSON-LD price (EUR only)
        if not price_eur and self.json_ld:
            offers = self.json_ld.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = offers.get("price")
            if price:
                price_eur = f"{float(str(price).replace(',', '.')):.2f}"
                # Convert to BGN if not found
                if not price_bgn:
                    # 1.95583 is the legally fixed EUR/BGN rate (EU Council, ERM II)
                    price_bgn = f"{float(price_eur) * 1.95583:.2f}"

        return price_bgn, price_eur

    # Site does not expose original/compare-at price or availability status.
    # Stubbed for ExtractedProduct interface; override in future site extractors.
    @staticmethod
    def _extract_original_price() -> str:
        return ""

    @staticmethod
    def _extract_availability() -> str:
        return ""

    def _extract_categories(self, product_title: str = "") -> list[str]:
        """Extract category breadcrumb."""
        categories = []
        if not product_title:
            product_title = self._extract_title()

        # Try JSON-LD BreadcrumbList
        scripts = self.soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Handle both direct object and array format
                breadcrumb_data = None
                if isinstance(data, dict) and data.get("@type") == "BreadcrumbList":
                    breadcrumb_data = data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "BreadcrumbList":
                            breadcrumb_data = item
                            break

                if breadcrumb_data:
                    for item in breadcrumb_data.get("itemListElement", []):
                        name = item.get("name") or item.get("item", {}).get("name", "")
                        if name and name.lower() != "начало" and name != product_title:
                            if len(name) < 50 or product_title not in name:
                                categories.append(name)
                    if categories:
                        return categories
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        # Fallback to HTML breadcrumb
        breadcrumb = self.soup.select(".breadcrumb a, .breadcrumbs a, nav[aria-label='breadcrumb'] a")
        for crumb in breadcrumb:
            text = crumb.get_text(strip=True)
            if text and text.lower() not in ["начало", "home"] and text != product_title:
                categories.append(text)

        return categories

    @staticmethod
    def _extract_highlights() -> list[str]:
        # Site has no highlights section; content is in tab sections instead.
        return []

    def _extract_tab_content(self, section_name: str, page_text: str) -> str:
        """Extract content for a specific section by finding text between headings."""
        page_lower = page_text.lower()
        section_lower = section_name.lower()

        # Section headers on pharmacy product pages
        section_markers = [
            "какво представлява",       # details
            "активни съставки",         # composition
            "противопоказания",         # contraindications
            "дозировка и начин на употреба",  # usage
            "допълнителна информация",  # more_info
            "все още няма ревюта",      # end marker (reviews section)
        ]

        # Skip tab headers - find "какво представлява" as content area start
        content_area_start = page_lower.find("какво представлява")
        if content_area_start == -1:
            content_area_start = 0

        # Find start of this section (after content area start)
        start_idx = page_lower.find(section_lower, content_area_start)
        if start_idx == -1:
            return ""

        # Move past the section header
        start_idx += len(section_lower)

        # Find where the next section starts
        end_idx = len(page_text)
        for marker in section_markers:
            if marker == section_lower:
                continue
            idx = page_lower.find(marker, start_idx)
            if idx != -1 and idx < end_idx:
                end_idx = idx

        # Extract and clean content
        content = page_text[start_idx:end_idx].strip()

        # Clean up whitespace
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        content = "\n".join(lines)

        # Remove any remaining noise
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
        seen_urls = set()

        def is_product_image(url: str) -> bool:
            """Check if URL is a product image (not icon/logo)."""
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
            """Normalize URL for deduplication.

            Both uploads/images/products/X/Y and media/cache/{variant}/images/products/X/Y
            normalize to the same key so we don't get duplicate images.
            """
            match = re.search(r'/images/products/.*', url)
            return match.group(0) if match else url

        def encode_url(url: str) -> str:
            """URL-encode special characters in filename."""
            # Split URL into parts and encode the filename
            parsed = urlparse(url)
            path_parts = parsed.path.rsplit('/', 1)
            if len(path_parts) == 2:
                directory, filename = path_parts
                # Encode filename preserving already-encoded chars
                encoded_filename = quote(filename, safe='%')
                encoded_path = directory + '/' + encoded_filename
                return parsed._replace(path=encoded_path).geturl()
            return url

        # Try JSON-LD image
        if self.json_ld:
            img_data = self.json_ld.get("image")
            if img_data:
                if isinstance(img_data, str):
                    img_urls = [img_data]
                elif isinstance(img_data, list):
                    img_urls = img_data
                else:
                    img_urls = []

                for url in img_urls:
                    if not url:
                        continue
                    # Rewrite uploads/ to product_view_default (higher quality, always available)
                    url_stripped = url.lstrip('/')
                    if url_stripped.startswith('uploads/'):
                        url_stripped = url_stripped.replace('uploads/', 'media/cache/product_view_default/', 1)
                    # Make absolute URL if relative
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

        # Try gallery images
        gallery_imgs = self.soup.select(".site-gallery img, .product-gallery img, .gallery img, .product-image img")
        for img in gallery_imgs:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy")
            if src:
                # Make absolute URL if relative
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

        # Optionally validate image URLs with HEAD requests; fallback to product_view_default if broken
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
        # Look for weight in product info
        info_rows = self.soup.select(".product-info tr, .additional-info tr")
        for row in info_rows:
            label = row.select_one("th, td:first-child")
            value = row.select_one("td:last-child")
            if label and value:
                label_text = label.get_text().lower()
                if "тегло" in label_text or "weight" in label_text:
                    weight_text = value.get_text()
                    return self._parse_weight(weight_text)

        # Try to extract from title (e.g., "500ml", "100g")
        title = self._extract_title()
        return self._parse_weight(title)

    def _parse_weight(self, text: str) -> int:
        """Parse weight/volume from text and convert to grams."""
        if not text:
            return 0

        text = text.lower()

        # Patterns: 500mg, 100g, 50ml, 1.5kg, etc.
        patterns = [
            (r'(\d+(?:[.,]\d+)?)\s*kg', 1000),      # kg to g
            (r'(\d+(?:[.,]\d+)?)\s*(?:g|гр)', 1),   # g stays g
            (r'(\d+(?:[.,]\d+)?)\s*(?:ml|мл)', 1),  # ml ≈ g for liquids
            (r'(\d+(?:[.,]\d+)?)\s*(?:l|л)', 1000), # l to g
            (r'(\d+(?:[.,]\d+)?)\s*mg', 0.001),     # mg to g (min 1g)
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1).replace(",", "."))
                grams = value * multiplier
                return max(1, round(grams)) if grams > 0 else 0

        return 0

    def _build_description(self, brand: str, highlights: list[str], sections: dict) -> str:
        """Build full HTML description from all sections.

        Args:
            brand: Product brand name
            highlights: Product highlight bullet points
            sections: Dict with keys: details, composition, usage, contraindications, more_info
        """
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
                # Split multi-line content into separate <p> tags
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                for line in lines:
                    parts.append(f"<p>{line}</p>")

        return "\n".join(parts)

    def _generate_handle(self, title: str) -> str:
        """Generate URL-friendly handle from source URL slug.

        Uses URL slug instead of title to prevent duplicates when
        the site has multiple pages with the same product title.
        """
        # Extract slug from source URL (e.g., /product-name-123 -> product-name-123)
        parsed = urlparse(self.url)
        slug = parsed.path.strip('/').split('/')[-1]

        if slug:
            # Clean up the slug - should already be URL-friendly
            handle = slug.lower()
            handle = re.sub(r'[^a-z0-9-]+', '-', handle)
            handle = re.sub(r'-+', '-', handle)
            handle = handle.strip('-')
            if handle:
                return handle[:200]  # Shopify handle limit

        # Fallback: generate from title if URL slug extraction fails
        if not title:
            return ""

        return transliterate_handle(title)[:200]  # Shopify handle limit

    def _generate_seo_title(self, title: str, brand: str, categories: list[str]) -> str:
        """Generate SEO title with progressive fallback.

        Tries formats in order until one fits within max length:
        1. "Brand Product - Category | ViaPharma"
        2. "Brand Product | ViaPharma"
        3. "Product | ViaPharma"
        4. "Product... | ViaPharma" (truncated)
        """
        if not title:
            return ""

        store_name = self._seo_settings.get("store_name", "ViaPharma")
        max_len = self._seo_settings.get("title_max_length", 70)
        suffix = f" | {store_name}"

        # Deduplicate brand from title if title already starts with brand
        display_title = title
        if brand and title.lower().startswith(brand.lower()):
            display_title = title[len(brand):].lstrip(" -–—")

        category = categories[0] if categories else ""

        # Try: "Brand Product - Category | ViaPharma"
        if brand and category:
            candidate = f"{brand} {display_title} - {category}{suffix}"
            if len(candidate) <= max_len:
                return candidate

        # Try: "Brand Product | ViaPharma"
        if brand:
            candidate = f"{brand} {display_title}{suffix}"
            if len(candidate) <= max_len:
                return candidate

        # Try: "Product | ViaPharma"
        candidate = f"{title}{suffix}"
        if len(candidate) <= max_len:
            return candidate

        # Truncate title to fit store name suffix
        available = max_len - len(suffix) - 3  # 3 for "..."
        if available > 0:
            return f"{title[:available]}...{suffix}"

        return title[:max_len]

    def _generate_seo_description(self, title: str, brand: str, categories: list[str], sections: dict) -> str:
        """Generate structured SEO meta description in Bulgarian.

        Format: "Купете {Brand} {Title}. {FirstSentence}. Поръчайте в {Category} на ViaPharma."
        Progressive fallback if too long.
        """
        store_name = self._seo_settings.get("store_name", "ViaPharma")
        max_len = self._seo_settings.get("description_max_length", 155)

        category = categories[0] if categories else ""

        # Build product name (deduplicate brand from title)
        if brand and title.lower().startswith(brand.lower()):
            product_name = title
        elif brand:
            product_name = f"{brand} {title}"
        else:
            product_name = title

        # Extract first sentence from details for benefit text
        details = sections.get("details", "")
        first_sentence = ""
        if details:
            # Split on sentence-ending punctuation
            sentences = re.split(r'[.!?]', details)
            if sentences and sentences[0].strip():
                first_sentence = sentences[0].strip()

        # Build CTA suffix
        if category:
            cta = f"Поръчайте в {category} на {store_name}."
        else:
            cta = f"Поръчайте на {store_name}."

        # Try: "Купете {product_name}. {first_sentence}. {cta}"
        if first_sentence:
            candidate = f"Купете {product_name}. {first_sentence}. {cta}"
            if len(candidate) <= max_len:
                return candidate

        # Try: "Купете {product_name}. {cta}"
        candidate = f"Купете {product_name}. {cta}"
        if len(candidate) <= max_len:
            return candidate

        # Truncate to fit
        candidate = f"Купете {product_name}."
        if len(candidate) <= max_len:
            return candidate

        return candidate[:max_len]

    def _optimize_image_alt_texts(self, images: list[ProductImage], brand: str, title: str) -> None:
        """Optimize image alt texts with brand and position context.

        Single image: "Brand ProductName"
        Multiple: "Brand ProductName - Снимка 1 от 3", etc.
        Max 125 chars.
        """
        if not images:
            return

        # Deduplicate brand from alt text if title already starts with brand
        if brand and title.lower().startswith(brand.lower()):
            base_alt = title
        elif brand:
            base_alt = f"{brand} {title}"
        else:
            base_alt = title
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

    @staticmethod
    def _extract_application_form(title: str) -> str:
        """Extract pharmaceutical application form from product title.

        Pattern-matches Bulgarian form keywords, ordered specific→general.
        Returns canonical Bulgarian label or empty string.
        """
        if not title:
            return ""

        title_lower = title.lower()

        # Ordered specific→general to avoid false matches.
        # Each tuple: (keyword, label, is_stem).
        # Stem keywords use leading \b only (e.g., "пластир" matches "пластири").
        # Full keywords use \b on both sides to prevent false positives
        # (e.g., "гел" won't match inside "гелатинови" or "ангел").
        form_patterns = [
            # Solid oral
            ("таблетки", "Таблетки", False),
            ("капсули", "Капсули", False),
            ("сашета", "Сашета", False),
            ("саше", "Сашета", True),
            ("пастили", "Пастили", False),
            ("драже", "Драже", False),
            # Topical
            ("крем", "Крем", False),
            ("мехлем", "Мехлем", False),
            ("гел", "Гел", False),
            ("маска", "Маска", False),
            ("серум", "Серум", False),
            ("лосион", "Лосион", False),
            ("балсам", "Балсам", False),
            ("пяна", "Пяна", False),
            ("тоник", "Тоник", False),
            ("паста", "Паста", False),
            ("пудра", "Пудра", False),
            # Liquid
            ("спрей", "Спрей", False),
            ("капки", "Капки", False),
            ("разтвор", "Разтвор", False),
            ("сироп", "Сироп", False),
            ("суспензия", "Суспензия", False),
            ("олио", "Олио", False),
            ("масло", "Масло", False),
            # Care
            ("шампоан", "Шампоан", False),
            # Other
            ("пластир", "Пластири", True),
            ("супозитори", "Супозитории", True),
        ]

        for keyword, label, is_stem in form_patterns:
            pattern = rf'\b{keyword}' if is_stem else rf'\b{keyword}\b'
            if re.search(pattern, title_lower):
                return label

        return ""

    @staticmethod
    def _extract_target_audience(categories: list[str], title: str) -> str:
        """Derive target audience from categories and title.

        Priority: Бебета > Деца > Възрастни (default).
        """
        text = " ".join(categories).lower() + " " + title.lower()

        # Baby keywords (highest priority)
        baby_keywords = ["бебе", "бебета", "бебешк", "новородено", "кърмач"]
        for kw in baby_keywords:
            if kw in text:
                return "Бебета"

        # Child keywords
        child_keywords = ["дете", "деца", "детск"]
        for kw in child_keywords:
            if kw in text:
                return "Деца"

        return "Възрастни"

    def _determine_google_category(self, categories: list[str]) -> str:
        """Map product categories to Google Shopping taxonomy via config.

        Uses startswith matching so "Козметика, красота и лична хигиена"
        matches config key "Козметика".
        """
        category_map = self._seo_settings.get("google_shopping_category_map", {})
        default = self._seo_settings.get("google_shopping", {}).get(
            "default_category", "Health & Beauty > Health Care > Pharmacy"
        )

        for cat in categories:
            # Exact match first
            if cat in category_map:
                return category_map[cat]
            # Prefix match: category starts with a config key
            for config_key, google_cat in category_map.items():
                if cat.lower().startswith(config_key.lower()):
                    return google_cat

        return default

    def _determine_google_age_group(self, categories: list[str]) -> str:
        """Determine Google Shopping age group from categories."""
        child_keywords = ["дете", "бебе", "деца", "бебета", "детски", "бебешки"]
        categories_lower = " ".join(categories).lower()

        for keyword in child_keywords:
            if keyword in categories_lower:
                return "kids"

        return "adult"
