# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Changed - 2026-02-18

#### Price Extraction Overhaul

**Breaking change:** Price extraction now uses Vue.js component data instead of JSON-LD

**Motivation:**
- JSON-LD prices were found to be stale/incorrect (up to -60% discrepancies)
- Could not distinguish between regular prices and promotional prices
- Missing "Compare-at price" data needed for Shopify discounts

**Implementation:**
- Modified `src/extraction/pharmacy_extractor.py`:
  - `_extract_prices()`: Now extracts from Vue.js `<add-to-cart :product>` component (primary), falls back to JSON-LD (with warning)
  - `_extract_original_price()`: Now extracts regular price for promotional products (was stubbed)
  - Added carousel detection to skip related product prices in HTML fallback

**Data improvements:**
- ✅ Accurate current prices (from Vue.js `discountedPrice`)
- ✅ Original prices for products on promotion (from Vue.js `price`)
- ✅ Distinguishes promotional vs regular pricing
- ✅ Supports Shopify "Compare-at price" field for showing savings
- ✅ EUR/BGN dual currency (Bulgaria's Euro transition)

**Architecture updates:**
- Updated `docs/ARCHITECTURE.md`: Added "Price Extraction" section with Vue.js component details
- Updated extraction strategy table to reflect new priority order

**Impact:**
- Requires re-extraction of all products to get accurate prices
- Products will have correct base prices for running independent promotions
- Future-proof for Bulgaria's EUR adoption (easy config switch)

**Testing:**
- Test promotional product: `https://benu.bg/apivita-just-bee-clear-pochistvasht-gel-za-lice-200ml`
- Test regular product: `https://benu.bg/aroma-izmiven-gel-zdrave-akne-stop-v-glen-150ml`

**Migration path:**
1. Test on sample products with `scripts/extract_single.py`
2. Re-extract full catalog with `scripts/bulk_extract.py` (~4-5 hours)
3. Export and import to Shopify with updated prices

---

## Previous Changes

(No previous changelog entries - project started Feb 2026)
