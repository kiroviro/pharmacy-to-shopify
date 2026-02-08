"""
Structured Data Parser

Extracts product information from JSON-LD structured data (schema.org).
This is the highest priority source for product data as it's explicitly
structured by the website for search engines.

Supported schema types: Drug, Product
"""

import json
from typing import Any, Dict

from bs4 import BeautifulSoup


class StructuredDataParser:
    """
    Parses JSON-LD structured data from HTML pages.

    JSON-LD is embedded in <script type="application/ld+json"> tags and
    contains schema.org structured data for products, drugs, etc.

    Usage:
        parser = StructuredDataParser()
        data = parser.parse(soup)
        brand = parser.extract_brand(data)
        price = parser.extract_price(data)
    """

    SUPPORTED_TYPES = ['Drug', 'Product']

    def parse(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract JSON-LD structured data from the page.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            Parsed JSON-LD data as dictionary, or empty dict if not found
        """
        scripts = soup.find_all('script', type='application/ld+json')

        for script in scripts:
            if script.string:
                try:
                    data = json.loads(script.string)
                    # Look for Drug or Product type
                    if isinstance(data, dict) and data.get('@type') in self.SUPPORTED_TYPES:
                        return data
                except json.JSONDecodeError:
                    continue

        return {}

    def extract_brand(self, data: Dict[str, Any]) -> str:
        """
        Extract brand name from structured data.

        Args:
            data: Parsed JSON-LD data

        Returns:
            Brand name or empty string
        """
        if not data:
            return ""

        brand_data = data.get("brand")
        if isinstance(brand_data, dict):
            return self._clean_text(brand_data.get("name", ""))
        elif isinstance(brand_data, str):
            return self._clean_text(brand_data)

        return ""

    def extract_price(self, data: Dict[str, Any]) -> str:
        """
        Extract current price from structured data.

        Args:
            data: Parsed JSON-LD data

        Returns:
            Price as string (e.g., "7.71") or empty string
        """
        if not data:
            return ""

        offers = data.get("offers", [])
        if isinstance(offers, dict):
            offers = [offers]

        if offers:
            price = offers[0].get("price")
            if price is not None:
                return str(price)

        return ""

    def extract_availability(self, data: Dict[str, Any]) -> str:
        """
        Extract availability status from structured data.

        Maps schema.org availability URLs to Bulgarian status text.

        Args:
            data: Parsed JSON-LD data

        Returns:
            Availability status in Bulgarian
        """
        if not data:
            return ""

        offers = data.get("offers", [])
        if isinstance(offers, dict):
            offers = [offers]

        if offers:
            availability = offers[0].get("availability", "")
            return self._map_availability(availability)

        return ""

    def extract_sku(self, data: Dict[str, Any]) -> str:
        """
        Extract SKU from structured data.

        Args:
            data: Parsed JSON-LD data

        Returns:
            SKU as string or empty string
        """
        if not data:
            return ""

        sku = data.get("sku")
        return str(sku) if sku else ""

    def extract_image(self, data: Dict[str, Any]) -> str:
        """
        Extract main image URL from structured data.

        Args:
            data: Parsed JSON-LD data

        Returns:
            Image URL or empty string
        """
        if not data:
            return ""

        image = data.get("image")
        if isinstance(image, list) and image:
            return str(image[0])
        elif isinstance(image, str):
            return image

        return ""

    def extract_active_ingredient(self, data: Dict[str, Any]) -> str:
        """
        Extract active ingredient/composition from structured data.

        Args:
            data: Parsed JSON-LD data

        Returns:
            Active ingredient text or empty string
        """
        if not data:
            return ""

        return self._clean_text(data.get("activeIngredient", ""))

    def extract_clinical_pharmacology(self, data: Dict[str, Any]) -> str:
        """
        Extract clinical pharmacology text from structured data.

        This field typically contains details, usage, and warnings.

        Args:
            data: Parsed JSON-LD data

        Returns:
            Clinical pharmacology text or empty string
        """
        if not data:
            return ""

        return self._clean_text(data.get("clinicalPharmacology", ""))

    def has_data(self, data: Dict[str, Any]) -> bool:
        """
        Check if structured data contains useful product information.

        Args:
            data: Parsed JSON-LD data

        Returns:
            True if data has brand, price, or other useful fields
        """
        if not data:
            return False

        return bool(
            data.get("brand") or
            data.get("offers") or
            data.get("sku") or
            data.get("activeIngredient")
        )

    def _map_availability(self, schema_url: str) -> str:
        """Map schema.org availability URL to Bulgarian text."""
        availability_map = {
            "https://schema.org/InStock": "В наличност",
            "https://schema.org/OutOfStock": "Няма в наличност",
            "https://schema.org/LimitedAvailability": "Ограничена наличност",
            "https://schema.org/PreOrder": "Предварителна поръчка",
            "https://schema.org/SoldOut": "Изчерпано",
            "http://schema.org/InStock": "В наличност",
            "http://schema.org/OutOfStock": "Няма в наличност",
        }
        return availability_map.get(schema_url, "")

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        return ' '.join(text.split()).strip()
