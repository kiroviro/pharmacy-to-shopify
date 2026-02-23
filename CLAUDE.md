## Commands

```bash
pytest                         # Run all tests
pytest tests/extraction/       # Run extraction tests only
ruff check src/ tests/         # Lint
ruff format src/ tests/        # Format
python scripts/extract_single.py <url>  # Debug single product extraction
python scripts/validate_crawl.py --spot-check 20  # Post-crawl validation with spot-checks
python scripts/price_sync.py --sample 100 --delay 1.0  # Detect price changes (sample)
python scripts/price_sync.py --output output/price_updates.csv  # Export Shopify update CSV
python scripts/push_theme.py --all  # Push all theme files to Shopify
python scripts/backup_theme.py     # Download active theme snapshot
```

## Pipeline (8 stages)

```
discover_urls.py → bulk_extract.py → validate_crawl.py → cleanup_tags.py
→ export_by_brand.py → [Shopify CSV import] → create_shopify_collections.py
→ google_ads_pmax.py
```

## Scripts

Beyond the 8 pipeline scripts above, grouped by function:

| Category | Script | Purpose |
|----------|--------|---------|
| **Price monitoring** | `price_sync.py` | Compare benu.bg prices vs Shopify, export update CSV |
| | `price_monitor.py` | Ongoing price change detection |
| **Shopify admin** | `chunk_csv.py` | Split large CSV for Shopify's import limit |
| | `create_shopify_menus.py` | Build navigation menus via API |
| | `configure_shopify_filters.py` | Set up storefront filters |
| | `shopify_delete_products.py` | Bulk product deletion |
| | `verify_shopify.py` | Post-import checks (images, descriptions, tags) |
| **Navigation/theme** | `setup_navigation.py` | 3-level mega menu setup |
| | `setup_mega_columns.py` | Flat column menu layout |
| | `upload_shop_icons.py` | SVG icons → Shopify Files API |
| | `push_theme.py` | Push theme files (single or `--all`) |
| | `backup_theme.py` | Download active theme snapshot |
| **Google Ads** | `google_ads_auth.py` | OAuth token management |
| | `google_ads_auth_flow.py` | Interactive OAuth flow |
| | `google_ads_create_account.py` | Create Google Ads sub-account |
| **Data cleanup** | `dedup_csv.py` | Deduplicate cleaned CSV by SKU (expiry-aware + true-dupe) |
| **Utilities** | `shopify_oauth.py` | Shopify OAuth helper |
| | `extract_single.py` | Debug single product extraction |
| | `demo.py` | Demo/playground script |
| | `test_barcode_extraction.py` | Barcode extraction testing |
| | `validate_extraction.sh` | Shell-based extraction validation |

## Architecture

Three independent data sources per product page (all from single HTTP fetch):
1. **Vue.js** `<add-to-cart :product="...">` — primary (price always from here)
2. **JSON-LD** `<script type="application/ld+json">` — fallback
3. **HTML DOM** via BeautifulSoup — last resort

Three validation layers run during `bulk_extract.py` (zero extra HTTP):
1. `SpecificationValidator` — per-field format/presence
2. `SourceConsistencyChecker` — cross-check sources 1 & 2 (11 checks)
3. `CrawlQualityTracker` — aggregate stats; PASS/FAIL gate at >5% errors

## Key Files

| File | Purpose |
|------|---------|
| `src/extraction/pharmacy_extractor.py` | Main extractor (~1026 lines) |
| `src/extraction/bulk_extractor.py` | Orchestration + inline validation |
| `src/extraction/consistency_checker.py` | 11 dual-source cross-checks |
| `src/extraction/validator.py` | Field format/presence checks |
| `src/extraction/brand_matcher.py` | Brand name matching against known_brands.yaml |
| `src/validation/crawl_tracker.py` | Aggregate stats, quality gate |
| `src/shopify/csv_exporter.py` | 56-col CSV; single source of truth for column layout |
| `src/shopify/api_client.py` | REST + GraphQL Shopify API wrapper |
| `src/shopify/menus.py` | Hierarchical menu creation via API |
| `src/shopify/collections.py` | Smart collection creation |
| `src/common/constants.py` | EUR/BGN rate (1.95583), field defaults |
| `config/known_brands.yaml` | 450+ brand database |

## Source Packages

| Package | Files | Purpose |
|---------|-------|---------|
| `common` | 7 | Constants, config loading, text/CSV utilities, transliteration |
| `extraction` | 5 | Extractor, bulk orchestration, validation, brand matching |
| `discovery` | 1 | URL discovery from benu.bg sitemap/category pages |
| `models` | 1 | Product data model |
| `shopify` | 4 | CSV export, API client, menus, collections |
| `cleanup` | 2 | Tag normalization, per-brand CSV export |
| `validation` | 1 | Crawl quality tracking and gating |

## Data Paths

```
data/benu.bg/
├── raw/
│   ├── urls.txt                 # Discovered product URLs (from discover_urls.py)
│   └── products.csv             # Raw extraction output (from bulk_extract.py)
├── processed/
│   ├── products_cleaned.csv     # After cleanup_tags.py
│   └── cleanup_report.txt       # Tag cleanup summary
└── corrected_prices.csv         # Manual price corrections
```

## Config

All in `config/`:

| File | Purpose |
|------|---------|
| `known_brands.yaml` | 450+ brand database for matching |
| `categories.yaml` | Product category hierarchy |
| `vendor_defaults.yaml` | Default vendor settings |
| `tag_normalization.yaml` | Tag cleanup rules |
| `promotional_patterns.yaml` | Promo text detection patterns |
| `seo_settings.yaml` | SEO metadata rules |
| `google-ads.yaml` | Google Ads campaign config |

## Testing Patterns

- Extractor tests: `extractor.load_html(html)` then call method — no mocking needed
- `SourceConsistencyChecker`: pass plain dicts + HTML via `_checker()` helper
- `BrandMatcher(brands=set(...))` — pass explicit set to skip YAML loading
- CSV-dependent tests: `@pytest.mark.skipif(not Path("data/benu.bg/raw/products.csv").exists(), ...)`
- `test_extraction_quality` permanently fails on real CSV (2 combo products missing price) — expected

## Gotchas

**CSV column names** (use exactly as defined in `csv_exporter.py`):
- `Product image URL` (not `Image Src`)
- `URL handle` (not `Handle`)
- `Vendor` (not `Brand`)

**Validation warning format:** `"field_name: description"` (underscores, not dots).
`CrawlQualityTracker._extract_field()` regex: `r"^([a-z_A-Z][a-z_A-Z0-9 ]+?):"`

**Known benu.bg data issues:**
- 2 Vichy Dercos combo products: empty price (combo price rendered differently — not a code bug)
- 119 duplicate SKU groups: 106 near-expiry "Годен до" variants + 13 true duplicates

## Shopify Theme

Theme lives in `../../viapharma.us-theme` (sibling directory).
```bash
python scripts/push_theme.py <relative-path-to-file>  # Push single file
python scripts/push_theme.py --all                     # Push all theme files
python scripts/backup_theme.py                         # Download active theme
python scripts/setup_navigation.py                     # 3-level mega menu
python scripts/setup_mega_columns.py                   # Flat column menus
python scripts/upload_shop_icons.py                    # SVG icons → Shopify Files
```
Credentials from `.env` or `.shopify_token.json`. Theme ID: `195131081041`.
**Pushing to `main` branch auto-deploys to live production at viapharma.us.**
