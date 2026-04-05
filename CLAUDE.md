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

### Fresh crawl (full pipeline stage 1–2)
```bash
python scripts/discover_urls.py --output data/benu.bg/raw/urls.txt
python scripts/bulk_extract.py --urls data/benu.bg/raw/urls.txt --delay 1.0

# With proxy rotation and retries (recommended for large crawls):
python scripts/discover_urls.py --proxies proxies.txt
python scripts/bulk_extract.py --urls data/benu.bg/raw/urls.txt --delay 1.0 --proxies proxies.txt --retries 3

# Retry failed URLs after a crawl (two-pass: no proxy first, then with proxies):
python scripts/bulk_extract.py --urls output/failed_urls.txt --output data/benu.bg/raw/products_retry1.csv --output-dir output/retry1 --delay 1.5 --retries 3
python scripts/bulk_extract.py --urls output/retry1/failed_urls.txt --output data/benu.bg/raw/products_retry2.csv --output-dir output/retry2 --delay 2.0 --retries 3 --proxies proxies.txt

# Merge retry results into products.csv (run after retries complete):
python3 -c "
import pandas as pd
from pathlib import Path
main = pd.read_csv('data/benu.bg/raw/products.csv')
orig_handles = set(main[main['Title'].fillna('').str.strip() != '']['URL handle'].dropna())
frames = [main]
for path in ['data/benu.bg/raw/products_retry1.csv', 'data/benu.bg/raw/products_retry2.csv']:
    p = Path(path)
    if p.exists() and p.stat().st_size > 200:
        df = pd.read_csv(path)
        frames.append(df[~df['URL handle'].isin(orig_handles)])
        orig_handles |= set(df['URL handle'].dropna())
merged = pd.concat(frames)
merged.to_csv('data/benu.bg/raw/products.csv', index=False)
print(f'Final: {(merged[\"Title\"].fillna(\"\").str.strip() != \"\").sum()} products')
"

# Split for Shopify import (outputs to output/YYYY.Mon.DD/export_NNN.csv):
python scripts/chunk_csv.py data/benu.bg/raw/products.csv
```

`proxies.txt` — one proxy URL per line (`http://user:pass@host:port`), blank lines and `#` comments ignored. File is gitignored (never committed). See `proxies.txt` in project root for Oxylabs credentials.

## Pipeline (8 stages)

```
discover_urls.py → bulk_extract.py → validate_crawl.py → cleanup_tags.py
→ export_by_brand.py → [Shopify CSV import] → create_shopify_collections.py
→ google_ads_pmax.py
```

**Scope:** This project owns the **initial product load** (crawl benu.bg → import to Shopify)
and discount visibility tooling. **Ongoing pricing and repricing** is managed by `viapharma-pricing`
(Phoenix B2B wholesale prices, promos, cosmetics, new product import). After any viapharma-pricing
repricing run, execute `scripts/tag_discounted_products.py` here to sync the "Намаление" tag.

## Scripts

Beyond the 8 pipeline scripts above, grouped by function:

| Category | Script | Purpose |
|----------|--------|---------|
| **Price monitoring** | `price_sync.py` | Compare benu.bg prices vs Shopify, export update CSV |
| | `price_monitor.py` | Ongoing price change detection |
| **Discount visibility** | `tag_discounted_products.py` | Tag products where compare_at > price with "Намаление"; run after every viapharma-pricing repricing |
| | `create_sale_collection.py` | Create "Намаления" smart collection (tag-based rule) |
| **Shopify admin** | `chunk_csv.py` | Split large CSV into Shopify chunks; outputs to `output/YYYY.Mon.DD/export_NNN.csv` |
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
| | `monitor_dsa_campaign.py` | Daily DSA campaign monitor (Google Ads orders vs organic, ROAS) |
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
3. `CrawlQualityTracker` — aggregate stats; PASS/FAIL gate at >5% errors (includes network errors: HTTPError, ProxyError)

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
| `src/shopify/api_client.py` | REST + GraphQL Shopify API wrapper; `paginate_rest()` for since_id pagination |
| `src/shopify/menus.py` | Hierarchical menu creation via API |
| `src/shopify/collections.py` | Smart collection creation; `create_sale_collection()` uses tag rule |
| `src/shopify/tagger.py` | `DiscountTagger` — tags products where compare_at > price; batched GraphQL |
| `src/extraction/fetcher.py` | HTTP fetcher; delegates to `session_factory.build_headers()` per request |
| `src/extraction/classifier.py` | Pure classification functions extracted from parser (form, audience, category, age group) |
| `src/common/constants.py` | EUR/BGN rate (1.95583), `USER_AGENTS` (10 rotating UAs), `BROWSER_HEADERS` (realistic browser headers) |
| `src/common/session_factory.py` | Shared HTTP session creation with anti-ban headers; `build_headers()`, `create_session()`, `rotate_headers()` |
| `src/common/cli.py` | Shared script boilerplate: `base_parser()`, `init_logging()`, `shopify_client_from_env()` |
| `src/common/google_ads_config.py` | Google Ads YAML config loading and client creation (lazy import of google-ads package) |
| `config/known_brands.yaml` | 450+ brand database |

