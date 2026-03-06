# Notification Email Templates — EUR Pricing Change & Revert Guide

**Changed:** 2026-03-06
**Revert by:** ~2026-07 (when Bulgaria joins the Eurozone and Shopify currency is switched to EUR)

---

## Why this was done

The store currency in Shopify is BGN, but customers pay in EUR (fixed ERM II rate: 1 EUR = 1.95583 BGN). The native notification emails showed BGN-only prices, causing customer confusion and order cancellations. EUR was added as the primary display everywhere, with BGN shown in small grey text as a reference.

---

## Files

| Template | EUR version (active) | Original BGN-only (for revert) |
|----------|----------------------|-------------------------------|
| Order confirmation | `docs/plans/order-confirmation-eur.liquid` | `docs/plans/order-confirmation-original.liquid` |
| Shipping confirmation | `docs/plans/shipping-confirmation-eur.liquid` | *(no original saved — only one `| money` changed, see note below)* |
| Order edited | `docs/plans/order-edited-eur.liquid` | `docs/plans/order-edited-original.liquid` |

**Shipping confirmation note:** The shipping confirmation template has no price cells. Only one change was made: the inline discount badge `(-{{ discount_allocation.amount | money }})` → EUR/BGN format. To revert, find that line and restore it.

---

## How to apply (or revert) each template

1. Go to `https://61a7bb-4d.myshopify.com/admin/settings/notifications`
2. Click the template name → **Edit code**
3. Select all (Cmd+A), delete
4. Open the appropriate `.liquid` file in your editor, select all, copy, paste
5. Click **Save**, then **Send test notification** to verify

---

## What changes between the two versions

Every price display was changed from:
```liquid
{{ PRICE | money }}
```
to:
```liquid
{%- assign _eur = PRICE | divided_by: 1.95583 | round: 0 -%}
€{{ _eur | money_without_currency }}<br><small style="color:#999;">({{ PRICE | money }} лв.)</small>
```

Affected price locations (Order confirmation and Order edited):
- Line item final prices and line totals
- Strikethrough original prices (del tags)
- Subtotal row
- Order discount rows
- Shipping rows (including discounted shipping, free shipping del, discount badge)
- Tax, duties, tip rows
- Order total (strong)
- Transaction/payment method rows (Visa, gift card, refund, rounding)
- Inline discount allocation amounts per line item
- Payment terms / next amount due

---

## When to revert

When Bulgaria adopts the Euro (expected ~mid-2026):
1. Change the Shopify store currency from BGN to EUR in Admin → Settings → Store details
2. Revert all three notification templates using the original `.liquid` files above
3. Also revert the same EUR conversion changes in the theme files:
   - `snippets/price.liquid`
   - `sections/main-cart-footer.liquid`
   - `snippets/cart-drawer.liquid`
   - `sections/main-cart-items.liquid`
   - Remove `.cart__eur-notice` paragraphs (the pre-checkout notice will be unnecessary)
   - Remove the dual-pricing CSS block from `assets/viapharma-apple.css`

Full theme change log: `docs/plans/2026-03-05-eur-bgn-dual-pricing-changes.md`
