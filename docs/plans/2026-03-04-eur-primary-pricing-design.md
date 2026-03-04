# EUR Primary Pricing Design

**Date:** 2026-03-04
**Status:** Approved
**Scope:** Product pages, cart, cart drawer, order notification emails

## Problem

Customers are cancelling orders because checkout and notification emails show only BGN (лв.) prices. Product pages already show dual EUR/BGN (via a plugin being removed), but the plugin is being replaced with native theme code. EUR should be the primary displayed currency; BGN secondary.

Shopify is on a non-Plus plan — the native checkout page cannot be customised.

## Conversion

Fixed ERM II rate: **1 EUR = 1.95583 BGN**

Shopify stores money as integer cents. EUR cents = BGN cents / 1.95583.

```liquid
{% assign eur_cents = price | divided_by: 1.95583 | round: 0 %}
```

## Display Format

### Regular price
```
€5.18          ← primary (large, bold)
10.12 лв.      ← secondary (small, muted)
```

### Sale price
```
€5.18          ← sale EUR, primary
~~€6.64~~      ← compare-at EUR, struck through
10.12 лв.      ← sale BGN, muted
~~12.99 лв.~~  ← compare-at BGN, struck through
```

### Cart / drawer total
```
Обща сума    €30.02      ← EUR primary
             58.72 лв.   ← BGN secondary, small
```

### Email line item
```
Product name    €5.18 × 1    €5.18
                10.12 лв.
```

### Email total rows
```
Обща сума    €30.02
             58.72 лв.
```

## Files to Change

### Theme (viapharma.us-theme)

| File | Change |
|------|--------|
| `snippets/price.liquid` | Add EUR computation + render EUR first, BGN second. Covers all product cards and product detail pages. |
| `sections/main-cart-footer.liquid` | Add EUR total above BGN total in the `totals` div (line ~123) |
| `snippets/cart-drawer.liquid` | Same treatment for cart drawer total (line ~517) |
| `assets/viapharma-apple.css` | Add `.price-item--bgn`, `.price-item--eur`, `.totals__bgn-note` styles |

### Shopify Admin (manual, not in repo)

Edit notification templates in Admin > Settings > Notifications:
- Order confirmation
- Shipping confirmation
- Order edited

Formula for email Liquid:
```liquid
{% assign eur_cents = line_item.final_price | divided_by: 1.95583 | round: 0 %}
{% assign total_eur_cents = subtotal_price | divided_by: 1.95583 | round: 0 %}
```

## Out of Scope

- Checkout page (sealed on non-Plus — BGN-only unavoidable)
- No metafield migration — pure computed conversion

## Deployment

1. Push theme files via `python scripts/push_theme.py`
2. Take screenshot after ~2 min propagation to verify visual change
3. Edit notification templates manually in Shopify Admin
