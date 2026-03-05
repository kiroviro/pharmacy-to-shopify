# EUR/BGN Dual Pricing — Full Change Log

**Date:** 2026-03-05
**Status:** Live on viapharma.us
**Commits:** `8d49b37` → `b7a72fc` (viapharma.us-theme `main`)

## Why

Customers were cancelling orders because checkout and notification emails showed only BGN prices. Product pages showed EUR (via a third-party plugin that was removed). This change replaces the plugin with native theme code and extends EUR display to the cart, cart drawer, and notification emails.

---

## Conversion Formula (everywhere)

Bulgaria is in ERM II — the rate is legally fixed:

```
1 EUR = 1.95583 BGN  (exact, never changes)
```

Shopify stores all prices as **integer BGN cents** (e.g. 1012 = 10.12 лв.). To get EUR cents:

```liquid
{% assign eur_cents = bgn_cents | divided_by: 1.95583 | round: 0 %}
€{{ eur_cents | money_without_currency }}
```

`money_without_currency` on an integer treats it as cents and formats it as `X.XX`.

---

## Files Changed (viapharma.us-theme)

### 1. `assets/viapharma-apple.css` — new CSS block at end of file

```css
/* ── EUR payment notice above checkout button ────────── */
.cart__eur-notice {
  font-size: 0.82em;
  text-align: center;
  color: var(--color-foreground);
  opacity: 0.75;
  margin-bottom: 0.6rem;
}

/* ── Dual EUR/BGN pricing ─────────────────────────────── */
.price-item--eur {
  font-weight: 600;
}

.price-item--bgn,
.totals__bgn-note {
  display: block;
  line-height: 1.3;
}
```

**Usage:** `.price-item--eur` wraps EUR amounts (bold). `.price-item--bgn` wraps BGN amounts (block, same size). `.totals__bgn-note` is used for BGN on cart totals. `.cart__eur-notice` is the pre-checkout notice paragraph.

---

### 2. `snippets/price.liquid` — product cards + product detail pages

**What changed:**

Added two `assign` lines at the end of the `{%- liquid -%}` block:
```liquid
assign eur_cents = price | divided_by: 1.95583 | round: 0
assign compare_at_eur_cents = compare_at_price | divided_by: 1.95583 | round: 0
```

**`.price__regular` div** (no-sale state): EUR span first (`price-item--eur`), then BGN span (`price-item--bgn`).

**`.price__sale` div** (sale state): EUR sale first (`price-item--eur`), EUR compare-at struck through (`<s>`), discount badge, then BGN span at bottom containing both BGN sale price and BGN compare-at struck through.

**Unit price section** (lines ~80-93): untouched.

---

### 3. `sections/main-cart-footer.liquid` — cart page total + notice

**Totals div** (was line 121-124): replaced `cart.total_price | money_with_currency` with:
```liquid
{%- assign cart_eur_cents = cart.total_price | divided_by: 1.95583 | round: 0 -%}
<p class="totals__total-value">€{{ cart_eur_cents | money_without_currency }}</p>
<p class="totals__bgn-note">{{ cart.total_price | money_with_currency }}</p>
```

**Checkout button**: added notice paragraph immediately before:
```liquid
<p class="cart__eur-notice">💳 Плащането се извършва в евро (EUR). 1 € = 1.9558 лв.</p>
```

---

### 4. `snippets/cart-drawer.liquid` — cart drawer total, line items + notice

**Total div** (was line 515-518): same pattern as cart footer above, with `.h5` class preserved on the EUR paragraph.

**Line item unit price** (regular + discounted): same EUR-first pattern as `price.liquid`, using `drawer_item_eur`, `drawer_orig_eur`, `drawer_final_eur` variable names.

**Line item total column** (regular + discounted): same EUR-first pattern using `drawer_line_eur`, `drawer_orig_line_eur`, `drawer_final_line_eur`.

**Checkout button**: same `.cart__eur-notice` paragraph as cart footer.

---

### 5. `sections/main-cart-items.liquid` — cart page line items

Four edits (same pattern throughout):

- **Regular unit price**: assign `item_eur`, render `€X.XX<br><span class="price-item--bgn">X.XX лв.</span>`
- **Discounted unit price**: assign `item_orig_eur` + `item_final_eur`, EUR on struck-through original, EUR+BGN on final price
- **Regular line total** (`replace_all: true` — appears in both mobile and desktop columns): assign `line_eur`, same pattern
- **Discounted line total** (`replace_all: true`): assign `orig_line_eur` + `final_line_eur`, same pattern

---

## What Was NOT Changed (Known Limitation)

### Native Shopify checkout page

The checkout page (`/checkouts/...`) is fully controlled by Shopify and **cannot be customised on Basic/Shopify/Advanced plans**. It shows `BGN X.XX лв.` only.

The `.cart__eur-notice` above the checkout button is the mitigation — customers are informed before they click through.

### After upgrading to Shopify Plus

Shopify Plus unlocks **Checkout UI Extensions**. To add EUR to the checkout page after upgrading:

1. Create a Shopify app (or use an existing extension) with a checkout UI extension
2. Use the `OrderSummarySection` or `Banner` extension point to display EUR equivalent
3. The conversion formula stays the same: `EUR = BGN / 1.95583`
4. Example extension code (React/JSX):
   ```jsx
   import { Banner, useCartLines } from "@shopify/checkout-ui-extensions-react";
   // Get total in cents, divide by 195.583 to get EUR
   const eurTotal = (totalBGNCents / 195.583).toFixed(2);
   return <Banner>💳 Обща сума в евро: €{eurTotal}</Banner>;
   ```
5. Remove the `.cart__eur-notice` paragraphs from `main-cart-footer.liquid` and `cart-drawer.liquid` once the checkout extension covers this.

---

## Notification Email Templates (Manual — Shopify Admin)

**Status: NOT YET DONE** — requires manual editing in Shopify Admin → Settings → Notifications.

**Templates to edit:** Order confirmation, Shipping confirmation, Order edited

**Line item prices:**
```liquid
{%- assign li_eur = line_item.final_price | divided_by: 1.95583 | round: 0 -%}
€{{ li_eur | money_without_currency }} × {{ line_item.quantity }}
<small style="color:#999">{{ line_item.final_price | money }} лв.</small>
```

**Line item total:**
```liquid
{%- assign li_total_eur = line_item.final_line_price | divided_by: 1.95583 | round: 0 -%}
€{{ li_total_eur | money_without_currency }}
<br><small style="color:#999">{{ line_item.final_line_price | money }} лв.</small>
```

**Subtotal:**
```liquid
{%- assign sub_eur = subtotal_price | divided_by: 1.95583 | round: 0 -%}
€{{ sub_eur | money_without_currency }}
<br><small style="color:#999">{{ subtotal_price | money }} лв.</small>
```

**Order total:**
```liquid
{%- assign total_eur = total_price | divided_by: 1.95583 | round: 0 -%}
<strong>€{{ total_eur | money_without_currency }}</strong>
<br><small style="color:#999">{{ total_price | money }} лв.</small>
```

Use "Send test notification" in Shopify Admin to verify after saving each template.

---

## Conflict Note: Shopify Auto-Backups

The Shopify GitHub integration auto-pushes theme snapshots to `origin/main` whenever the theme is saved in Admin. These commits conflict with our customisations.

**Resolution strategy:** `git merge -X ours origin/main` — always keep our changes when conflicts arise. The auto-backup commits only affect content we've already intentionally overridden.

```bash
cd viapharma.us-theme
git fetch origin
git merge -X ours origin/main --no-edit
git push origin main
```
