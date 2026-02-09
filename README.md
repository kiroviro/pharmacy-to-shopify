# Pharmacy Product Catalogue Tool

Extracts product catalogues from pharmacy vendor websites, generates Shopify-compatible CSV files, and automates the entire store setup -- collections, navigation, filters, translations, and Google Ads campaigns.

**See it live:** [viapharma.us](https://viapharma.us) -- a fully operational Shopify store with 11,000+ products, built entirely with this pipeline.

---

## Why This Project Exists

Small pharmacies in Bulgaria face a structural disadvantage. Their wholesale vendors -- like BENU (Phoenix Pharma) -- sell directly to consumers online with full product catalogues. But they don't share product data with the small pharmacies they supply. There's no API, no data feed, no export.

The result: a single-owner pharmacy that wants to go digital has to build a catalogue of thousands of products from scratch -- titles, descriptions, images, categories, pricing, pharmaceutical metadata -- all in Bulgarian. That's not feasible without an IT team.

This tool closes that gap. It extracts product data from vendor websites, transforms it into Shopify-ready format, and automates the entire store setup -- collections, navigation, filters, translations, and even Google Ads campaigns. The live result is [viapharma.us](https://viapharma.us), a fully operational Shopify store with 11,000+ products, built entirely with this pipeline.

### More than a web scraper

The gap between "scraping product pages" and "running a live store" is enormous. This project covers that entire gap:

| Stage | Typical scraper | This project |
|-------|----------------|--------------|
| **Data extraction** | Dump raw HTML | Multi-source structured extraction with fallback chains, validation, 95%+ Shopify compliance |
| **Data quality** | Raw output | Tag normalization, brand matching (450+), promotional pattern stripping, category inference |
| **Store setup** | Manual | Automated collections, menus, sidebar filters, Bulgarian translations, theme customization |
| **Marketing** | Nothing | Google Ads Performance Max campaign creation linked to product feed |
| **Localization** | Nothing | Full Bulgarian language support -- filter labels, sort options, theme strings, transliteration |

### On data and ethics

This tool restructures publicly available product information so that a vendor's own wholesale customers can present the same products they already purchase and resell. No proprietary data is accessed -- everything extracted is visible on the public-facing vendor website. The goal is equity: giving small pharmacies the same digital presence their suppliers already have.

### Built with AI

**Built entirely with [Claude Code](https://docs.anthropic.com/en/docs/claude-code)** -- from the first line of code to the live store. This project demonstrates that a small business owner, working with AI tools, can build production-quality software that solves a real business problem -- without a traditional engineering team. Claude Code also serves as an ongoing operational tool for store management: theme customization, filter configuration, collection creation, and more.

---

## How It Works

```
Discover URLs  -->  Extract Products  -->  Export CSV  -->  Import to Shopify
(sitemap)          (structured data)      (56-column)      (Admin > Products)
```

1. **Discover** -- fetch all product URLs from the vendor's sitemap
2. **Extract** -- parse each product page for title, price, description, images, categories
3. **Export** -- generate Shopify-compatible CSV (56-column template with custom metafields)
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
- **Complete product data** -- title, brand, SKU, barcode (EAN), price (BGN + EUR), categories, descriptions, images, application form, target audience
- **Content sections** -- product details, composition, usage instructions, contraindications
- **Brand matching** -- 450+ known pharmacy brands
- **Image URL resolution** -- rewrites vendor `uploads/` paths to CDN `product_view_default/` for higher quality images that work for all products, with HEAD-request validation and automatic fallback
- **High compliance** with Shopify product specification (validated via `src/extraction/validator.py`)

### Shopify Integration
- **56-column CSV format** -- Shopify product import template with 2 custom metafields for storefront filters
- **Original image URLs** -- Shopify fetches and caches images from source during import
- **Sidebar filters** -- Brand (Vendor), Product Type (L1 category), Application Form, and Target Audience as storefront filters with Bulgarian labels
- **Smart collections** -- breadcrumb categories exported as tags for automatic collection rules
- **Dual currency** -- BGN (primary) and EUR prices exported to CSV for Bulgaria's Euro transition
- **Clean data** -- source site references automatically stripped from text fields

### Workflow Tools
- **Bulk extraction** with progress tracking and resume capability
- **Selective brand export** -- import by brand, top-N, or exclude specific brands
- **Tag cleanup** -- normalize casing, remove promotional tags, infer missing categories
- **Collection creation** -- automated Shopify collection setup via Admin API
- **Navigation menus** -- automated Shopify menu creation from category hierarchy
- **Filter configuration** -- create custom metafield definitions and translate theme filter labels to Bulgarian via Admin API
- **Theme customization** -- modify theme locale strings and assets via Admin API (e.g., storefront labels, tax/shipping messages)
- **Filter label translation** -- patched `snippets/facets.liquid` in the Mediva theme to use locale-based translations for sidebar filter labels (Availability → Наличност, Price → Цена, Vendor → Марка, Product Type → Категория)

### Required Shopify Apps

| App | Purpose | Cost |
|-----|---------|------|
| **Shopify Search & Discovery** | Collection sidebar filters + product recommendations | Free |

The Mediva theme (by MUUP, preset of Meka) depends on Search & Discovery for:
- **Collection filters** -- the sidebar with Availability, Price, Vendor, Product Type, and custom metafield filters
- **Product recommendations** -- the "Подобни продукти" (Related Products) section on product pages

Filters must be enabled manually in the app: **Apps → Search & Discovery → Filters tab → Add filter** (Product vendor, Product type, custom.application_form, custom.target_audience).

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
├── configure_shopify_filters.py   # Sidebar filter setup (metafields + translations)
├── shopify_oauth.py               # Shopify OAuth helper
├── shopify_delete_products.py     # Bulk product deletion via GraphQL
├── google_ads_auth.py             # Google Ads OAuth2 refresh token generator
├── google_ads_auth_flow.py        # OAuth2 flow helper
├── google_ads_pmax.py             # Performance Max campaign creation
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
│   │   ├── csv_exporter.py        # 56-column CSV export
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
│   ├── vendor_defaults.yaml       # Default tags for specific vendors
│   ├── seo_settings.yaml          # SEO limits, store name, Google Shopping categories
│   └── google-ads.yaml            # Google Ads API credentials (gitignored)
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
- **`seo_settings.yaml`** -- SEO title/description limits, store name, Google Shopping category mapping

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

# Configure sidebar filters (metafield definitions + Bulgarian translations)
python3 configure_shopify_filters.py --shop YOUR_STORE --token YOUR_TOKEN

# Delete all products (for reimport scenarios)
python3 shopify_delete_products.py --shop YOUR_STORE --token YOUR_TOKEN --dry-run   # preview
python3 shopify_delete_products.py --shop YOUR_STORE --token YOUR_TOKEN              # delete with confirmation
python3 shopify_delete_products.py --shop YOUR_STORE --token YOUR_TOKEN --yes        # skip prompt
```

The filter configuration script:
1. Creates custom metafield definitions (`Форма`, `За кого`) via GraphQL — these become filter labels on the storefront
2. Patches the active theme's Bulgarian locale file to translate built-in filter labels (`Availability` → `Наличност`, `Price` → `Цена`, `Vendor` → `Марка`, `Product Type` → `Категория`)
3. Prints remaining manual steps (enabling filters in Shopify Admin > Navigation)

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
- Enabled product comparison by adding the `compare-product` section to `templates/product.json` with fields: product header, vendor, type, description
- Moved product filters from left sidebar to right sidebar (`component-facets.css`: `flex-direction: row-reverse`, `padding-right` → `padding-left`)
- Hid brand collections from `/collections` page (`main-list-collections.liquid`: `unless collection.handle contains 'brand-'`)
- Hid brand collections from search category dropdown (`header-search.liquid`: same filter)
- Disabled "Всички Категории" search filter button (`show_search_filter: false` in `settings_data.json`)
- Created dedicated brands page template (`sections/brands-list.liquid` + `templates/page.brands.json`) -- fixed `paginate` error on sorted array
- Removed "Марки" from main navigation menu -- brands accessible via sidebar filter and dedicated `/pages/brands` page
- Removed "Всички Категории" drawer button from header (`header-group.json`)
- Added category search input to `/collections` page (`main-list-collections.liquid`)
- Uploaded 4 trust badge SVG icons and wired into collection + product multicolumn sections (Оригинални лекарства, Поддръжка след покупка, Бърза и сигурна доставка, Достъпно здравеопазване)
- Uploaded 3 collection promo/banner images (2 inline promo cards + 1 discount banner)
- Compact header: reduced padding from 22px to 4px, logo from 175px to 100px, created `assets/custom-header-compact.css` with aggressive mobile overrides (85px logo, 3rem search bar, minimal gaps)
- Switched header menu from `main-menu` (flat links) to `categories-menu` (full category tree with 6 categories and 82 subcategories)
- Shortened long menu item names via GraphQL `menuUpdate`: "Медицински изделия и консумативи" → "Медицински изделия", "Здравословно хранене чайове и билки" → "Здравословно хранене"
- Compact collection banner: set `banner_height` to small, reduced padding to 10px, added CSS override `min-height: auto !important` for all banner sizes, reduced product grid top padding from 130px to 20px
- Removed author name from blog posts (`templates/article.json`: removed `author` block)
- Disabled "От нашия блог" featured blog section on article pages (`templates/article.json`)
- Hidden author name on homepage blog section (`templates/index.json`: `show_author: false` in featured-blog section)
- Translated breadcrumb "Home" → "Начало" across all sections: `main-article.liquid`, `main-blog.liquid`, `main-collection-banner.liquid`, `main-list-collections.liquid`, `main-product.liquid`

---

## Managing Your Shopify Store with Claude Code

Once your products are imported, you can use [Claude Code](https://docs.anthropic.com/en/docs/claude-code) to manage your Shopify store directly -- updating products, creating collections, adjusting navigation, customizing theme translations, and more. This project includes Shopify API integration (`src/shopify/api_client.py`) that Claude Code can use as a foundation.

Examples of store management tasks performed with Claude Code:
- Creating smart collections and navigation menus from extracted categories
- Configuring sidebar filters with Bulgarian translations (metafield definitions + theme locale)
- Modifying theme locale strings (e.g., removing shipping messages from product pages)
- Enabling theme features by updating product templates (e.g., product comparison)
- Reading and updating theme assets programmatically
- Bulk product deletion via GraphQL Bulk Operations API (`shopify_delete_products.py`)
- Theme layout changes: moving filter sidebar to right, hiding brand collections from `/collections` page, adding category search to collection list page
- Menu management: updating navigation links, removing unused menu items
- Uploading storefront images via GraphQL staged uploads and wiring into theme templates

---

## Google Ads Integration

Create and manage Google Ads Performance Max campaigns via the API to drive traffic to the Shopify store.

### Setup

1. **Credentials** -- fill in `config/google-ads.yaml` with:
   - Developer Token (Google Ads → Tools & Settings → API Center, requires a Manager/MCC account)
   - OAuth2 Client ID + Secret (Google Cloud Console → APIs & Services → Credentials)
   - Customer ID (Google Ads advertiser account, no dashes)
   - Login Customer ID (Manager/MCC account ID, if applicable)
   - Merchant Center ID (merchants.google.com)

2. **Generate refresh token**:
   ```bash
   python google_ads_auth.py
   ```
   This opens a browser for OAuth2 authorization and prints a refresh token to paste into the config.

3. **Create a Performance Max campaign**:
   ```bash
   # Validate config without creating anything
   python google_ads_pmax.py --dry-run

   # Create campaign with custom daily budget
   python google_ads_pmax.py --budget 5.00
   ```

### What the Campaign Script Creates

- **Campaign budget** -- daily budget (default €20, configurable via `--budget`)
- **Performance Max campaign** -- linked to Merchant Center product feed, using Maximize Conversion Value bidding
- **Asset group** -- with `viapharma.us` as the landing page
- **Text assets** -- 5 headlines, 2 long headlines, 4 descriptions in Bulgarian, business name
- **Listing group filter** -- includes all products from the Merchant Center feed
- **Target market** -- Bulgaria (Bulgarian language ads)

The campaign is created in **PAUSED** state. Review it in the Google Ads UI, add image assets (logo, marketing images), and enable when ready.

### Google Ads Policy Note

Google has strict policies on pharmaceutical advertising. Vitamins, supplements, and cosmetics are generally allowed. Prescription drugs and certain OTC medicines may require LegitScript certification.

---

## Requirements

- Python 3.9+
- beautifulsoup4, requests, lxml, pyyaml
- google-ads, google-auth-oauthlib (for Google Ads integration)

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

See also `TODO.md` for AI-generated storefront image tasks.

---

## Built With

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) -- AI-powered development
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) -- HTML parsing
- [Shopify Admin API](https://shopify.dev/docs/api/admin) -- store management
