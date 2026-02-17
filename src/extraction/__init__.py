"""
Product extraction modules for pharmacy sites.

Modules:
    pharmacy_extractor - PharmacyExtractor for pharmacy.example.com
    validator - SpecificationValidator for data validation
    brand_matcher - Match product titles to known brand names
    bulk_extractor - Bulk extraction with progress tracking
"""

from urllib.parse import urlparse

from ..common.text_utils import remove_source_references
from .brand_matcher import BrandMatcher
from .bulk_extractor import BulkExtractor
from .pharmacy_extractor import PharmacyExtractor
from .validator import SpecificationValidator

# Registry of supported site extractors
SITE_EXTRACTORS = {
    'pharmacy.example.com': PharmacyExtractor,
    'benu.bg': PharmacyExtractor,
}


def get_extractor_for_url(url: str):
    """
    Get the appropriate extractor class for a URL.

    Args:
        url: Product URL

    Returns:
        Extractor class (e.g., PharmacyExtractor)

    Raises:
        ValueError: If site is not supported
    """
    domain = urlparse(url).netloc.lower()

    for site, extractor_class in SITE_EXTRACTORS.items():
        if site in domain:
            return extractor_class

    supported = ', '.join(SITE_EXTRACTORS.keys())
    raise ValueError(f"Unsupported site: {domain}. Supported: {supported}")


def get_site_from_url(url: str) -> str:
    """
    Get site identifier from URL.

    Args:
        url: Any URL from the site

    Returns:
        Site identifier (e.g., "pharmacy.example.com")
    """
    domain = urlparse(url).netloc.lower()

    for site in SITE_EXTRACTORS:
        if site in domain:
            return site

    return domain


__all__ = [
    # Site-specific extractors
    'PharmacyExtractor',
    # Helper functions
    'get_extractor_for_url',
    'get_site_from_url',
    # Validator
    'SpecificationValidator',
    # Brand matching
    'BrandMatcher',
    # Bulk extraction
    'BulkExtractor',
    # Utilities
    'remove_source_references',
]
