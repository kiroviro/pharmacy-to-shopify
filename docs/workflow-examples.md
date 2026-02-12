# Workflow Examples

## Full Extraction (benu.bg)

```bash
# 1. Discover all product URLs (~9,800 URLs in ~2 seconds)
python3 scripts/discover_urls.py --site benu.bg

# 2. Bulk extract all products (with resume support)
python3 scripts/bulk_extract.py --urls data/benu.bg/raw/urls.txt --resume --continue-on-error

# 3. Clean up tags
python3 scripts/cleanup_tags.py --input data/benu.bg/raw/products.csv --output data/benu.bg/processed/products_cleaned.csv

# 4. Export for Shopify (auto-splits files at 14MB)
python3 scripts/export_by_brand.py --all-brands --input data/benu.bg/processed/products_cleaned.csv --output output/benu.bg/products.csv

# 5. Import each CSV file to Shopify Admin > Products > Import
```

## Selective Brand Import

```bash
# List all brands and product counts
python3 scripts/export_by_brand.py --list --input data/benu.bg/raw/products.csv

# Export a single brand for testing
python3 scripts/export_by_brand.py --brands "Nivea" --input data/benu.bg/raw/products.csv --output output/benu.bg/nivea.csv

# Export top 5 brands by product count
python3 scripts/export_by_brand.py --top 5 --input data/benu.bg/raw/products.csv --output output/benu.bg/top5.csv
```

## Shopify Store Setup

```bash
# Create smart collections from categories
python3 scripts/create_shopify_collections.py --csv data/benu.bg/processed/products_cleaned.csv --shop YOUR_STORE --token YOUR_TOKEN --skip-brands

# Create navigation menus
python3 scripts/create_shopify_menus.py --shop YOUR_STORE --token YOUR_TOKEN --csv data/benu.bg/processed/products_cleaned.csv

# Configure sidebar filters (metafield definitions + Bulgarian translations)
python3 scripts/configure_shopify_filters.py --shop YOUR_STORE --token YOUR_TOKEN

# Delete all products (for reimport scenarios)
python3 scripts/shopify_delete_products.py --shop YOUR_STORE --token YOUR_TOKEN --dry-run   # preview
python3 scripts/shopify_delete_products.py --shop YOUR_STORE --token YOUR_TOKEN              # delete with confirmation
python3 scripts/shopify_delete_products.py --shop YOUR_STORE --token YOUR_TOKEN --yes        # skip prompt
```

The filter configuration script:
1. Creates custom metafield definitions (`Форма`, `За кого`) via GraphQL -- these become filter labels on the storefront
2. Patches the active theme's Bulgarian locale file to translate built-in filter labels (`Availability` -> `Наличност`, `Price` -> `Цена`, `Vendor` -> `Марка`, `Product Type` -> `Категория`)
3. Prints remaining manual steps (enabling filters in Shopify Admin > Navigation)

## Theme Customization

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
- Moved product filters from left sidebar to right sidebar (`component-facets.css`: `flex-direction: row-reverse`, `padding-right` -> `padding-left`)
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
- Shortened long menu item names via GraphQL `menuUpdate`: "Медицински изделия и консумативи" -> "Медицински изделия", "Здравословно хранене чайове и билки" -> "Здравословно хранене"
- Compact collection banner: set `banner_height` to small, reduced padding to 10px, added CSS override `min-height: auto !important` for all banner sizes, reduced product grid top padding from 130px to 20px
- Removed author name from blog posts (`templates/article.json`: removed `author` block)
- Disabled "От нашия блог" featured blog section on article pages (`templates/article.json`)
- Hidden author name on homepage blog section (`templates/index.json`: `show_author: false` in featured-blog section)
- Translated breadcrumb "Home" -> "Начало" across all sections: `main-article.liquid`, `main-blog.liquid`, `main-collection-banner.liquid`, `main-list-collections.liquid`, `main-product.liquid`

## Managing Your Shopify Store with Claude Code

Once your products are imported, you can use [Claude Code](https://docs.anthropic.com/en/docs/claude-code) to manage your Shopify store directly -- updating products, creating collections, adjusting navigation, customizing theme translations, and more. This project includes Shopify API integration (`src/shopify/api_client.py`) that Claude Code can use as a foundation.

Examples of store management tasks performed with Claude Code:
- Creating smart collections and navigation menus from extracted categories
- Configuring sidebar filters with Bulgarian translations (metafield definitions + theme locale)
- Modifying theme locale strings (e.g., removing shipping messages from product pages)
- Enabling theme features by updating product templates (e.g., product comparison)
- Reading and updating theme assets programmatically
- Bulk product deletion via GraphQL Bulk Operations API (`scripts/shopify_delete_products.py`)
- Theme layout changes: moving filter sidebar to right, hiding brand collections from `/collections` page, adding category search to collection list page
- Menu management: updating navigation links, removing unused menu items
- Uploading storefront images via GraphQL staged uploads and wiring into theme templates
