# Data Fields

## SKU Strategy

SKUs are extracted from the vendor site and stored in the Shopify CSV `SKU` field, but they are **not displayed** on the storefront. They exist purely for internal operations:

- **Product mapping** -- align products between the vendor's wholesale catalogue and your Shopify store
- **Promotion sync** -- check which products the vendor has on promotion and mirror pricing
- **Order integration** -- match Shopify orders back to vendor SKUs for procurement
- **Inventory alignment** -- keep your catalogue in sync with what the vendor actually stocks

SKUs are the vendor's internal identifiers. Exposing them publicly on your storefront would reveal the wholesale source. Shopify's `SKU` field is only visible in Admin, not to customers, which makes it the right place for this data.

## Barcode (EAN) Extraction

Barcodes are parsed from the "Допълнителна информация" section of each product page (e.g., `Баркод : 3800232331104`) and exported to the Shopify CSV `Barcode` column. This populates the barcode field on each product variant in Shopify, which is useful for:

- **POS scanning** -- identify products by barcode at point of sale
- **Google Shopping** -- GTIN/EAN improves product matching in Google Merchant Center
- **Inventory systems** -- barcode lookup for stock management

Products without a barcode in their "Допълнителна информация" section will have an empty barcode field (no errors).

## Known Issues

- **Hardcoded inventory quantity** -- currently set to `11` for all products. Should be configurable via CLI argument.
- **Products without images** -- skipped during extraction to avoid Shopify import errors.
- **Image URL encoding** -- special characters in filenames are URL-encoded to prevent import failures.
