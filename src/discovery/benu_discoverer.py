"""
URL Discovery for benu.bg

Discovers all product URLs from the sitemap.
"""

import xml.etree.ElementTree as ET
from typing import Set, Optional

import requests


class BenuURLDiscoverer:
    """Discovers product URLs from a pharmacy site using its sitemap."""

    def __init__(
        self,
        verbose: bool = False,
        base_url: str = "https://benu.bg",
        sitemap_url: str = "https://benu.bg/sitemap.products.xml",
    ):
        self.verbose = verbose
        self.BASE_URL = base_url
        self.SITEMAP_URL = sitemap_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "bg-BG,bg;q=0.9,en;q=0.8",
        })
        self.product_urls: Set[str] = set()

    def log(self, message: str):
        """Print message if verbose mode is on."""
        if self.verbose:
            print(message)

    def discover_from_sitemap(self) -> Set[str]:
        """Fetch all product URLs from the sitemap."""
        print(f"Fetching sitemap from {self.SITEMAP_URL}...")

        response = self.session.get(self.SITEMAP_URL, timeout=30)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        # Handle XML namespace
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        for url_elem in root.findall("ns:url", ns):
            loc = url_elem.find("ns:loc", ns)
            if loc is not None and loc.text:
                self.product_urls.add(loc.text)

        print(f"Found {len(self.product_urls)} product URLs")
        return self.product_urls

    def discover_all_products(self, limit: int = 0, output_file: Optional[str] = None) -> Set[str]:
        """
        Discover all product URLs from the sitemap.

        Args:
            limit: Maximum number of URLs to return (0 = no limit)
            output_file: If provided, write URLs to this file

        Returns:
            Set of discovered product URLs
        """
        self.discover_from_sitemap()

        if limit and len(self.product_urls) > limit:
            self.product_urls = set(sorted(self.product_urls)[:limit])
            print(f"Limited to {limit} URLs")

        if output_file:
            self.save_urls(output_file)

        return self.product_urls

    def save_urls(self, filepath: str):
        """Save discovered URLs to a file."""
        sorted_urls = sorted(self.product_urls)

        with open(filepath, "w", encoding="utf-8") as f:
            for url in sorted_urls:
                f.write(url + "\n")

        print(f"Saved {len(sorted_urls)} URLs to {filepath}")

    def get_stats(self) -> dict:
        """Return discovery statistics."""
        return {
            "products_found": len(self.product_urls),
        }
