"""
Specialized parsers for product data extraction.

Each parser handles a specific data source:
- StructuredDataParser: JSON-LD structured data (schema.org)
- GTMDataParser: Google Tag Manager dl4Objects
- HTMLContentParser: HTML element extraction
- LeafletParser: Pharmaceutical leaflet sections
"""

from .structured_data import StructuredDataParser
from .gtm_data import GTMDataParser
from .html_parser import HTMLContentParser
from .leaflet_parser import LeafletParser

__all__ = [
    'StructuredDataParser',
    'GTMDataParser',
    'HTMLContentParser',
    'LeafletParser',
]
