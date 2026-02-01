"""
Data models for product extraction.

This module contains pure data classes with no business logic.
"""

from .product import ProductImage, ProductVariant, ExtractedProduct

__all__ = ['ProductImage', 'ProductVariant', 'ExtractedProduct']
