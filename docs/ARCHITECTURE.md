# Architecture

## Overview

A modular product extraction and Shopify migration tool for pharmacy websites. Designed to be extensible for multiple vendor sites.

**Currently supported:** benu.bg (Phoenix Pharma / BENU Bulgaria)

---

## Project Structure

```
webcrawler-shopify/
├── CLI Scripts (thin wrappers)
│   ├── extract_single.py          # Single product extraction with validation
│   ├── discover_urls.py           # URL discovery from sitemaps
│   ├── bulk_extract.py            # Bulk extraction with resume
│   ├── export_by_brand.py         # Brand-based export with splitting
│   ├── cleanup_tags.py            # Tag normalization
│   ├── create_shopify_collections.py
│   ├── create_shopify_menus.py
│   ├── configure_shopify_filters.py
│   ├── shopify_delete_products.py
│   └── shopify_oauth.py
│
├── src/                           # Business logic modules
│   ├── models/                    # Data models
│   ├── extraction/                # Product extraction
│   ├── discovery/                 # URL discovery
│   ├── shopify/                   # Shopify integration
│   ├── cleanup/                   # Post-processing
│   └── common/                    # Shared utilities
│
├── config/                        # YAML configuration
├── data/{site}/                   # Site-specific data
├── output/{site}/                 # Export output
├── reports/{site}/                # Generated reports
└── docs/                          # Documentation
```

---

## Module Responsibilities

### `src/models/`

Pure data classes with no business logic.

| Class | Purpose |
|-------|---------|
| `ExtractedProduct` | Complete product data (title, prices, images, content sections) |
| `ProductImage` | Image with URL, position, alt text |
| `ProductVariant` | SKU, price, inventory (for future variant support) |

**ExtractedProduct key fields:**
- `price` - Price in BGN (лв.)
- `price_eur` - Price in EUR (€) for Bulgaria's Euro transition
- `contraindications` - Product warnings/contraindications
- `tags` - Generated from breadcrumb categories (for Shopify smart collections)
- `product_type` - L1 breadcrumb category (for Shopify "Product Type" filter)
- `application_form` - Pharmaceutical form extracted from title (Таблетки, Капсули, Крем, etc.)
- `target_audience` - Target audience derived from categories + title (Възрастни, Деца, Бебета)

### `src/extraction/`

Core extraction logic for product data.

| Module | Class | Purpose |
|--------|-------|---------|
| `benu_extractor.py` | `BenuExtractor` | Extractor for benu.bg |
| `validator.py` | `SpecificationValidator` | Validates extraction completeness |
| `bulk_extractor.py` | `BulkExtractor` | Batch processing with progress tracking |
| `brand_matcher.py` | `BrandMatcher` | Brand detection from YAML config |
| `utils.py` | - | Helper functions (text cleanup, source reference removal) |
| `parsers/` | Various | Specialized data parsers |

**Helper functions:**
- `get_extractor_for_url(url)` - Returns appropriate extractor class for URL
- `get_site_from_url(url)` - Returns site identifier (e.g., "benu.bg")

**Parsers:**

| Parser | Purpose |
|--------|---------|
| `StructuredDataParser` | JSON-LD schema.org data |
| `GTMDataParser` | Google Tag Manager dl4Objects |
| `HTMLContentParser` | HTML element extraction |
| `LeafletParser` | Pharmaceutical leaflet sections |

### `src/discovery/`

URL discovery from site sitemaps.

| Module | Class | Purpose |
|--------|-------|---------|
| `benu_discoverer.py` | `BenuURLDiscoverer` | Sitemap-based URL discovery for benu.bg |

**Helper functions:**
- `get_discoverer_for_site(site)` - Returns appropriate discoverer class
- `get_supported_sites()` - Returns list of supported sites

### `src/shopify/`

Shopify integration for export and API operations.

| Module | Class | Purpose |
|--------|-------|---------|
| `csv_exporter.py` | `ShopifyCSVExporter` | Export to 56-column Shopify CSV |
| `api_client.py` | `ShopifyAPIClient` | REST/GraphQL client with rate limiting |
| `collections.py` | `ShopifyCollectionCreator` | Create smart collections |
| `menus.py` | `ShopifyMenuCreator` | Create navigation menus |

