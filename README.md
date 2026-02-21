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

The pipeline covers eight stages — from raw sitemap URLs to a live store with running ad campaigns:

```
 1. DISCOVER    2. EXTRACT     3. VALIDATE    4. CLEANUP
 ──────────     ──────────     ──────────     ──────────
 Sitemap    →   Per-product →  Post-crawl  →  Tag
 URLs           structured     CSV checks     normalization
                data + inline                 + L1 inference
                validation

 5. EXPORT      6. IMPORT      7. STORE SETUP  8. GOOGLE ADS
 ──────────     ──────────     ────────────    ──────────────
 Split CSV  →   Shopify    →   Collections, →  Performance Max
 files for      Admin          menus, filters  campaign linked
 import         Products       & translations  to product feed
```

**What each stage delivers:**

| Stage | What it does | Why it matters |
|-------|-------------|----------------|
| **1. Discover** | Fetches all product URLs from vendor sitemap | Finds 9,800 products in ~2 seconds, with zero manual work |
| **2. Extract** | Parses title, price (Vue.js), description, images, categories, brand, SKU, barcode, metafields | Multi-source extraction with fallback chains; 3 layers of inline validation catch issues before they reach Shopify |
| **3. Validate** | Post-crawl CSV checks: duplicates, coverage, image URLs, optional live spot-check | Catches data problems before import; exit code usable in CI |
| **4. Cleanup** | Normalises tags, infers missing L1 categories, strips promotional tags | Ensures smart collections match correctly; prevents duplicate/broken tags in Shopify |
| **5. Export** | Generates 56-column Shopify CSV split into ≤14MB files | Shopify's import limit is 15MB — auto-splitting handles this; files import in order |
| **6. Import** | Shopify Admin CSV import | 9,800 products with images, prices, metafields, tags, SEO data — one upload per file |
| **7. Store Setup** | Automated smart collections, navigation menus, sidebar filters (metafield definitions + Bulgarian translations), theme customization | A manually configured store would take weeks; this runs in minutes |
| **8. Google Ads** | OAuth2 → account creation → Performance Max campaign linked to Shopify product feed | Drives traffic from day one; campaign targets all products automatically via the product feed |

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

### Complete Workflow Overview

Eight stages from sitemap to live store with running ad campaigns:

```
 1. DISCOVER     2. EXTRACT       3. VALIDATE      4. CLEANUP
 ─────────────   ─────────────    ─────────────    ─────────────
 Fetch all       Per-product      Post-crawl CSV   Normalise tags,
 URLs from   →   structured   →   checks:      →   infer missing
 sitemap         data + 3-layer   duplicates,      L1 categories,
 (~9,800 URLs)   inline valid.    coverage,        strip promo tags
                 (zero extra      image URLs,
                 HTTP)            spot-check

 5. EXPORT       6. IMPORT        7. STORE SETUP   8. GOOGLE ADS
 ─────────────   ─────────────    ─────────────    ─────────────
 Generate    →   Shopify      →   Smart        →   Performance Max
 56-column CSV   Admin >          collections,     campaign linked
 split into      Products >       menus, sidebar   to Shopify
 ≤14MB files     Import           filters,         product feed
                                  translations
```

**File locations:**
- **Source data:** `data/benu.bg/raw/products.csv` (output from bulk extraction)
- **Processed:** `data/benu.bg/processed/products_cleaned.csv` (after tag cleanup)
- **Shopify import:** `output/benu.bg/products_*.csv` (split files ready for import)

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
python3 scripts/discover_urls.py --site benu.bg
# Output: data/benu.bg/raw/urls.txt (~9,800 URLs in ~2 seconds)

# 4. Extract a single product (test)
python3 scripts/extract_single.py --url "https://benu.bg/sample-product" --verbose

# 5. Bulk extract all products (~4.8 hours for ~9,800 products)
# Option A: Extract + Auto-export to Shopify (recommended)
python3 scripts/bulk_extract.py \
  --urls data/benu.bg/raw/urls.txt \
  --output data/benu.bg/raw/products.csv \
  --delay 1.0 \
  --export-shopify

# Option B: Extract only (manual export later)
python3 scripts/bulk_extract.py \
  --urls data/benu.bg/raw/urls.txt \
  --output data/benu.bg/raw/products.csv \
  --delay 1.0

# Output summary:
#   ✅ Products extracted: ~9,800
#   ✅ Inline validation:  SpecificationValidator + SourceConsistencyChecker
#   ✅ Quality gate:       PASS/FAIL printed at end (>5% errors = exit 1)
#   ✅ Price accuracy:     Fresh from Vue.js component (matches live site)
#   ✅ File size:          ~30 MB

# 6. Post-crawl validation (catches data issues before import)
python3 scripts/validate_crawl.py --csv data/benu.bg/raw/products.csv
# Optional: add --spot-check 100 to also verify 100 products against the live site

# 7. Clean up tags (normalise, infer missing L1 categories, strip promotional tags)
python3 scripts/cleanup_tags.py \
  --input data/benu.bg/raw/products.csv \
  --output data/benu.bg/processed/products_cleaned.csv

# 8. Export for Shopify (auto-splits into ≤14MB files)
python3 scripts/export_by_brand.py \
  --all-brands \
  --input data/benu.bg/processed/products_cleaned.csv \
  --output output/benu.bg/products.csv

# Output: products_001.csv, products_002.csv, products_003.csv
# Located at: output/benu.bg/products_*.csv  (~9,800 products total)

