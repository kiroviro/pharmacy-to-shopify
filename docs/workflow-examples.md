# Workflow Examples

## Full Extraction

```bash
# 1. Discover all product URLs (~9,800 URLs in ~2 seconds)
python3 scripts/discover_urls.py --site pharmacy.example.com

# 2. Bulk extract all products (with resume support)
python3 scripts/bulk_extract.py --urls data/pharmacy.example.com/raw/urls.txt --resume --continue-on-error

# 3. Clean up tags
python3 scripts/cleanup_tags.py --input data/pharmacy.example.com/raw/products.csv --output data/pharmacy.example.com/processed/products_cleaned.csv

# 4. Export for Shopify (auto-splits files at 14MB)
python3 scripts/export_by_brand.py --all-brands --input data/pharmacy.example.com/processed/products_cleaned.csv --output output/pharmacy.example.com/products.csv

# 5. Import each CSV file to Shopify Admin > Products > Import
```

## Selective Brand Import

```bash
# List all brands and product counts
python3 scripts/export_by_brand.py --list --input data/pharmacy.example.com/raw/products.csv

# Export a single brand for testing
python3 scripts/export_by_brand.py --brands "Nivea" --input data/pharmacy.example.com/raw/products.csv --output output/pharmacy.example.com/nivea.csv

# Export top 5 brands by product count
python3 scripts/export_by_brand.py --top 5 --input data/pharmacy.example.com/raw/products.csv --output output/pharmacy.example.com/top5.csv
```

## Shopify Store Setup

```bash
# Create smart collections from categories
python3 scripts/create_shopify_collections.py --csv data/pharmacy.example.com/processed/products_cleaned.csv --shop YOUR_STORE --token YOUR_TOKEN --skip-brands

# Create navigation menus
python3 scripts/create_shopify_menus.py --shop YOUR_STORE --token YOUR_TOKEN --csv data/pharmacy.example.com/processed/products_cleaned.csv

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

## Programmatic Store Management

Once your products are imported, you can use the included Shopify API integration (`src/shopify/api_client.py`) to manage your store programmatically -- updating products, creating collections, adjusting navigation, customizing theme translations, and more.

Examples of automated store management tasks:
- Creating smart collections and navigation menus from extracted categories
- Configuring sidebar filters with Bulgarian translations (metafield definitions + theme locale)
- Modifying theme locale strings (e.g., removing shipping messages from product pages)
- Enabling theme features by updating product templates (e.g., product comparison)
- Reading and updating theme assets programmatically
- Bulk product deletion via GraphQL Bulk Operations API (`scripts/shopify_delete_products.py`)
- Theme layout changes: moving filter sidebar to right, hiding brand collections from `/collections` page, adding category search to collection list page
- Menu management: updating navigation links, removing unused menu items
- Uploading storefront images via GraphQL staged uploads and wiring into theme templates