## Source Packages

| Package | Files | Purpose |
|---------|-------|---------|
| `common` | 10 | Constants, config loading, text/CSV utilities, transliteration, session factory, CLI helpers, Google Ads config |
| `extraction` | 6 | Extractor, bulk orchestration, validation, brand matching, classifier |
| `discovery` | 1 | URL discovery from benu.bg sitemap/category pages |
| `models` | 1 | Product data model |
| `shopify` | 5 | CSV export, API client, menus, collections, discount tagger |
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

**Anti-ban crawl (2026-03-07):** `PharmacyFetcher` rotates from 10 real browser UAs and sends full `BROWSER_HEADERS` (Sec-Fetch-*, Accept-Encoding, etc.) per request. `BulkExtractor` sleeps `random.uniform(delay, delay*3)` between requests. `price_monitor.py` and `price_sync.py` use the same rotation. Optional proxy rotation: pass `--proxies proxies.txt` to `bulk_extract.py` and `discover_urls.py`. `--retries N` (default 3) retries `requests.RequestException` failures with jitter sleep; parse errors are not retried. Network errors (HTTPError, ProxyError) count toward the quality gate via `CrawlQualityTracker.record_network_error()`. `--output-dir` sets where `extraction_state.json` and `failed_urls.txt` are written (default: `output/`).

**failed_urls.txt format:** Written as `url\terror` (tab-separated). The bulk_extract.py reader strips the error part automatically — safe to pass directly as `--urls` input for retries.

**EUR pricing in crawl:** benu.bg serves prices natively in EUR (Vue.js `variant.price` field). `price_eur` = raw EUR; `price` (BGN) = `price_eur × 1.95583`. CSV `Price` column currently exports BGN (Shopify store base). When store base switches to EUR, swap `csv_exporter.py:120` to `product.price_eur` — marked with `TODO(EUR-transition)`.

**Known benu.bg data issues:**
- 2 Vichy Dercos combo products: empty price (combo price rendered differently — not a code bug)
- 119 duplicate SKU groups: 106 near-expiry "Годен до" variants + 13 true duplicates

**Google Ads — Bulgarian market limitations:**
- Google Shopping / Merchant Center feed is **not available in Bulgaria**. PMax campaigns targeting Bulgaria will show "No products for any locations" — this is a platform limitation, not a configuration error.
- Many Google Ads features are disabled for the Bulgarian market (confirmed by Google partner).
- Recommended campaign type for Bulgaria: **Dynamic Search Ads (DSA)** — uses URL/content crawling, does not depend on Shopping feed.
- Google Ads API developer token (`U8t0BWmbOgkKz9hga9_rkw`) has **test-only access** — cannot modify production accounts. Use **Claude-in-Chrome MCP** for campaign management instead.
- Active account: **825-619-0101 (ViaPharma US, EUR)**, `ocid=8001809503` in URLs. Account 306-969-3810 is canceled (was BGN).
- Manager account: **966-252-5245 (Viapharma)**.
- **Claude-in-Chrome on ads.google.com:** `find` and `computer` (click/type) work; `read_page` and `javascript_tool` are blocked by Google's CSP. Navigate to the campaigns page first — deep URLs sometimes redirect; use `find`/`computer` to drill in from there.

**Shopify API deprecations (deadline Apr 1 2026):**
- `productsCount` — must pass `(limit: null)` for uncapped count; fixed in `shopify_delete_products.py`
- `Blog.articlesCount` in Liquid — platform-level property with no argument syntax; no fix possible in Liquid code

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
