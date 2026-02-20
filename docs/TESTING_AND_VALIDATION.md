# Testing and Validation

## Overview

The project has three layers of validation that run at different points in the pipeline:

| Layer | When | Tool | Scope |
|-------|------|------|-------|
| **1. Field validation** | During crawl, per-product | `SpecificationValidator` | Field presence, format, URL safety |
| **2. Source consistency** | During crawl, per-product | `SourceConsistencyChecker` | Cross-checks Vue vs JSON-LD vs HTML DOM |
| **3. Aggregate quality** | During crawl, running total | `CrawlQualityTracker` | Stats, duplicate detection, PASS/FAIL gate |
| **4. Post-crawl** | After crawl, before export | `validate_crawl.py` | CSV coverage rates, duplicate checks, spot-check |
| **5. Post-import** | After Shopify import | `verify_shopify.py` | Shopify API field verification |

Layers 1–3 run automatically inside `bulk_extract.py`. Layers 4–5 are optional CLI scripts.

---

## Running the Test Suite

```bash
# Full pytest suite (all unit tests, no network)
pytest tests/ -v

# Extraction tests only
pytest tests/extraction/ -v

# Validation tests only
pytest tests/validation/ -v
```

**Expected:** 328 passing, 0 failed (1 pre-existing fixture failure in test_extract_benu_product_prices for
a specific Vichy Dercos product whose prices changed — this is a known live-data issue, not a logic bug).

---

## Layer 1 — Field Validation (`SpecificationValidator`)

**File:** `src/extraction/validator.py`

Per-product format and presence checks. Called automatically by `BulkExtractor` during crawl.

**Errors (blocking — counted toward FAIL gate):**

| Field | Check |
|-------|-------|
| `title` | 5–250 chars, non-empty |
| `url` | starts with `https://` |
| `price` | parseable float, > 0 and < 10 000 |
| `brand` | non-empty |
| `sku` | non-empty |
| `category_path` | ≥ 1 element |
| `handle` | non-empty, matches `[a-z0-9-]+`, ≤ 200 chars |
| `images` | ≥ 1 image |
| image URL (each) | starts `https://`, no placeholder domain |
| `price_eur` consistency | if both set: `abs(price - price_eur × 1.95583) / price ≤ 1%` |

**Warnings (non-blocking — logged but not counted toward FAIL gate):**

| Field | Check |
|-------|-------|
| `barcode` | if set: must be 8, 12, 13, or 14 digits (valid GTIN lengths) |
| `description` | non-empty |
| `seo_title` | ≤ 70 chars |
| `seo_description` | ≤ 155 chars |

---

## Layer 2 — Source Consistency (`SourceConsistencyChecker`)

**File:** `src/extraction/consistency_checker.py`

Cross-checks extracted product values against independent data sources within the same already-fetched HTML page. Zero extra HTTP requests.

Three independent data sources on benu.bg:
- **JSON-LD** (`<script type="application/ld+json">`) — structured data
- **Vue.js component** (`<add-to-cart :product="...">`) — real-time pricing
- **BeautifulSoup DOM** — raw HTML selectors

**Checks (all emit warnings, never errors):**

| Check | Source A | Source B | Tolerance |
|-------|----------|----------|-----------|
| Price | Vue `discountedPrice` × 1.95583 | JSON-LD `offers.price` × 1.95583 | ≤ 1% |
| Title | JSON-LD `name` | `<h1>` text | substring match |
| Brand | JSON-LD `brand.name` | `BrandMatcher.match_from_title()` | exact |
| Images | Gallery CSS selectors | JSON-LD `image[]` | ≥ 1 URL in common |
| Category path | JSON-LD `BreadcrumbList` | HTML `.breadcrumb a` | same set |
| Promo logic | `product.price` | `product.original_price` | price < original |
| Barcode | JSON-LD `gtin*` / `ean` fields | `"Баркод:"` text pattern | exact |
| Section: details | header present in page | `product.details` non-empty | presence → content |
| Section: composition | header present in page | `product.composition` non-empty | presence → content |
| Section: usage | header present in page | `product.usage` non-empty | presence → content |
| Section: contraindications | header present in page | `product.contraindications` non-empty | presence → content |

A warning fires **only when both sides have data and they disagree**. If one side is missing, the check is silently skipped.

Warning format: `consistency_price: Vue=13.50 BGN vs JSON-LD=13.49 BGN (0.1% deviation)`

---

## Layer 3 — Aggregate Quality Tracking (`CrawlQualityTracker`)

**File:** `src/validation/crawl_tracker.py`

Accumulates per-product results across the full crawl and prints summaries.

