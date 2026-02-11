"""
Shopify CSV Exporter

Exports products to Shopify-compatible CSV format (Official Template).
Handles all 56 columns of the Shopify product import format.
"""

import csv
import logging
import os
from typing import Dict, List, Set

from ..common.csv_utils import configure_csv
from ..common.text_utils import remove_source_references
from ..models import ExtractedProduct, ProductImage

logger = logging.getLogger(__name__)

# Configure CSV for large fields
configure_csv()

# Official Shopify CSV columns (exact template format)
SHOPIFY_FIELDNAMES = [
    'Title', 'URL handle', 'Description', 'Vendor', 'Product category', 'Type', 'Tags',
    'Published on online store', 'Status', 'SKU', 'Barcode',
    'Option1 name', 'Option1 value', 'Option1 Linked To',
    'Option2 name', 'Option2 value', 'Option2 Linked To',
    'Option3 name', 'Option3 value', 'Option3 Linked To',
    'Price', 'Price EUR', 'Compare-at price', 'Cost per item', 'Charge tax', 'Tax code',
    'Inventory tracker', 'Inventory quantity', 'Continue selling when out of stock',
    'Weight value (grams)', 'Weight unit for display', 'Requires shipping',
    'Fulfillment service', 'Product image URL', 'Image position', 'Image alt text',
    'Variant image URL', 'Gift card', 'SEO title', 'SEO description',
    'Color (product.metafields.shopify.color-pattern)',
    'Форма (product.metafields.custom.application_form)',
    'За кого (product.metafields.custom.target_audience)',
    'Google Shopping / Google product category', 'Google Shopping / Gender',
    'Google Shopping / Age group', 'Google Shopping / Manufacturer part number (MPN)',
    'Google Shopping / Ad group name', 'Google Shopping / Ads labels',
    'Google Shopping / Condition', 'Google Shopping / Custom product',
    'Google Shopping / Custom label 0', 'Google Shopping / Custom label 1',
    'Google Shopping / Custom label 2', 'Google Shopping / Custom label 3',
    'Google Shopping / Custom label 4'
]