The API client also supports **theme asset management** -- reading and updating theme files (locale translations, templates, config) via the Asset API (`themes/{id}/assets.json`).

### `src/cleanup/`

Post-processing for data quality.

| Module | Class | Purpose |
|--------|-------|---------|
| `tag_cleaner.py` | `TagCleaner` | Normalize tags, remove duplicates |
| `brand_exporter.py` | `BrandExporter` | Filter by brand, split large files |

### `src/common/`

Shared utilities used across modules.

| Module | Purpose |
|--------|---------|
| `config_loader.py` | Load YAML configuration files |
| `transliteration.py` | Bulgarian to Latin conversion (URL handles) |
| `csv_utils.py` | CSV reading/writing utilities |

---

## Data Flow

```
1. DISCOVERY
   discover_urls.py --site {site} → Discoverer → data/{site}/raw/urls.txt

2. EXTRACTION
   bulk_extract.py --urls data/{site}/raw/urls.txt → BulkExtractor → Extractor (auto-detected)
                                                   → data/{site}/raw/products.csv

3. CLEANUP
   cleanup_tags.py → TagCleaner → data/{site}/processed/products_cleaned.csv

4. EXPORT
   export_by_brand.py → BrandExporter → output/{site}/products_001.csv, ...

5. SHOPIFY
   create_shopify_collections.py → ShopifyCollectionCreator → Shopify API
   create_shopify_menus.py → ShopifyMenuCreator → Shopify API
   configure_shopify_filters.py → ShopifyAPIClient → Metafield definitions + theme locale
```

---

## Configuration

All configuration in `config/` directory (YAML format).

| File | Purpose |
|------|---------|
| `known_brands.yaml` | 450+ brand names for matching |
| `categories.yaml` | L1/L2 category hierarchy |
| `tag_normalization.yaml` | Tag casing rules |
| `promotional_patterns.yaml` | Patterns to filter out |
| `vendor_defaults.yaml` | Default tags per vendor |
| `seo_settings.yaml` | SEO title/description limits, store name, Google Shopping category map |

---

## Multi-Site Architecture

The project supports multiple source sites with isolated data:

```
data/
├── benu.bg/               # Currently supported
│   ├── raw/
│   └── processed/
└── {new-site}/            # Future sites
    ├── raw/
    └── processed/
```

### Adding a New Site

1. **Create site directory**: `data/{site}/raw/`, `data/{site}/processed/`
2. **Create extractor**: `src/extraction/{site}_extractor.py`
3. **Create discoverer**: `src/discovery/{site}_discoverer.py`
4. **Implement interface**:
   ```python
   class NewSiteExtractor:
       def __init__(self, url: str): ...
       def fetch(self) -> None: ...
       def extract(self) -> ExtractedProduct: ...
   ```
5. **Register in `__init__.py`**:
   - Add to `SITE_EXTRACTORS` in `src/extraction/__init__.py`
   - Add to `SITE_DISCOVERERS` in `src/discovery/__init__.py`
6. **Reuse existing modules**: parsers, validators, exporters

### Shared vs Site-Specific

| Shared (reuse) | Site-Specific (create new) |
|----------------|---------------------------|
| `ExtractedProduct` model | Extractor class |
| `ShopifyCSVExporter` | URL discovery patterns |
| `TagCleaner` | Brand list |
| `BrandExporter` | Category mapping |
| Parsers (if applicable) | HTML selectors |

---

## CLI Scripts

All CLI scripts are wrappers that:
- Parse command-line arguments
- Import business logic from `src/`
- Handle input/output paths
- Display progress and results