**Periodic summary** (printed every 100 products during crawl):
```
[Progress 1200] Quality: ✅ 97.2% valid | ⚠️  2.1% warnings | ❌ 0.7% errors
  Top issues: brand (7), consistency_price (4)
```

**Final report** (printed at end of crawl):
```
============================================================
Quality Report  [PASS]
============================================================
  Total products:   9270
  Valid (no issues):  9012  (97.2%)
  Warnings only:       195  (2.1%)
  Errors:               63  (0.7%)

  Per-field failure rates (top 10):
    brand                          45  (0.5%)
    consistency_price              32  (0.3%)
    images                         18  (0.2%)
    ...

  Duplicate handles: 0
  Duplicate SKUs:    3 (e.g. '8825')

  Price range: 0.89 – 312.50 BGN

  Gate (>5% errors = FAIL): PASS
============================================================
```

**FAIL gate:** If the error rate exceeds 5%, `bulk_extract.py` exits with code 1 after printing the report.

**What's counted:**
- Errors (from `SpecificationValidator`) count toward the error rate and per-field breakdown
- Warnings (from both `SpecificationValidator` and `SourceConsistencyChecker`) appear in the per-field breakdown but do NOT affect the FAIL gate

---

## Layer 4 — Post-Crawl Validation (`validate_crawl.py`)

**File:** `scripts/validate_crawl.py`

Validates the raw CSV after extraction, before export. Recommended before every import.

```bash
# Basic validation
python3 scripts/validate_crawl.py --csv data/benu.bg/raw/products.csv

# With live spot-check (fetches 100 random product pages — takes ~2 minutes)
python3 scripts/validate_crawl.py \
  --csv data/benu.bg/raw/products.csv \
  --spot-check 100

# Save JSON report
python3 scripts/validate_crawl.py \
  --csv data/benu.bg/raw/products.csv \
  --spot-check 100 \
  --report output/validation_report.json
```

**What it checks:**
- Duplicate handles and SKUs across the full CSV
- Field coverage rates (price, brand, images, barcode, description)
- Image URL domain validation (flags placeholder domains)
- Price range outliers
- Spot-check (live benu.bg): title, price, brand, and HTTP 200 on at least 1 image URL

**Exit codes:** `0` = PASS (≤5% errors), `1` = FAIL (>5% errors or critical issues)

---

## Layer 5 — Post-Import Verification (`verify_shopify.py`)

**File:** `scripts/verify_shopify.py`

After importing the CSV to Shopify, verifies that products landed correctly.

```bash
python3 scripts/verify_shopify.py \
  --csv data/benu.bg/raw/products.csv \
  --shop viapharma \
  --sample 100
```

Set `SHOPIFY_ACCESS_TOKEN` in your `.env` or pass `--token`.

**What it checks:** For 100 sampled products:
- Product exists in Shopify
- Title matches
- Vendor (brand) matches
- Price within 5% tolerance

---

## GTIN / Barcode Validation

benu.bg labels both GTINs and internal SKUs as "Баркод" (Barcode). Only valid GTINs are accepted.

**Valid GTIN lengths:** 8, 12, 13, or 14 digits

| Code | Length | Status | Examples |
|------|--------|--------|---------|
| EAN-13 | 13 digits | ✅ Valid | `3352710009079` (BOIRON) |
| UPC-A | 12 digits | ✅ Valid | `012345678901` |
| EAN-8 | 8 digits | ✅ Valid | `12345678` |
| GTIN-14 | 14 digits | ✅ Valid | `00012345678905` |
| SOLGAR codes | 11 digits | ❌ Invalid | `33984007536` |
| Internal SKUs | 3–7 digits | ❌ Invalid | `559`, `5909` |

**Known exclusions:**
- 174 SOLGAR products with 11-digit codes (not valid GTIN length)
- 43 products with 3–7 digit internal SKUs labeled as barcodes
- These products will not sync to Google Merchant Center (expected behavior)

---

## Known Issues

### Vichy Dercos price fixture

`tests/extraction/test_extract_benu_product_prices.py` contains a fixture for a specific Vichy Dercos
product whose live price changed after the fixture was captured. The test is marked as a known failure
and does not affect CI. Do not update the fixture without re-crawling that URL.

### Near-expiry "Годен до" products

benu.bg lists near-expiry products as separate entries with the same base SKU (e.g., SKU `8825` for
both `АБГ Кардио х30` and `АБГ Кардио х30 Годен до: 30.4.2026 г.`). Both get crawled; `CrawlQualityTracker`
detects and reports the duplicate SKU. No deduplication is performed — both products are kept in the CSV.
