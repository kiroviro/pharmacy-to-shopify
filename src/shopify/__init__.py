"""
Shopify integration modules.

Modules:
    api_client - Shared REST/GraphQL client for Shopify Admin API
    collections - Smart collection creation from tags/vendors
    menus - Navigation menu creation
    csv_exporter - Product export to Shopify CSV format
"""

from .api_client import ShopifyAPIClient
from .collections import ShopifyCollectionCreator
from .menus import ShopifyMenuCreator
from .csv_exporter import (
    ShopifyCSVExporter,
    SHOPIFY_FIELDNAMES,
    remove_source_references,
)

__all__ = [
    # API Client
    'ShopifyAPIClient',
    # Collections
    'ShopifyCollectionCreator',
    # Menus
    'ShopifyMenuCreator',
    # CSV Export
    'ShopifyCSVExporter',
    'SHOPIFY_FIELDNAMES',
    'remove_source_references',
]
