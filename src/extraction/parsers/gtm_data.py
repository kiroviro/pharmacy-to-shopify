"""
GTM Data Parser

Extracts product information from Google Tag Manager dl4Objects data.
This data is embedded in JavaScript and contains ecommerce tracking info.

The dl4Objects array typically contains:
- item_name: Product title
- item_brand: Brand name
- item_id: SKU/product ID
- price: Current price
- item_stock_status: Stock availability
"""

import json
import re
from typing import Any, Dict


class GTMDataParser:
    """
    Parses Google Tag Manager dl4Objects data from page HTML.

    GTM data is embedded as JavaScript:
        var dl4Objects = [{item_name: "...", item_brand: "...", ...}];

    Usage:
        parser = GTMDataParser()
        data = parser.parse(html)
        title = parser.extract_title(data)
        brand = parser.extract_brand(data)
    """

    # Regex pattern to extract dl4Objects array from JavaScript
    DL4_PATTERN = r'var\s+dl4Objects\s*=\s*(\[.*?\]);'

    def parse(self, html: str) -> Dict[str, Any]:
        """
        Extract GTM dl4Objects data from page HTML.

        Args:
            html: Raw HTML string of the page

        Returns:
            Parsed GTM data as dictionary, or empty dict if not found
        """
        match = re.search(self.DL4_PATTERN, html, re.DOTALL)

        if match:
            try:
                json_str = match.group(1)
                data_list = json.loads(json_str)

                # Find first object with item data
                for item in data_list:
                    if isinstance(item, dict) and ('item_name' in item or 'item_brand' in item):
                        return item

            except (json.JSONDecodeError, IndexError):
                pass

        return {}

    def extract_title(self, data: Dict[str, Any]) -> str:
        """
        Extract product title from GTM data.

        Args:
            data: Parsed GTM data

        Returns:
            Product title or empty string
        """
        if not data:
            return ""

        return self._clean_text(data.get("item_name", ""))

    def extract_brand(self, data: Dict[str, Any]) -> str:
        """
        Extract brand name from GTM data.

        Args:
            data: Parsed GTM data

        Returns:
            Brand name or empty string
        """
        if not data:
            return ""

        return self._clean_text(data.get("item_brand", ""))

    def extract_sku(self, data: Dict[str, Any]) -> str:
        """
        Extract SKU/product ID from GTM data.

        Args:
            data: Parsed GTM data

        Returns:
            SKU as string or empty string
        """
        if not data:
            return ""

        item_id = data.get("item_id")
        return str(item_id) if item_id else ""

    def extract_price(self, data: Dict[str, Any]) -> str:
        """
        Extract price from GTM data.

        Args:
            data: Parsed GTM data

        Returns:
            Price as string or empty string
        """
        if not data:
            return ""

        price = data.get("price")
        return str(price) if price else ""

    def extract_stock_status(self, data: Dict[str, Any]) -> str:
        """
        Extract stock status from GTM data.

        Args:
            data: Parsed GTM data

        Returns:
            Stock status string or empty string
        """
        if not data:
            return ""

        return self._clean_text(data.get("item_stock_status", ""))

    def extract_category(self, data: Dict[str, Any]) -> str:
        """
        Extract category from GTM data.

        Args:
            data: Parsed GTM data

        Returns:
            Category string or empty string
        """
        if not data:
            return ""

        return self._clean_text(data.get("item_category", ""))

    def has_data(self, data: Dict[str, Any]) -> bool:
        """
        Check if GTM data contains useful product information.

        Args:
            data: Parsed GTM data

        Returns:
            True if data has name, brand, or price
        """
        if not data:
            return False

        return bool(
            data.get("item_name") or
            data.get("item_brand") or
            data.get("price")
        )

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        if not isinstance(text, str):
            text = str(text)
        return ' '.join(text.split()).strip()