| Script | Module Used | Purpose |
|--------|-------------|---------|
| `extract_single.py` | `Extractor` (auto-detected) | Single product with validation |
| `discover_urls.py` | `Discoverer` (by --site) | Find all product URLs |
| `bulk_extract.py` | `BulkExtractor` (auto-detected) | Extract products in batch |
| `cleanup_tags.py` | `TagCleaner` | Normalize and clean tags |
| `export_by_brand.py` | `BrandExporter` | Export by brand with splitting |
| `create_shopify_collections.py` | `ShopifyCollectionCreator` | Create collections |
| `create_shopify_menus.py` | `ShopifyMenuCreator` | Create menus |
| `configure_shopify_filters.py` | `ShopifyAPIClient` | Configure sidebar filters + translations |
| `shopify_delete_products.py` | `ShopifyAPIClient` | Bulk delete all products via GraphQL Bulk Operations |
| `shopify_oauth.py` | `ShopifyAPIClient` | OAuth token helper |

---

## Design Principles

1. **Separation of Concerns**: Models, business logic, and CLI are separate
2. **Single Responsibility**: Each parser/module handles one task
3. **Configuration over Code**: Brands, categories, patterns in YAML
4. **Multi-Site Ready**: Data isolated per site, shared modules
5. **Thin CLI Wrappers**: Business logic in `src/`, CLI just orchestrates
6. **Graceful Degradation**: Multiple fallback sources for each field
7. **Generic Extraction**: No hardcoded product-specific keywords

---

## Extraction Strategy

The extractor uses multiple data sources with fallback priority:

| Field | Priority 1 | Priority 2 | Priority 3 | Priority 4 |
|-------|------------|------------|------------|------------|
| Brand | JSON-LD | GTM data | Title prefix | Known brands list |
| Price (EUR) | JSON-LD offers | HTML .product-prices | - | - |
| Price (BGN) | HTML .product-prices | Calculated from EUR | - | - |
| SKU | JSON-LD | - | - | - |
| Categories | Breadcrumb | - | - | - |
| Tags | From categories | - | - | - |
| Product Type | L1 breadcrumb | - | - | - |
| Application Form | Title keyword match | - | - | - |
| Target Audience | Categories + title | - | - | - |
| Images | JSON-LD (rewritten to CDN) | Gallery selectors | - | HEAD validation |
| Content | Accordion tabs | JSON-LD fields | Leaflet sections | HTML panels |

### benu.bg Image URL Resolution

benu.bg serves product images at two URL patterns:

| Pattern | Example |
|---------|---------|
| Raw upload | `https://benu.bg/uploads/images/products/{id}/{file}` |
| CDN cache | `https://benu.bg/media/cache/product_view_default/images/products/{id}/{file}` |

The `uploads/` path returns 404 for ~3.4% of products, while `product_view_default/` works for all products and returns higher-quality images (1.6-3.2x larger files).

**Resolution strategy in `_extract_images()`:**

1. **URL rewrite** -- JSON-LD image paths starting with `uploads/` are rewritten to `media/cache/product_view_default/`
2. **Selective filtering** -- only non-product cache paths are excluded (`product_in_category_list`, `brands_nav_slider`); `product_view_default` images pass through
3. **Normalized deduplication** -- both URL patterns normalize to `/images/products/...` so the same image isn't added twice from JSON-LD and gallery HTML
4. **HEAD validation** -- after collection, each image URL is verified with a HEAD request; non-200 responses trigger a fallback to `product_view_default`

### SKU Handling

SKUs are extracted from JSON-LD structured data and stored in the Shopify CSV `SKU` field. They are **not visible on the storefront** -- Shopify only exposes SKU in Admin.

SKUs serve as the internal key for vendor integration:
- Product mapping between vendor wholesale catalogue and Shopify store
- Promotion synchronization (detect vendor promotions, mirror pricing)
- Order-to-vendor SKU matching for procurement
- Catalogue alignment (detect new/removed products)

The vendor's SKU is also written to `google_mpn` for Google Shopping feeds.

### benu.bg Content Sections

Content is extracted using a generic section marker-based approach:
- Finds section headers in page text
- Extracts content between section boundaries
- No hardcoded product-specific keywords

| Tab Name | Maps To |
|----------|---------|
| Какво представлява | details |
| Активни съставки | composition |
| Противопоказания | contraindications |
| Дозировка и начин на употреба | usage |
| Допълнителна информация | more_info |

