"""
Product extraction modules.

Modules:
    pharmacy_extractor - PharmacyExtractor for product page extraction
    validator - SpecificationValidator for data validation
    brand_matcher - Match product titles to known brand names
    bulk_extractor - Bulk extraction with progress tracking
"""

from .brand_matcher import BrandMatcher
from .bulk_extractor import BulkExtractor
from .consistency_checker import SourceConsistencyChecker
from .pharmacy_extractor import PharmacyExtractor
from .validator import SpecificationValidator

__all__ = [
    'PharmacyExtractor',
    'SpecificationValidator',
    'SourceConsistencyChecker',
    'BrandMatcher',
    'BulkExtractor',
]
