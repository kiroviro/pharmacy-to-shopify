"""
Product extraction modules for pharmacy sites.

Modules:
    benu_extractor - BenuExtractor for benu.bg
    validator - SpecificationValidator for data validation
    brand_matcher - Match product titles to known brand names
    bulk_extractor - Bulk extraction with progress tracking
    utils - Helper functions (remove_source_references)
    parsers - Specialized parsers for different data sources
"""

from urllib.parse import urlparse

from .benu_extractor import BenuExtractor
from .validator import SpecificationValidator
from .brand_matcher import BrandMatcher, get_brand_matcher, match_brand
from .bulk_extractor import BulkExtractor
from .utils import remove_source_references
from .parsers import (
    StructuredDataParser,
    GTMDataParser,
    HTMLContentParser,
    LeafletParser,
)

# Registry of supported site extractors
SITE_EXTRACTORS = {
    'benu.bg': BenuExtractor,
}


def get_extractor_for_url(url: str):
    """
    Get the appropriate extractor class for a URL.

    Args:
        url: Product URL

    Returns:
        Extractor class (e.g., BenuExtractor)

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
        Site identifier (e.g., "benu.bg")
    """
    domain = urlparse(url).netloc.lower()

    for site in SITE_EXTRACTORS:
        if site in domain:
            return site

    return domain


__all__ = [
    # Site-specific extractors
    'BenuExtractor',
    # Helper functions
    'get_extractor_for_url',
    'get_site_from_url',
    # Validator
    'SpecificationValidator',
    # Brand matching
    'BrandMatcher',
    'get_brand_matcher',
    'match_brand',
    # Bulk extraction
    'BulkExtractor',
    # Utilities
    'remove_source_references',
    # Parsers
    'StructuredDataParser',
    'GTMDataParser',
    'HTMLContentParser',
    'LeafletParser',
]
