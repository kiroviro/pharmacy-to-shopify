## Commands

```bash
pytest                         # Run all tests
pytest tests/extraction/       # Run extraction tests only
ruff check src/ tests/         # Lint
ruff format src/ tests/        # Format
python scripts/extract_single.py <url>  # Debug single product extraction
```

## Pipeline (8 stages)

```
discover_urls.py → bulk_extract.py → validate_crawl.py → cleanup_tags.py
→ export_by_brand.py → [Shopify CSV import] → create_shopify_collections.py
→ google_ads_pmax.py
```

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
| `src/validation/crawl_tracker.py` | Aggregate stats, quality gate |
| `src/shopify/csv_exporter.py` | 56-col CSV; single source of truth for column layout |
| `src/common/constants.py` | EUR/BGN rate (1.95583), field defaults |
| `config/known_brands.yaml` | 450+ brand database |

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
```
Credentials from `.env` or `.shopify_token.json`. Theme ID: `195131081041`.
**Pushing to `main` branch auto-deploys to live production at viapharma.us.**
