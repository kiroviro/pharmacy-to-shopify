# Намаления Menu Fix — Design

**Date:** 2026-03-08
**Status:** Approved

## Problem

Two independent bugs make the Намаления top-level mega menu show wrong products:

1. **Wrong collection rule.** The "Намаления" smart collection is driven by `tag = Намаление`. The tag sync script (`tag_discounted_products.py`) runs manually and is frequently stale. Products that are no longer discounted remain in the collection until the script is run again.

2. **Sub-navigation bypasses the discount filter.** Every L1/L2/L3 link inside the Намаления mega-menu columns links to a full category collection (e.g. `/collections/lechenie-i-zdrave`). Clicking any sub-category shows ALL products in that category, ignoring the discount filter entirely.

## Approved Solution

### Part 1 — Change collection rule to `compare_at_price > 0`

Replace the tag-based smart collection rule with Shopify's native `variant_compare_at_price > 0` condition.

**Why this works:**
- `viapharma-pricing` sends `compare_at_price: null` (via `None`) to the Shopify API whenever a product is no longer discounted. This is consistent across all 4 repricing scripts (Phoenix, competitive, cosmetics, benu sync).
- Shopify evaluates the collection rule live after every API price write — no scripts, no tags, no lag.
- Zero manual steps required after any pricing change.

**Known limitation:** Products excluded from a repricing run (e.g. cosmetics when running Phoenix repricing) retain their `compare_at_price` until their next repricing. They may appear in the collection briefly as "ghost" discounted products. Acceptable trade-off given zero-maintenance benefit.

**Implementation:** Update `ShopifyCollectionCreator.create_sale_collection()` in `src/shopify/collections.py` to use `column: "variant_compare_at_price", relation: "greater_than", condition: "0"` instead of the tag rule. Then re-create (or update) the live collection via the script.

### Part 2 — Fix mega-menu sub-navigation URLs

Every L1/L2/L3 link inside the Намаления mega-menu columns in `snippets/header-mega-menu.liquid` must route through the sale collection with a tag filter instead of a standalone category collection.

**Pattern:**
```
Before: /collections/lechenie-i-zdrave
After:  /collections/namaleniya?filter.p.tag=Лечение%20и%20здраве
```

Tag values are exact Bulgarian strings already present on products from the crawl pipeline (`categories.yaml` hierarchy). No new data needed.

**Prerequisite:** Shopify storefront filters must have the `tag` filter enabled on the `namaleniya` collection. Verify in Shopify Admin → Navigation → Filters before deploying.

### Part 3 — One-time stale tag cleanup (optional)

Run `tag_discounted_products.py` once to strip stale `"Намаление"` tags from products. The tags are no longer used to drive the collection, but cleaning them avoids confusion. The tagging script itself is not retired — it remains available for diagnostics.

## Files to Change

| File | Change |
|------|--------|
| `src/shopify/collections.py` | Update `create_sale_collection()` to use `variant_compare_at_price > 0` rule |
| `scripts/create_sale_collection.py` | Add `--update` flag or re-run to apply new rule to live collection |
| `viapharma.us-theme/snippets/header-mega-menu.liquid` | Change all Намаления sub-nav links to `/collections/namaleniya?filter.p.tag=<tag>` |

## Out of Scope

- `tag_discounted_products.py` remains unchanged (not retired, not automated)
- No changes to `viapharma-pricing`
- No new collections created
- No changes to how the mega-menu is structured or rendered — only destination URLs change
