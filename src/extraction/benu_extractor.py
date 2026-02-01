"""
BENU.bg Product Extractor

Extracts product data from benu.bg Bulgarian pharmacy website.
"""

import re
import json
from typing import Optional, List, Dict
from urllib.parse import urlparse, quote

import requests
from bs4 import BeautifulSoup

from ..models import ExtractedProduct, ProductImage
from .brand_matcher import BrandMatcher
from ..common.transliteration import transliterate


class BenuExtractor:
    """Extracts product data from a pharmacy site."""

    def __init__(self, url: str, site_domain: str = "benu.bg"):
        self.url = url
        self.SITE_DOMAIN = site_domain
        self.html = None
        self.soup = None
        self.json_ld = None
        self.brand_matcher = BrandMatcher()
        self.product_type = "otc"

    def fetch(self) -> None:
        """Fetch the product page HTML."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
        }
        response = requests.get(self.url, headers=headers, timeout=30)
        response.raise_for_status()
        self.html = response.text
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
                    break
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            self.json_ld = item
                            break
            except (json.JSONDecodeError, TypeError):
                continue

    def extract(self) -> ExtractedProduct:
        """Extract all product data."""
        title = self._extract_title()
        brand = self._extract_brand(title)
        categories = self._extract_categories()
        price_bgn, price_eur = self._extract_prices()

        # Build tags from categories (for Shopify smart collections)
        tags = list(categories)  # Copy categories as tags

        return ExtractedProduct(
            title=title,
            url=self.url,
            handle=self._generate_handle(title),
            brand=brand,
            sku=self._extract_sku(),
            price=price_bgn,
            price_eur=price_eur,
            original_price=self._extract_original_price(),
            availability=self._extract_availability(),
            category_path=categories,
            highlights=self._extract_highlights(),
            details=self._extract_tab_content("Какво представлява"),
            composition=self._extract_tab_content("Активни съставки"),
            usage=self._extract_tab_content("Дозировка и начин на употреба"),
            contraindications=self._extract_tab_content("Противопоказания"),
            more_info=self._extract_tab_content("Допълнителна информация"),
            description=self._build_description(),
            images=self._extract_images(),
            tags=tags,
            weight_grams=self._extract_weight(),
            seo_title=title[:70] if title else "",
            seo_description=self._generate_seo_description(),
        )

    def _extract_title(self) -> str:
        """Extract product title."""
        # Try JSON-LD first
        if self.json_ld and self.json_ld.get("name"):
            return self.json_ld["name"].strip()

        # Fallback to H1
        h1 = self.soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return ""

    def _extract_brand(self, title: str) -> str:
        """Extract brand name."""
        # Try JSON-LD
        if self.json_ld:
            brand_data = self.json_ld.get("brand")
            if isinstance(brand_data, dict):
                brand = brand_data.get("name", "")
            else:
                brand = brand_data or ""
            if brand:
                return brand.strip()

        # Try brand matcher on title
        matched = self.brand_matcher.match_from_title(title)
        if matched:
            return matched

        return ""

    def _extract_sku(self) -> str:
        """Extract SKU/product code."""
        if self.json_ld and self.json_ld.get("sku"):
            return str(self.json_ld["sku"])
        return ""

    def _extract_prices(self) -> tuple:
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
                    price_bgn = f"{float(price_eur) * 1.95583:.2f}"

        return price_bgn, price_eur

    def _extract_original_price(self) -> str:
        """Original price not used - we extract regular price, ignoring promotions."""
        return ""

    def _extract_availability(self) -> str:
        """Extract availability status (not used - inventory not tracked)."""
        return ""

    def _extract_categories(self) -> List[str]:
        """Extract category breadcrumb."""
        categories = []
        product_title = self._extract_title()

        # Try JSON-LD BreadcrumbList
        scripts = self.soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string)
                # Handle both direct object and array format
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "BreadcrumbList":
                            data = item
                            break
                    else:
                        continue

                if isinstance(data, dict) and data.get("@type") == "BreadcrumbList":
                    items = data.get("itemListElement", [])
                    for item in items:
                        name = item.get("name") or item.get("item", {}).get("name", "")
                        # Skip "Начало" (Home) and the product name itself
                        if name and name.lower() != "начало" and name != product_title:
                            # Also skip if it looks like the product title (partial match)
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

    def _extract_highlights(self) -> List[str]:
        """Extract product highlights (optional for benu.bg)."""
        # benu.bg doesn't have a highlights section - return empty
        # Content is in ОПИСАНИЕ, СЪСТАВ, НАЧИН НА УПОТРЕБА, ПРОТИВОПОКАЗАНИЯ
        return []

    def _extract_tab_content(self, section_name: str) -> str:
        """Extract content for a specific section by finding text between headings."""
        page_text = self.soup.get_text(separator="\n")
        page_lower = page_text.lower()
        section_lower = section_name.lower()

        # Section headers on benu.bg product pages
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

    def _clean_html_content(self, element) -> str:
        """Clean HTML content preserving structure."""
        # Remove script and style tags
        for tag in element.find_all(["script", "style"]):
            tag.decompose()

        # Get text with some formatting
        text = element.get_text(separator="\n", strip=True)
        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _extract_images(self) -> List[ProductImage]:
        """Extract product images."""
        images = []
        seen_urls = set()

        def is_product_image(url: str) -> bool:
            """Check if URL is a product image (not icon/logo)."""
            if not url:
                return False
            url_lower = url.lower()
            # Exclude icons, logos, placeholders, cached versions, and non-product images
            exclude_patterns = ['.svg', 'icon', 'logo', 'heart', 'cart', 'arrow', 'close', 'search', 'default.jpg', 'default.png', '/media/cache/']
            for pattern in exclude_patterns:
                if pattern in url_lower:
                    return False
            # Must be in product images path or be a webp/jpg/png
            return '/images/products/' in url or url_lower.endswith(('.webp', '.jpg', '.jpeg', '.png', '.gif'))

        def normalize_url(url: str) -> str:
            """Normalize URL for deduplication."""
            # Remove cache/size suffixes to detect duplicates
            return re.sub(r'/media/cache/[^/]+/', '/media/', url)

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
                    # Make absolute URL if relative
                    if url and not url.startswith(('http://', 'https://')):
                        url = f"https://{self.SITE_DOMAIN}/{url.lstrip('/')}"

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
        gallery_imgs = self.soup.select(".benu-gallery img, .product-gallery img, .gallery img, .product-image img")
        for img in gallery_imgs:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy")
            if src:
                # Make absolute URL if relative
                if not src.startswith(('http://', 'https://')):
                    src = f"https://{self.SITE_DOMAIN}/{src.lstrip('/')}"

                if is_product_image(src):
                    normalized = normalize_url(src)
                    if normalized not in seen_urls:
                        seen_urls.add(normalized)
                        images.append(ProductImage(
                            source_url=encode_url(src),
                            position=len(images) + 1,
                            alt_text=img.get("alt", self._extract_title())
                        ))

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
            (r'(\d+(?:[.,]\d+)?)\s*mg', 0.001),    # mg to g
        ]

        for pattern, multiplier in patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1).replace(",", "."))
                return int(value * multiplier)

        return 0

    def _build_description(self) -> str:
        """Build full HTML description from all sections."""
        parts = []

        highlights = self._extract_highlights()
        if highlights:
            parts.append("<ul>")
            for h in highlights:
                parts.append(f"<li>{h}</li>")
            parts.append("</ul>")

        sections = [
            ("Описание", self._extract_tab_content("Какво представлява")),
            ("Състав", self._extract_tab_content("Активни съставки")),
            ("Начин на употреба", self._extract_tab_content("Дозировка и начин на употреба")),
            ("Противопоказания", self._extract_tab_content("Противопоказания")),
            ("Допълнителна информация", self._extract_tab_content("Допълнителна информация")),
        ]

        for title, content in sections:
            if content:
                parts.append(f"<h3>{title}</h3>")
                parts.append(f"<p>{content}</p>")

        return "\n".join(parts)

    def _generate_handle(self, title: str) -> str:
        """Generate URL-friendly handle from source URL slug.

        Uses URL slug instead of title to prevent duplicates when
        benu.bg has multiple pages with the same product title.
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

        # Transliterate Bulgarian to Latin
        handle = transliterate(title)

        # Lowercase and replace spaces/special chars with hyphens
        handle = handle.lower()
        handle = re.sub(r'[^a-z0-9]+', '-', handle)
        handle = re.sub(r'-+', '-', handle)
        handle = handle.strip('-')

        return handle[:200]  # Shopify handle limit

    def _generate_seo_description(self) -> str:
        """Generate SEO description."""
        highlights = self._extract_highlights()
        if highlights:
            return highlights[0][:155]

        if self.json_ld and self.json_ld.get("description"):
            return self.json_ld["description"][:155]

        return ""
