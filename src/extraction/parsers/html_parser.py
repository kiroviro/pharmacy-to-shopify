"""
HTML Content Parser

Extracts product information from HTML elements:
- Title from h1 tags
- Categories from breadcrumbs
- Highlights from product description lists
- Tab content from product tabs
- Images from JavaScript initialImages array
- Weight from product attributes table

This parser handles direct HTML element extraction when structured
data (JSON-LD, GTM) is not available.
"""

import re
from typing import List, Tuple

from bs4 import BeautifulSoup

from ...models import ProductImage


class HTMLContentParser:
    """
    Parses product content from HTML elements.

    Usage:
        parser = HTMLContentParser(soup, html)
        title = parser.extract_title()
        categories = parser.extract_categories()
        images = parser.extract_images()
    """

    def __init__(self, soup: BeautifulSoup, html: str = ""):
        """
        Initialize the HTML parser.

        Args:
            soup: BeautifulSoup object of the page
            html: Raw HTML string (needed for regex-based extraction)
        """
        self.soup = soup
        self.html = html

    def extract_title(self) -> str:
        """
        Extract product title from HTML.

        Tries multiple selectors in priority order.

        Returns:
            Product title or empty string
        """
        selectors = ['h1[itemprop="name"]', 'h1']

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                return self._clean_text(element.get_text())

        return ""

    def extract_categories(self) -> List[str]:
        """
        Extract category path from breadcrumb navigation.

        Returns:
            List of category names (excluding "Home")
        """
        categories = []

        # Try main nav breadcrumbs
        breadcrumb_nav = self.soup.select_one('nav.breadcrumbs')
        if breadcrumb_nav:
            links = breadcrumb_nav.find_all('a')
            for link in links:
                text = self._clean_text(link.get_text())
                if text and text.lower() not in ['home', 'начало', '']:
                    categories.append(text)
            if categories:
                return categories

        # Fallback: Try ordered list breadcrumbs
        breadcrumb_list = self.soup.select_one('ol.items')
        if breadcrumb_list:
            links = breadcrumb_list.find_all('a')
            for link in links:
                text = self._clean_text(link.get_text())
                if text and text.lower() not in ['home', 'начало', '']:
                    categories.append(text)

        return categories

    def extract_highlights(self, limit: int = 3) -> List[str]:
        """
        Extract product highlights/bullet points.

        Args:
            limit: Maximum number of highlights to return

        Returns:
            List of highlight strings
        """
        highlights = []

        # Try product description list
        desc_elem = self.soup.select_one('div[itemprop="description"]')
        if desc_elem:
            ul_elem = desc_elem.find('ul')
            if ul_elem:
                for li in ul_elem.find_all('li'):
                    text = self._clean_text(li.get_text())
                    if text and len(text) > 10:
                        highlights.append(text)

        # Fallback: Try other description divs
        if not highlights:
            for selector in ['.product-description ul', '.highlights ul']:
                elem = self.soup.select_one(selector)
                if elem:
                    for li in elem.find_all('li'):
                        text = self._clean_text(li.get_text())
                        if text and len(text) > 10:
                            highlights.append(text)
                    if highlights:
                        break

        return highlights[:limit]

    def extract_images(self) -> List[ProductImage]:
        """
        Extract all product images from JavaScript initialImages array.

        Returns:
            List of ProductImage objects
        """
        images = []

        # Extract from JavaScript initialImages JSON array
        pattern = r'"initialImages"\s*:\s*(\[.*?\])'
        match = re.search(pattern, self.html, re.DOTALL)

        if match:
            try:
                import json
                images_json = match.group(1)
                # Fix potential JSON issues (single quotes, trailing commas)
                images_json = images_json.replace("'", '"')
                images_data = json.loads(images_json)

                for idx, img_data in enumerate(images_data, 1):
                    if isinstance(img_data, dict):
                        # Use 'img' field for medium size images
                        img_url = img_data.get('img') or img_data.get('full') or img_data.get('thumb')

                        if img_url and '/media/catalog/product/' in img_url:
                            caption = img_data.get('caption', '')
                            images.append(ProductImage(
                                source_url=img_url,
                                position=idx,
                                alt_text=self._clean_text(caption)
                            ))
            except (json.JSONDecodeError, KeyError):
                pass

        # Fallback: Try schema.org image
        if not images:
            images = self._extract_schema_images()

        # Fallback: Try gallery images
        if not images:
            images = self._extract_gallery_images()

        return images

    def _extract_schema_images(self) -> List[ProductImage]:
        """Extract images from schema.org markup."""
        images = []

        img_elem = self.soup.select_one('[itemprop="image"]')
        if img_elem:
            src = img_elem.get('src') or img_elem.get('content')
            if src and '/media/catalog/product/' in src:
                alt = img_elem.get('alt', '')
                images.append(ProductImage(
                    source_url=src,
                    position=1,
                    alt_text=self._clean_text(alt)
                ))

        return images

    def _extract_gallery_images(self) -> List[ProductImage]:
        """Extract images from gallery elements."""
        images = []

        gallery = self.soup.select_one('.gallery-placeholder, .product-image-gallery')
        if gallery:
            for idx, img in enumerate(gallery.find_all('img'), 1):
                src = img.get('src') or img.get('data-src')
                if src and '/media/catalog/product/' in src:
                    alt = img.get('alt', '')
                    images.append(ProductImage(
                        source_url=src,
                        position=idx,
                        alt_text=self._clean_text(alt)
                    ))

        return images

    def extract_weight(self) -> Tuple[int, str]:
        """
        Extract product weight for shipping calculations.

        Returns:
            Tuple of (weight_in_grams, unit_string)
        """
        weight_grams = 0
        weight_unit = "kg"

        # Try "Повече информация" table
        weight_grams = self._extract_weight_from_table()

        # Fallback: Try title/description pattern matching
        if weight_grams == 0:
            weight_grams = self._extract_weight_from_text()

        return (weight_grams, weight_unit)

    def _extract_weight_from_table(self) -> int:
        """Extract weight from product attributes table."""
        table = self.soup.find('table', class_='additional-attributes')
        if not table:
            return 0

        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                label = self._clean_text(cells[0].get_text()).lower()
                if 'тегло' in label or 'weight' in label:
                    value = self._clean_text(cells[1].get_text())
                    return self._parse_weight_value(value)

        return 0

    def _extract_weight_from_text(self) -> int:
        """Extract weight from title or description using pattern matching."""
        # Get title
        title_elem = self.soup.select_one('h1')
        title = title_elem.get_text() if title_elem else ""

        # Get description
        desc_elem = self.soup.select_one('[itemprop="description"]')
        desc = desc_elem.get_text() if desc_elem else ""

        text = f"{title} {desc}"

        # Pattern: number followed by unit
        patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(kg|кг)',      # Kilograms
            r'(\d+(?:[.,]\d+)?)\s*(g|гр|грама)',  # Grams
            r'(\d+(?:[.,]\d+)?)\s*(ml|мл)',       # Milliliters (assume ~1g/ml)
            r'(\d+(?:[.,]\d+)?)\s*(l|л|литр)',    # Liters
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1).replace(',', '.'))
                unit = match.group(2).lower()
                return self._convert_to_grams(value, unit)

        return 0

    def _parse_weight_value(self, value: str) -> int:
        """Parse weight value string to grams."""
        # Extract number and unit
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(\w+)?', value)
        if match:
            num = float(match.group(1).replace(',', '.'))
            unit = (match.group(2) or 'g').lower()
            return self._convert_to_grams(num, unit)
        return 0

    def _convert_to_grams(self, value: float, unit: str) -> int:
        """Convert weight value to grams."""
        unit = unit.lower()

        if unit in ['kg', 'кг']:
            return int(value * 1000)
        elif unit in ['g', 'гр', 'грама', 'gr']:
            return int(value)
        elif unit in ['ml', 'мл']:
            return int(value)  # Assume liquid ~1g/ml
        elif unit in ['l', 'л', 'литр', 'литра']:
            return int(value * 1000)
        elif unit in ['mg', 'мг']:
            return max(1, int(value / 1000))

        return int(value)

    def extract_brand_from_html(self) -> str:
        """
        Extract brand from HTML elements.

        Returns:
            Brand name or empty string
        """
        selectors = ['[itemprop="brand"]', '.brand', '.manufacturer']

        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                text = self._clean_text(element.get_text())
                if text:
                    return text

        return ""

    def extract_brand_from_table(self) -> str:
        """
        Extract brand from "Повече информация" table.

        Returns:
            Brand name or empty string
        """
        table = self.soup.find('table', class_='additional-attributes')
        if not table:
            return ""

        for row in table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) >= 2:
                label = self._clean_text(cells[0].get_text()).lower()
                if 'марка' in label or 'brand' in label or 'производител' in label:
                    return self._clean_text(cells[1].get_text())

        return ""

    def extract_availability_from_html(self) -> str:
        """
        Extract availability status from HTML elements.

        Returns:
            Availability status or empty string
        """
        # Check for stock status div
        stock_elem = self.soup.select_one('div.stock, .availability, [itemprop="availability"]')
        if stock_elem:
            text = self._clean_text(stock_elem.get_text())
            if text:
                return text

        # Check page text for common phrases
        page_text = self.soup.get_text()

        if 'В наличност' in page_text:
            return 'В наличност'
        elif 'Няма в наличност' in page_text:
            return 'Няма в наличност'
        elif 'Ограничена наличност' in page_text:
            return 'Ограничена наличност'

        return ""

    def is_prescription_product(self) -> bool:
        """
        Check if the product is prescription-only.

        Returns:
            True if product requires prescription
        """
        page_text = self.soup.get_text()

        indicators = [
            'не може да бъде закупен онлайн',
            'Продукти по лекарско предписание',
            'лекарско предписание',
            'само с рецепта',
        ]

        for indicator in indicators:
            if indicator.lower() in page_text.lower():
                return True

        # Check breadcrumbs
        categories = self.extract_categories()
        for cat in categories:
            if 'лекарско предписание' in cat.lower():
                return True

        return False

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        return ' '.join(text.split()).strip()