# 9. Import to Shopify
#    IMPORTANT: Import files in order — Shopify processes one at a time
#    Wait for each Shopify confirmation email before uploading the next file.
#
#    For each file (001, 002, 003):
#      - Go to: Shopify Admin > Products > Import
#      - Upload the file
#      - Settings:
#        ✅ "Overwrite existing products that have the same handle"
#        ✅ "Publish new products to online store"
#      - Click "Import products" and wait for Shopify's confirmation email

# 10. Post-import verification (optional but recommended)
python3 scripts/verify_shopify.py \
  --csv data/benu.bg/processed/products_cleaned.csv \
  --shop YOUR_STORE \
  --sample 100
# Checks: product exists, title matches, vendor matches, price within 5%

# 11. Store setup (smart collections, navigation, sidebar filters, translations)
python3 scripts/create_shopify_collections.py \
  --csv data/benu.bg/processed/products_cleaned.csv \
  --shop YOUR_STORE --token YOUR_TOKEN --skip-brands
python3 scripts/create_shopify_menus.py \
  --shop YOUR_STORE --token YOUR_TOKEN \
  --csv data/benu.bg/processed/products_cleaned.csv
python3 scripts/configure_shopify_filters.py \
  --shop YOUR_STORE --token YOUR_TOKEN
# Creates: category collections + navigation menus + Bulgarian-labelled sidebar
# filters (Форма, За кого, Наличност, Цена, Марка, Категория)

# 12. Google Ads — Performance Max campaign linked to Shopify product feed
python3 scripts/google_ads_auth.py          # OAuth2 token (one-time)
python3 scripts/google_ads_create_account.py  # create/link MCC account
python3 scripts/google_ads_pmax.py          # Performance Max campaign
# Result: campaign auto-targets all products via the Shopify product feed
```

Three layers of validation run automatically during extraction — field checks (`SpecificationValidator`), source cross-checks (`SourceConsistencyChecker`), and aggregate tracking (`CrawlQualityTracker`). The final quality report is printed at the end of `bulk_extract.py`. See [Testing and Validation](docs/TESTING_AND_VALIDATION.md) for details.

**Expected data completeness:**
- Title: 100%
- Price: 100% ✅ **Fresh prices from Vue.js component**
- Compare-at price: ~15–25% (products on promotion only)
- SKU: 100%
- Barcode: ~88% (valid GTIN only — EAN-13, UPC-A, EAN-8, GTIN-14)
- Description: 100%
- Vendor/Brand: 100%

**Price accuracy (Feb 2026 update):**

Prices are now extracted from Vue.js component data instead of JSON-LD:
- ✅ Always current (matches what customers see)
- ✅ Distinguishes regular vs promotional pricing
- ✅ Includes original price for products on sale
- ✅ Supports running your own promotions in Shopify

See `CHANGELOG.md` for implementation details.

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

### Automated Price Monitoring (Cron Job)

For hands-off price synchronization, set up a daily cron job to automatically monitor and sync prices:

**Option 1: Price Monitor (Full Automation)**

```bash
# Setup environment variables
export SHOPIFY_SHOP="your-store-name"
export SHOPIFY_ACCESS_TOKEN="your-admin-api-token"

# Add to crontab (run daily at 3 AM)
crontab -e

# Add this line:
0 3 * * * cd /Users/kiril/IdeaProjects/pharmacy-to-shopify && python3 scripts/price_monitor.py --auto-sync >> logs/price_sync.log 2>&1
```

**What it does:**
- Fetches live prices from benu.bg
- Compares with current Shopify prices
- Automatically updates prices via Shopify Admin API
- Logs all changes to `logs/price_sync.log`

**Option 2: Price Sync (Manual Review)**

For more control, generate a daily report without auto-updating:

```bash
# Add to crontab (generate report daily at 3 AM)
0 3 * * * cd /Users/kiril/IdeaProjects/pharmacy-to-shopify && python3 scripts/price_sync.py --output output/price_updates_$(date +\%Y\%m\%d).csv >> logs/price_check.log 2>&1
```

Then manually review and import the CSV when ready.

**Available scripts:**

| Script | Purpose | Use Case |
|--------|---------|----------|
| `price_monitor.py` | Auto-sync via API | Hands-off automation |
| `price_sync.py` | Generate CSV report | Manual review workflow |

**Setup instructions:**

1. Create logs directory:
   ```bash
   mkdir -p logs
   ```

2. Set environment variables in `.env`:
   ```bash
   SHOPIFY_SHOP=your-store-name
   SHOPIFY_ACCESS_TOKEN=shpat_xxxxx
   ```

3. Test the script manually first:
   ```bash
   # Test with sample (no changes made)
   python3 scripts/price_monitor.py --sample 100 --report-only

   # Test full sync (review mode - asks for confirmation)
   python3 scripts/price_monitor.py --review
   ```

4. Add to crontab once verified

**Monitoring recommendations:**
- **Daily:** Check for price changes (catches most updates)
- **Weekly:** Review price sync logs for anomalies
- **Monthly:** Full re-extraction to capture new products

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
│   ├── validate_crawl.py            # Post-crawl CSV validation + optional spot-check
│   ├── verify_shopify.py            # Post-import Shopify product verification
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
│   ├── extraction/                  # Product extraction (PharmacyExtractor, validator, brand matching, consistency)
│   ├── validation/                  # Aggregate quality tracking (CrawlQualityTracker)
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
