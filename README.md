# Pharmacy Product Catalogue Tool

Extracts product catalogues from pharmacy vendor websites and generates Shopify-compatible CSV files for import.

**See it live:** [viapharma.us](https://viapharma.us) -- a Shopify store built entirely from data extracted by this tool.

---

## Why This Project Exists

Small pharmacies are under pressure to go digital. They need online product catalogues, but:

- They have **no IT support** -- most are single-owner businesses
- Their wholesale vendors sell products online themselves, but **don't share product data** with the small pharmacies they supply
- There is **no API, no data export, no catalogue feed** available to these small business customers
- Building a product catalogue from scratch -- with descriptions, images, categories, and pricing for thousands of products -- is not feasible manually

This tool bridges that gap. It extracts product data from vendor websites and transforms it into Shopify-ready CSV files that a small pharmacy can import directly into their online store.

This is not about copyright infringement. It is about enabling a vendor's own customers to access product information they already sell through that vendor. The data is publicly available on the vendor's website -- this tool simply restructures it for a different use case.

**Built entirely with [Claude Code](https://docs.anthropic.com/en/docs/claude-code)** -- AI as a bridge builder for small businesses without developers.

---

## How It Works

```
Discover URLs  -->  Extract Products  -->  Export CSV  -->  Import to Shopify
(sitemap)          (structured data)      (53-column)      (Admin > Products)
```

1. **Discover** -- fetch all product URLs from the vendor's sitemap
2. **Extract** -- parse each product page for title, price, description, images, categories
3. **Export** -- generate Shopify-compatible CSV (official 53-column template)
4. **Import** -- upload CSV to Shopify Admin for direct product creation

---

## Quick Start

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 1. Discover product URLs from benu.bg sitemap
python3 discover_urls.py --site benu.bg

# 2. Extract a single product (test)
python3 extract_single.py --url "https://benu.bg/ferveks-za-v-zrastni-saseta-pri-prostuda-i-grip-h12" --verbose

# 3. Bulk extract all products
python3 bulk_extract.py --urls data/benu.bg/raw/urls.txt --continue-on-error --resume

# 4. Export for Shopify (auto-splits into 14MB files)
python3 export_by_brand.py --all-brands --input data/benu.bg/raw/products.csv --output output/benu.bg/products.csv

# 5. Import to Shopify: Admin > Products > Import > Upload CSV
```

---

## Features

### Extraction
- **Structured data parsing** -- JSON-LD, HTML content, breadcrumb navigation
- **Complete product data** -- title, brand, SKU, barcode (EAN), price (BGN + EUR), categories, descriptions, images
- **Content sections** -- product details, composition, usage instructions, contraindications
- **Brand matching** -- 450+ known pharmacy brands
- **Image URL resolution** -- rewrites vendor `uploads/` paths to CDN `product_view_default/` for higher quality images that work for all products, with HEAD-request validation and automatic fallback
- **95%+ compliance** with Shopify product specification

### Shopify Integration
- **Official CSV format** -- 53-column Shopify product import template
- **Original image URLs** -- Shopify fetches and caches images from source during import
- **Smart collections** -- breadcrumb categories exported as tags for automatic collection rules
- **Dual currency** -- BGN and EUR prices for Bulgaria's Euro transition
- **Clean data** -- source site references automatically stripped from text fields

### Workflow Tools
- **Bulk extraction** with progress tracking and resume capability
- **Selective brand export** -- import by brand, top-N, or exclude specific brands
- **Tag cleanup** -- normalize casing, remove promotional tags, infer missing categories
- **Collection creation** -- automated Shopify collection setup via Admin API
- **Navigation menus** -- automated Shopify menu creation from category hierarchy
- **Theme customization** -- modify theme locale strings and assets via Admin API (e.g., storefront labels, tax/shipping messages)

---

## Project Structure

```
webcrawler-shopify/
├── extract_single.py              # Single product extraction with validation
├── discover_urls.py               # URL discovery from sitemaps
├── bulk_extract.py                # Bulk extraction with resume
├── export_by_brand.py             # Selective brand export
├── cleanup_tags.py                # Tag cleanup and normalization
├── create_shopify_collections.py  # Shopify collection creation
├── create_shopify_menus.py        # Shopify navigation menu creation
├── shopify_oauth.py               # Shopify OAuth helper
│
├── src/
│   ├── models/                    # Data models
│   │   └── product.py             # ExtractedProduct, ProductImage, ProductVariant
│   │
│   ├── extraction/                # Product extraction
│   │   ├── benu_extractor.py      # BenuExtractor for benu.bg
│   │   ├── validator.py           # Specification compliance validator
│   │   ├── bulk_extractor.py      # Batch processing with progress tracking
│   │   ├── brand_matcher.py       # Brand name matching (450+ brands)
│   │   ├── utils.py               # Text cleaning helpers
│   │   └── parsers/               # Specialized data parsers
│   │
│   ├── discovery/                 # URL discovery
│   │   └── benu_discoverer.py     # Sitemap-based URL discovery
│   │
│   ├── shopify/                   # Shopify integration
│   │   ├── csv_exporter.py        # 53-column CSV export
│   │   ├── api_client.py          # Shopify Admin API client
│   │   ├── collections.py         # Smart collection creation
│   │   └── menus.py               # Navigation menu creation
│   │
│   ├── cleanup/                   # Post-processing
│   │   ├── tag_cleaner.py         # Tag normalization and cleanup
│   │   └── brand_exporter.py      # Selective brand export
│   │
│   └── common/                    # Shared utilities
│       ├── config_loader.py       # YAML config loading
│       ├── transliteration.py     # Bulgarian-to-Latin transliteration
│       └── csv_utils.py           # CSV field size handling
│
├── config/                        # YAML configuration
│   ├── categories.yaml            # L1/L2 category hierarchy
│   ├── known_brands.yaml          # Known brand names
│   ├── tag_normalization.yaml     # Tag casing rules
│   ├── promotional_patterns.yaml  # Patterns to strip from tags
│   └── vendor_defaults.yaml       # Default tags for specific vendors
│
├── data/{site}/                   # Per-site data (raw + processed)
├── output/{site}/                 # Export output (CSV files)
├── reports/{site}/                # Generated reports
└── docs/                          # Architecture documentation
```

---

## Configuration

### Adding Support for a New Vendor Site

The tool is designed to support multiple vendor sites. To add a new site:

1. **Create an extractor** in `src/extraction/` (e.g., `newsite_extractor.py`)
   - Implement `fetch()` and `extract()` methods that return `ExtractedProduct`
   - Use JSON-LD, HTML parsing, or other strategies appropriate for the site

2. **Create a discoverer** in `src/discovery/` (e.g., `newsite_discoverer.py`)
   - Implement `discover_all_products()` to find product URLs (sitemap, crawling, etc.)

3. **Register in `__init__.py`** files:
   - Add to `SITE_EXTRACTORS` in `src/extraction/__init__.py`
   - Add to `SITE_DISCOVERERS` in `src/discovery/__init__.py`

4. **Create data directories**: `data/{new-site}/raw/` and `data/{new-site}/processed/`

The CLI scripts auto-detect the site from URLs, so no changes are needed there.

### Category and Tag Configuration

All category and tag settings are in YAML files under `config/`:

- **`categories.yaml`** -- L1/L2 category hierarchy (83 subcategories for benu.bg)
- **`tag_normalization.yaml`** -- canonical brand name casing (e.g., "AboPharma")
- **`promotional_patterns.yaml`** -- patterns to strip from tags (e.g., "Black Friday")
- **`vendor_defaults.yaml`** -- default tags for specific vendors

After editing config files, re-run `cleanup_tags.py` to apply changes.

---

## Workflow Examples

### Full Extraction (benu.bg)

```bash
# 1. Discover all product URLs (~9,800 URLs in ~2 seconds)
python3 discover_urls.py --site benu.bg

# 2. Bulk extract all products (with resume support)
python3 bulk_extract.py --urls data/benu.bg/raw/urls.txt --resume --continue-on-error

# 3. Clean up tags
python3 cleanup_tags.py --input data/benu.bg/raw/products.csv --output data/benu.bg/processed/products_cleaned.csv

# 4. Export for Shopify (auto-splits files at 14MB)
python3 export_by_brand.py --all-brands --input data/benu.bg/processed/products_cleaned.csv --output output/benu.bg/products.csv

# 5. Import each CSV file to Shopify Admin > Products > Import
```

### Selective Brand Import

```bash
# List all brands and product counts
python3 export_by_brand.py --list --input data/benu.bg/raw/products.csv

# Export a single brand for testing
python3 export_by_brand.py --brands "Nivea" --input data/benu.bg/raw/products.csv --output output/benu.bg/nivea.csv

# Export top 5 brands by product count
python3 export_by_brand.py --top 5 --input data/benu.bg/raw/products.csv --output output/benu.bg/top5.csv
```

### Shopify Store Setup

```bash
# Create smart collections from categories
python3 create_shopify_collections.py --csv data/benu.bg/processed/products_cleaned.csv --shop YOUR_STORE --token YOUR_TOKEN --skip-brands

# Create navigation menus
python3 create_shopify_menus.py --shop YOUR_STORE --token YOUR_TOKEN --csv data/benu.bg/processed/products_cleaned.csv
```

### Theme Customization

The Shopify API client supports reading and updating theme assets, including locale files. This is useful for customizing storefront text without touching the Shopify Admin UI.

```python
from src.shopify.api_client import ShopifyAPIClient
import json

client = ShopifyAPIClient(shop="YOUR_STORE", access_token="YOUR_TOKEN")

# List themes and find the active one (role: "main")
themes = client.rest_request("GET", "themes.json")

# Read a locale file
asset = client.rest_request("GET", "themes/THEME_ID/assets.json?asset[key]=locales/bg-BG.json")
data = json.loads(asset["asset"]["value"])

# Modify a translation string
data["products"]["product"]["shipping_policy_html"] = ""

# Upload the modified locale file
client.rest_request("PUT", "themes/THEME_ID/assets.json", data={
    "asset": {"key": "locales/bg-BG.json", "value": json.dumps(data, ensure_ascii=False)}
})
```

**Changes made via this workflow:**
- Removed "Доставката се изчислява при плащане" from product pages -- storefront now shows only "С включени данъци."

---

## Managing Your Shopify Store with Claude Code

Once your products are imported, you can use [Claude Code](https://docs.anthropic.com/en/docs/claude-code) to manage your Shopify store directly -- updating products, creating collections, adjusting navigation, customizing theme translations, and more. This project includes Shopify API integration (`src/shopify/api_client.py`) that Claude Code can use as a foundation.

Examples of store management tasks performed with Claude Code:
- Creating smart collections and navigation menus from extracted categories
- Modifying theme locale strings (e.g., removing shipping messages from product pages)
- Reading and updating theme assets programmatically

---

## Requirements

- Python 3.9+
- beautifulsoup4, requests, lxml, pyyaml

All dependencies are in `requirements.txt`.

---

## SKU Strategy

SKUs are extracted from the vendor site and stored in the Shopify CSV `SKU` field, but they are **not displayed** on the storefront. They exist purely for internal operations:

- **Product mapping** -- align products between the vendor's wholesale catalogue and your Shopify store
- **Promotion sync** -- check which products the vendor has on promotion and mirror pricing
- **Order integration** -- match Shopify orders back to vendor SKUs for procurement
- **Inventory alignment** -- keep your catalogue in sync with what the vendor actually stocks

SKUs are the vendor's internal identifiers. Exposing them publicly on your storefront would reveal the wholesale source. Shopify's `SKU` field is only visible in Admin, not to customers, which makes it the right place for this data.

### Barcode (EAN) Extraction

Barcodes are parsed from the "Допълнителна информация" section of each product page (e.g., `Баркод : 3800232331104`) and exported to the Shopify CSV `Barcode` column. This populates the barcode field on each product variant in Shopify, which is useful for:

- **POS scanning** -- identify products by barcode at point of sale
- **Google Shopping** -- GTIN/EAN improves product matching in Google Merchant Center
- **Inventory systems** -- barcode lookup for stock management

Products without a barcode in their "Допълнителна информация" section will have an empty barcode field (no errors).

---

## Known Issues / TODO

- **Hardcoded inventory quantity** -- currently set to `11` for all products. Should be configurable via CLI argument.
- **Products without images** -- skipped during extraction to avoid Shopify import errors.
- **Image URL encoding** -- special characters in filenames are URL-encoded to prevent import failures.

---

## Built With

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) -- AI-powered development
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) -- HTML parsing
- [Shopify Admin API](https://shopify.dev/docs/api/admin) -- store management