class ShopifyCSVExporter:
    """
    Exports products to Shopify-compatible CSV format.

    Usage:
        exporter = ShopifyCSVExporter()
        exporter.export_single(product, "output/product.csv")
        exporter.export_multiple(products, "output/products.csv")
    """

    def __init__(self, source_domain: str = "benu.bg"):
        """
        Initialize the exporter.

        Args:
            source_domain: Source domain to remove from text fields
        """
        self.fieldnames = SHOPIFY_FIELDNAMES
        self.source_domain = source_domain

    def clean_product(self, product: ExtractedProduct) -> ExtractedProduct:
        """
        Clean product text fields by removing source references.

        Args:
            product: Product to clean (modified in place)

        Returns:
            Cleaned product
        """
        product.title = remove_source_references(product.title, self.source_domain)
        product.description = remove_source_references(product.description, self.source_domain)
        product.seo_title = remove_source_references(product.seo_title, self.source_domain)
        product.seo_description = remove_source_references(product.seo_description, self.source_domain)
        return product

    def product_to_main_row(self, product: ExtractedProduct) -> Dict[str, str]:
        """
        Convert product to main CSV row (includes first image).

        Args:
            product: Product to convert

        Returns:
            Dictionary of field values
        """
        tags_str = ', '.join(product.tags)
        published = 'TRUE' if product.published else 'FALSE'
        requires_shipping = 'TRUE' if product.requires_shipping else 'FALSE'
        continue_selling = 'deny' if product.inventory_policy == 'deny' else 'continue'

        # Determine status based on product type (prescription = draft)
        status = 'Draft' if product.availability == "Само с рецепта" else 'Active'

        return {
            'Title': product.title,
            'URL handle': product.handle,
            'Description': product.description,
            'Vendor': product.brand,
            'Product category': '',
            'Type': product.product_type,
            'Tags': tags_str,
            'Published on online store': published,
            'Status': status,
            'SKU': product.sku,
            'Barcode': product.barcode,
            'Option1 name': '',
            'Option1 value': '',
            'Option1 Linked To': '',
            'Option2 name': '',
            'Option2 value': '',
            'Option2 Linked To': '',
            'Option3 name': '',
            'Option3 value': '',
            'Option3 Linked To': '',
            'Price': product.price,
            'Price EUR': product.price_eur if product.price_eur else '',
            'Compare-at price': product.original_price if product.original_price else '',
            'Cost per item': '',
            'Charge tax': 'TRUE',
            'Tax code': '',
            'Inventory tracker': 'shopify',
            'Inventory quantity': product.inventory_quantity or 11,
            'Continue selling when out of stock': continue_selling,
            'Weight value (grams)': product.weight_grams if product.weight_grams > 0 else '',
            'Weight unit for display': 'g' if product.weight_grams > 0 else '',
            'Requires shipping': requires_shipping,
            'Fulfillment service': 'manual',
            'Product image URL': product.images[0].source_url if product.images else '',
            'Image position': '1' if product.images else '',
            'Image alt text': product.images[0].alt_text if product.images else '',
            'Variant image URL': '',
            'Gift card': 'FALSE',
            'SEO title': product.seo_title,
            'SEO description': product.seo_description,
            'Color (product.metafields.shopify.color-pattern)': '',
            'Форма (product.metafields.custom.application_form)': product.application_form,
            'За кого (product.metafields.custom.target_audience)': product.target_audience,
            'Google Shopping / Google product category': product.google_product_category,
            'Google Shopping / Gender': 'Unisex',
            'Google Shopping / Age group': product.google_age_group,
            'Google Shopping / Manufacturer part number (MPN)': product.google_mpn,
            'Google Shopping / Ad group name': '',
            'Google Shopping / Ads labels': '',
            'Google Shopping / Condition': 'new',
            'Google Shopping / Custom product': 'FALSE',
            'Google Shopping / Custom label 0': product.brand,
            'Google Shopping / Custom label 1': product.category_path[0] if product.category_path else '',
            'Google Shopping / Custom label 2': '',
            'Google Shopping / Custom label 3': '',
            'Google Shopping / Custom label 4': ''
        }

    def image_to_row(self, handle: str, image: ProductImage) -> Dict[str, str]:
        """
        Convert additional image to CSV row.

        Args:
            handle: Product handle (for association)
            image: Image to convert

        Returns:
            Dictionary of field values (mostly empty)
        """
        row = {field: '' for field in self.fieldnames}
        row.update({
            'URL handle': handle,
            'Product image URL': image.source_url,
            'Image position': str(image.position),
            'Image alt text': image.alt_text,
        })
        return row

    def product_to_rows(self, product: ExtractedProduct) -> List[Dict[str, str]]:
        """
        Convert product to all CSV rows (main + additional images).

        Args:
            product: Product to convert

        Returns:
            List of row dictionaries
        """
        rows = [self.product_to_main_row(product)]

        # Add additional image rows
        for img in product.images[1:]:
            rows.append(self.image_to_row(product.handle, img))

        return rows

    def export_single(
        self,
        product: ExtractedProduct,
        output_path: str,
        clean_source_refs: bool = True
    ):
        """
        Export a single product to CSV.

        Args:
            product: Product to export
            output_path: Output CSV file path
            clean_source_refs: Whether to remove source domain references
        """
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        if clean_source_refs:
            self.clean_product(product)

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            writer.writeheader()

            for row in self.product_to_rows(product):
                writer.writerow(row)

    def export_multiple(
        self,
        products: List[ExtractedProduct],
        output_path: str,
        clean_source_refs: bool = True
    ) -> int:
        """
        Export multiple products to CSV.

        Args:
            products: Products to export
            output_path: Output CSV file path
            clean_source_refs: Whether to remove source domain references

        Returns:
            Number of rows written
        """
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        row_count = 0

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            writer.writeheader()

            for product in products:
                if clean_source_refs:
                    self.clean_product(product)

                for row in self.product_to_rows(product):
                    writer.writerow(row)
                    row_count += 1

        return row_count

    def _load_existing_handles(self, csv_path: str) -> Set[str]:
        """Load existing product handles from CSV for dedup."""
        handles = set()
        if not os.path.exists(csv_path):
            return handles
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    handle = row.get('URL handle', '').strip()
                    title = row.get('Title', '').strip()
                    if handle and title:
                        handles.add(handle)
        except Exception as e:
            logger.warning("Could not read CSV for dedup: %s", e)
        return handles

    def append_product(
        self,
        product: ExtractedProduct,
        output_path: str,
        clean_source_refs: bool = True
    ):
        """
        Append a product to existing CSV (creates if doesn't exist).
        Skips products whose handle already exists in the CSV.

        Args:
            product: Product to append
            output_path: Output CSV file path
            clean_source_refs: Whether to remove source domain references
        """
        file_exists = os.path.exists(output_path)

        if clean_source_refs:
            self.clean_product(product)

        # Check for duplicate handle
        if file_exists:
            existing_handles = self._load_existing_handles(output_path)
            if product.handle in existing_handles:
                logger.info("Skipped duplicate: %s", product.handle)
                return

        mode = 'a' if file_exists else 'w'

        with open(output_path, mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)

            if not file_exists:
                writer.writeheader()

            for row in self.product_to_rows(product):
                writer.writerow(row)


