"""
Brand Matcher

Matches product titles to known brand names using multiple strategies:
1. Exact match from structured data (JSON-LD, GTM)
2. Title prefix matching against known brands list
3. Multi-word brand matching (e.g., "La Roche-Posay", "Nature's Way")

The known brands list is loaded from config/known_brands.yaml.
"""

from typing import Optional, Set

from ..common.config_loader import get_brands_lowercase_map, load_known_brands


class BrandMatcher:
    """
    Matches product titles to known brand names.

    Usage:
        matcher = BrandMatcher()
        brand = matcher.match(
            title="Nivea Creme 150ml",
            structured_brand="",  # From JSON-LD
            gtm_brand=""          # From GTM data
        )
        # Returns: "Nivea"
    """

    def __init__(self, brands: Optional[Set[str]] = None):
        """
        Initialize the brand matcher.

        Args:
            brands: Optional set of known brands. If None, loads from config.
        """
        if brands is None:
            self.known_brands = load_known_brands()
        else:
            self.known_brands = brands

        # Create lowercase lookup for case-insensitive matching
        self.brands_lower = get_brands_lowercase_map(self.known_brands)

    def match(
        self,
        title: str,
        structured_brand: str = "",
        gtm_brand: str = ""
    ) -> str:
        """
        Match a product to a brand using multiple strategies.

        Priority order:
        1. Structured data brand (JSON-LD) - most reliable
        2. GTM data brand - second choice
        3. Title prefix matching - fallback

        Args:
            title: Product title
            structured_brand: Brand from JSON-LD structured data
            gtm_brand: Brand from GTM dl4Objects

        Returns:
            Matched brand name (canonical capitalization) or empty string
        """
        # Priority 1: Structured data (most reliable)
        stripped = structured_brand.strip() if structured_brand else ""
        if stripped:
            return stripped

        # Priority 2: GTM data
        stripped = gtm_brand.strip() if gtm_brand else ""
        if stripped:
            return stripped

        # Priority 3: Title prefix matching
        return self.match_from_title(title)

    def match_from_title(self, title: str) -> str:
        """
        Extract brand from product title using prefix matching.

        Tries to match the beginning of the title against known brands,
        checking multi-word brands first (3 words, then 2, then 1).

        Args:
            title: Product title

        Returns:
            Matched brand name or empty string

        Example:
            >>> matcher.match_from_title("La Roche-Posay Effaclar Gel 200ml")
            'La Roche-Posay'
            >>> matcher.match_from_title("Nivea Creme 150ml")
            'Nivea'
        """
        if not title:
            return ""

        words = title.split()

        # Try multi-word matches first (3 words, then 2, then 1)
        # This ensures "La Roche-Posay" matches before "La"
        for n in [3, 2, 1]:
            if len(words) >= n:
                candidate = ' '.join(words[:n]).lower()
                if candidate in self.brands_lower:
                    return self.brands_lower[candidate]

        return ""

    def is_known_brand(self, brand: str) -> bool:
        """
        Check if a brand name is in the known brands list.

        Args:
            brand: Brand name to check

        Returns:
            True if brand is known (case-insensitive)
        """
        return brand.lower() in self.brands_lower

    def get_canonical_name(self, brand: str) -> str:
        """
        Get the canonical capitalization of a brand name.

        Args:
            brand: Brand name (any capitalization)

        Returns:
            Canonical brand name or original if not found

        Example:
            >>> matcher.get_canonical_name("abopharma")
            'AboPharma'
        """
        return self.brands_lower.get(brand.lower(), brand)

    @property
    def brand_count(self) -> int:
        """Return the number of known brands."""
        return len(self.known_brands)