### Sidebar Filter Extraction

Four storefront filters are populated during extraction:

| Filter | Shopify Field | Source | Values |
|--------|--------------|--------|--------|
| Марка (Brand) | Vendor | JSON-LD `brand` / title matching | 450+ brands |
| Категория (Product Type) | Type | L1 breadcrumb category | e.g., Лечение и здраве, Козметика... |
| Форма (Application Form) | `custom.application_form` metafield | Title keyword match (27 patterns) | Таблетки, Капсули, Крем, Спрей, etc. |
| За кого (Target Audience) | `custom.target_audience` metafield | Categories + title keywords | Възрастни, Деца, Бебета |

**Application Form extraction** — pattern-matches 27 Bulgarian pharmaceutical form keywords from the product title, ordered specific→general: solid (таблетки, капсули, сашета, пастили, драже), topical (крем, мехлем, гел, маска, серум, лосион, балсам, пяна, тоник, паста, пудра), liquid (спрей, капки, разтвор, сироп, суспензия, олио, масло), care (шампоан), other (пластири, супозитории). Returns empty string if no match.

**Target Audience extraction** — derives audience from categories and title with priority: Бебета (baby keywords: бебе, бебета, бебешк, новородено, кърмач) > Деца (child keywords: дете, деца, детск) > Възрастни (default).

**Filter configuration** (`configure_shopify_filters.py`) creates the metafield definitions via GraphQL and translates built-in filter labels (Availability, Price) to Bulgarian via theme locale patching.

---

## Output Formats

### Shopify CSV (56 columns)

Standard Shopify product import format with 2 custom metafield columns:
- One main row per product
- Additional rows for extra images
- HTML-formatted description
- Tags from breadcrumb categories (for smart collections)
- Vendor from brand (for brand collections)
- Original image URLs (Shopify fetches during import)
- `Форма (product.metafields.custom.application_form)` — pharmaceutical form
- `За кого (product.metafields.custom.target_audience)` — target audience

**Inventory Settings:**
- `Inventory tracker`: `shopify`
- `Inventory quantity`: `11` (hardcoded — see README Known Issues)
- `Continue selling when out of stock`: uses `inventory_policy` from product model (default: `deny`)

### JSON (detailed)

Full extraction data including:
- All extracted fields
- Validation results
- Extraction source metadata

---

## Theme Customization

The API client can read and modify theme assets, enabling programmatic storefront customization:

- **Locale files** (`locales/bg-BG.json`, etc.) -- modify translation strings
- **Theme templates** -- read/update Liquid templates
- **Settings** -- adjust theme configuration

**REST endpoints used:**
- `GET /themes.json` -- list themes (find active theme by `role: "main"`)
- `GET /themes/{id}/assets.json?asset[key]=...` -- read a theme file
- `PUT /themes/{id}/assets.json` -- update a theme file

**Applied customizations:**
- Cleared `products.product.shipping_policy_html` in `bg-BG` locale to remove "Доставката се изчислява при плащане" from product pages
- Added `compare-product` section to `templates/product.json` to enable product comparison (fields: product header, vendor, type, description)
- Created `locales/bg.json` with Bulgarian translations for sidebar filter labels (Наличност, Цена, Марка, Категория) and sorting options
- Moved product filters from right to left sidebar (`component-facets.css`: changed `flex-direction: row-reverse` → `row`)
- Hid brand collections (`brand-*` handle) from `/collections` page and search category dropdown
- Created `sections/brands-list.liquid` + `templates/page.brands.json` for a dedicated `/pages/brands` page
- Assigned `categories-menu` to header drawer button; updated menu links to use `/pages/brands`
- Added client-side category search input to `/collections` page

---

## Future Improvements

1. **Unit Tests**: Add pytest tests for parsers and validators
2. **API Upload**: Direct product upload via Shopify Admin API
3. **Image Upload**: Upload images to Shopify CDN
4. **Scheduling**: Automated periodic extraction
5. **Delta Updates**: Only extract changed products
6. **Vendor Integration**: Automated promotion sync and order mapping using extracted SKUs
