# Ликвидация Section — Design Spec

**Date:** 2026-03-28
**Status:** Approved

## Goal

Surface pharmacy overstock products (≥15% discount) on the viapharma.us homepage and a dedicated collection page, sorted by biggest discount first. The pharmacist sets prices manually in Shopify Admin or via viapharma-pricing; this feature only handles display.

## Scope

- Homepage section: inline grid of top 8 liquidation products + "Виж всички ликвидации →" link
- Collection page: `/collections/likvidatsii` — full page with all ≥15% discounted products, sorted by discount %
- No backend script, no cron job, no tags — pure client-side filtering and sorting

## Current State

As of 2026-03-28: 65 products qualify (≥15% discount), 51 at ≥20%, 32 at ≥30%. Source of truth is `compare_at_price` set by viapharma-pricing or manually in Shopify Admin.

## Architecture

### No server-side components

The filter (≥15%) and sort (discount % descending) are computed entirely in the browser from Shopify's `products.json` endpoint. No tags, no scripts, no cron.

### Data source

Both homepage section and collection page fetch from the `namaleniya` collection (`/collections/namaleniya/products.json`), which already contains all products with `compare_at_price > 0`.

- Homepage: fetches first 1–2 pages (250–500 products). At current density (~3% qualify), the first 250 products yield ~8 qualifying products on average — sufficient for the homepage display.
- Collection page: fetches all pages to ensure all 65+ qualifying products are shown and correctly sorted.

### Discount calculation

```
discount_pct = (compare_at_price - price) / compare_at_price
```

Cards without `compare_at_price` or with `compare_at_price = 0` are excluded. Cards below 15% sort to the bottom (homepage) or are hidden (collection page).

## Components

### 1. `sections/liquidation-products.liquid` (new)

Homepage section. Renders a static container with title "Ликвидации" and a "Виж всички" link. On `DOMContentLoaded`, JS:

1. Fetches `/collections/namaleniya/products.json?limit=250`
2. Filters variants to find products where `(compare_at_price - price) / compare_at_price >= 0.15`
3. Sorts descending by discount %
4. Renders top N product cards (section setting: 4 / 8 / 12, default 8) as simplified JS-generated cards (image, title, price, compare-at, discount badge) styled to match existing product card CSS
5. Hides section if 0 qualifying products found

Section settings (Shopify customizer):
- `title` — string, default "Ликвидации"
- `products_to_show` — range 4–12, default 8
- `collection` — collection picker, default `namaleniya`

### 2. `/collections/likvidatsii` (new Shopify collection)

Shopify Smart Collection with rule `variant_compare_at_price > 0` (identical logic to `namaleniya`, different handle and title). Assigned template: `collection.likvidatsii`.

Created via `scripts/create_sale_collection.py` — add `create_liquidation_collection()` alongside the existing `create_sale_collection()`.

### 3. `templates/collection.likvidatsii.json` (new)

Collection page template. Mirrors `templates/collection.namaleniya.json` structure (banner + product grid). The product grid section includes the JS sort/filter overlay specific to this page.

On page load, JS:
1. Fetches all pages of `/collections/likvidatsii/products.json?limit=250`
2. Filters to ≥15% discount
3. Sorts descending by discount %
4. Replaces the Liquid-rendered product grid with JS-rendered cards
5. Adds a load-more button if >24 products qualify

### 4. `templates/index.json` (modified)

Add `liquidation-products` section to the homepage, positioned above or below the existing `namaleniya` featured collection section (user decides position during implementation).

## Data Flow

```
Pharmacist sets compare_at_price (Shopify Admin or viapharma-pricing)
        ↓
namaleniya smart collection auto-includes product (compare_at_price > 0)
        ↓
Homepage JS fetches namaleniya/products.json → filter ≥15% → sort → render top 8
        ↓
User clicks "Виж всички" → /collections/likvidatsii
        ↓
Collection page JS fetches all pages → filter ≥15% → sort → render full list
```

## Error Handling

- **JS fetch fails:** section stays hidden (no broken UI)
- **0 qualifying products:** section hidden via JS (homepage); collection page shows empty state message
- **Product missing compare_at_price:** excluded from results silently
- **Partial page fetch on collection page:** show what was loaded, log warning to console

## Testing

1. **Unit logic:** pure function `computeDiscount(price, compareAt) → pct | null` — test edge cases (zero, null, equal prices, negative)
2. **Filter/sort:** given mock products JSON, assert correct filtering at 15% boundary and sort order
3. **Dry visual check:** screenshot homepage and `/collections/likvidatsii` after deploy, confirm section renders and sort is correct
4. **Empty state:** temporarily set threshold to 99% in dev to verify section hides cleanly

## Files to Create / Modify

| File | Action | Repo |
|------|--------|------|
| `sections/liquidation-products.liquid` | Create | viapharma.us-theme |
| `templates/collection.likvidatsii.json` | Create | viapharma.us-theme |
| `templates/index.json` | Modify — add section | viapharma.us-theme |
| `scripts/create_sale_collection.py` | Modify — add `create_liquidation_collection()` | pharmacy-to-shopify |

## Out of Scope

- Applying discounts to products (done manually or via viapharma-pricing)
- Tagging products with "ликвидация"
- Any backend script or cron job
- The two Фунгитер products mentioned during design — apply their -20% discount manually in Shopify Admin before the section goes live
