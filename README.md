# Pharmacy Product Catalogue Tool

[![CI](https://github.com/kiroviro/pharmacy-to-shopify/actions/workflows/ci.yml/badge.svg)](https://github.com/kiroviro/pharmacy-to-shopify/actions)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Extracts product catalogues from pharmacy vendor websites, generates Shopify-compatible CSV files, and automates the entire store setup -- collections, navigation, filters, translations, and Google Ads campaigns.

**See it live:** [viapharma.us](https://viapharma.us) -- a fully operational Shopify store with 11,000+ products, built entirely with this pipeline.

---

## Why This Project Exists

Small pharmacies face a structural disadvantage. Their wholesale vendors - sell directly to consumers online with full product catalogues. But they don't share product data with the small pharmacies they supply. There's no API, no data feed, no export.

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

### Technical Approach

This project demonstrates that modern tooling enables rapid development of production-quality software that solves real business problems. The entire pipeline -- from initial extraction logic to the live store deployment -- was built iteratively with a focus on data quality, Shopify compliance, and automation.

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

## Try It Out (No Setup Required)

**Want to see how it works without any setup?** Run the demo script:

```bash
# Clone the repository
git clone https://github.com/kiroviro/pharmacy-to-shopify.git
cd pharmacy-to-shopify

# Run the demo (no dependencies needed)
python3 scripts/demo.py
```

The demo script extracts a sample product page and shows all extracted fields:
- ✅ Product title, brand, SKU, barcode
- ✅ Prices (BGN & EUR), availability
- ✅ Categories, tags, and organization
- ✅ Product descriptions, composition, usage instructions
- ✅ Images with captions
- ✅ SEO metadata and Google Shopping fields
- ✅ Shopify-ready formatting

**No credentials, API keys, or real websites needed!**

---

## Quick Start

### Option 1: Local Setup

```bash
# 1. Clone and setup environment
python3 -m venv venv
source venv/bin/activate
pip install .

# 2. Configure credentials (optional, for Shopify/Google Ads integration)
cp .env.example .env
# Edit .env with your actual credentials

# 3. Discover product URLs from pharmacy site sitemap
python3 scripts/discover_urls.py --site pharmacy.example.com

# 4. Extract a single product (test)
python3 scripts/extract_single.py --url "https://pharmacy.example.com/sample-product" --verbose

# 5. Bulk extract all products
python3 scripts/bulk_extract.py --urls data/pharmacy.example.com/raw/urls.txt --continue-on-error --resume

# 6. Export for Shopify (auto-splits into 14MB files)
python3 scripts/export_by_brand.py --all-brands --input data/pharmacy.example.com/raw/products.csv --output output/pharmacy.example.com/products.csv

# 7. Import to Shopify: Admin > Products > Import > Upload CSV
```

### Ongoing Price Management

After initial import, use the price sync tool to detect and update price changes without a full re-crawl:

```bash
# 1. Check for price differences (sample)
python3 scripts/price_sync.py --sample 100

# 2. Full catalog comparison
python3 scripts/price_sync.py

# 3. Generate Shopify import CSV with only changed prices
python3 scripts/price_sync.py --output output/price_updates.csv

# 4. Import updates: Admin > Products > Import > "Overwrite existing products"
```

This compares live benu.bg prices with your Shopify store and generates a minimal CSV containing only products that need price updates.

### Option 2: Docker Setup

```bash
# 1. Build the Docker image
docker-compose build

# 2. Configure credentials (create .env file)
cp .env.example .env
# Edit .env with your actual credentials

# 3. Run extraction commands
docker-compose run extractor python scripts/discover_urls.py --site pharmacy.example.com
docker-compose run extractor python scripts/bulk_extract.py --urls data/pharmacy.example.com/raw/urls.txt

# 4. Run tests
docker-compose --profile test run test

# 5. Run linter
docker-compose --profile lint run lint
```

---

## Project Structure

```
webcrawler-shopify/
├── scripts/                          # CLI scripts
│   ├── discover_urls.py              # URL discovery from sitemaps
│   ├── extract_single.py            # Single product extraction with validation
│   ├── bulk_extract.py              # Bulk extraction with resume
│   ├── export_by_brand.py           # Selective brand export
│   ├── price_sync.py                 # Price monitoring and sync (benu.bg vs Shopify)
│   ├── chunk_csv.py                  # Split large CSVs for Shopify import
│   ├── cleanup_tags.py              # Tag cleanup and normalization
│   ├── create_shopify_collections.py # Shopify collection creation
│   ├── create_shopify_menus.py      # Shopify navigation menu creation
│   ├── configure_shopify_filters.py # Sidebar filter setup
│   ├── shopify_oauth.py             # Shopify OAuth helper
│   ├── shopify_delete_products.py   # Bulk product deletion
│   ├── google_ads_auth.py           # Google Ads OAuth2 token generator
│   ├── google_ads_auth_flow.py      # OAuth2 flow helper
│   ├── google_ads_pmax.py           # Performance Max campaign creation
│   └── google_ads_create_account.py # Google Ads account creation
│
├── src/
│   ├── models/                      # Data models (ExtractedProduct, ProductImage)
│   ├── extraction/                  # Product extraction (PharmacyExtractor, validator, brand matching)
│   ├── discovery/                   # URL discovery (sitemap-based)
│   ├── shopify/                     # Shopify integration (CSV export, API client, collections, menus)
│   ├── cleanup/                     # Post-processing (tag normalization, brand export)
│   └── common/                      # Shared utilities (config, transliteration, CSV handling)
│
├── config/                          # YAML configuration (categories, brands, SEO, tags)
├── tests/                           # Test suite (pytest)
├── docs/                            # Documentation
├── data/{site}/                     # Per-site data (raw + processed)
└── output/{site}/                   # Export output (CSV files)
```

---

## Requirements

- Python 3.9+
- beautifulsoup4, requests, lxml, pyyaml
- google-ads, google-auth-oauthlib (optional, for Google Ads integration: `pip install ".[google-ads]"`)

All dependencies are declared in `pyproject.toml`.

---

## Development

### Setting Up Development Environment

```bash
# Install development dependencies
pip install ".[dev]"

# Install pre-commit hooks for code quality
pip install pre-commit
pre-commit install

# Run tests
pytest tests/ -v

# Run linter
ruff check .

# Run formatter
ruff format .
```

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality:
- **Ruff**: Fast Python linter and formatter
- **Trailing whitespace**: Removes trailing whitespace
- **End of file fixer**: Ensures files end with newline
- **YAML/JSON validation**: Checks syntax
- **Secret detection**: Prevents committing credentials

Run manually on all files:
```bash
pre-commit run --all-files
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style and formatting
- Writing tests
- Submitting pull requests
- Reporting issues

---

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)** -- module structure, data flow, extraction strategy
- **[Features](docs/features.md)** -- extraction capabilities, Shopify integration, workflow tools
- **[Configuration](docs/configuration.md)** -- adding new vendor sites, category/tag config
- **[Workflow Examples](docs/workflow-examples.md)** -- full extraction, store setup, theme customization
- **[Google Ads](docs/google-ads.md)** -- Performance Max campaign setup and management
- **[Data Fields](docs/data-fields.md)** -- SKU strategy, barcode extraction, known issues

---

## Built With

- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) -- HTML parsing
- [Shopify Admin API](https://shopify.dev/docs/api/admin) -- store management
- [Google Ads API](https://developers.google.com/google-ads/api/docs/start) -- campaign automation
