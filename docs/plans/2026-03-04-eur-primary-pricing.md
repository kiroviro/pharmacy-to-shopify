# EUR Primary Pricing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show EUR as the primary price and BGN as secondary across product pages, cart, cart drawer, and order notification emails.

**Architecture:** Pure Liquid computation (BGN cents ÷ 1.95583 = EUR cents) — no metafields, no JS, no plugin. The `snippets/price.liquid` snippet is the single source for all product card and product detail prices; editing it covers the entire storefront. Cart totals are in two separate files. Email templates are edited manually in Shopify Admin (not in the theme repo).

**Tech Stack:** Shopify Liquid, CSS (viapharma-apple.css), theme push via `python scripts/push_theme.py` from the `pharmacy-to-shopify` repo.

---

## Conversion Formula

Shopify stores all money values as **integer cents** (e.g. 1012 = 10.12 лв.).

```liquid
{% assign eur_cents = price | divided_by: 1.95583 | round: 0 %}
```

`money_without_currency` on the result gives the decimal string (e.g. 518 → "5.18").

---

## Task 1: Add CSS for secondary BGN style

**Files:**
- Modify: `../../viapharma.us-theme/assets/viapharma-apple.css` (append at end)

**Step 1: Append the CSS block**

Add to the very end of `assets/viapharma-apple.css`:

```css
/* ── Dual EUR/BGN pricing ─────────────────────────────── */
.price-item--eur {
  font-weight: 600;
}

.price-item--bgn,
.totals__bgn-note {
  font-size: 0.82em;
  opacity: 0.65;
  display: block;
  line-height: 1.3;
}
```

**Step 2: Push the file**

Run from the `pharmacy-to-shopify` directory:
```bash
python scripts/push_theme.py assets/viapharma-apple.css
```
Expected: `✓ Uploaded assets/viapharma-apple.css`

**Step 3: Commit**

```bash
cd ../../viapharma.us-theme
git add assets/viapharma-apple.css
git commit -m "feat: add dual EUR/BGN price styles"
```

---

## Task 2: Rewrite `snippets/price.liquid` for EUR-primary display

**Files:**
- Modify: `../../viapharma.us-theme/snippets/price.liquid` (full rewrite)

### What the file does now

- Lines 13-33: Liquid block assigns `price`, `compare_at_price`, `money_price`
- Lines 42-47: `.price__regular` div — shown when no sale; renders `money_price` (BGN)
- Lines 48-70: `.price__sale` div — shown on sale; renders sale price + struck-through compare-at (both BGN)
- Lines 72-85: unit price (leave untouched)

### Step 1: Update the Liquid computation block (lines 13-33)

Replace the existing `{%- liquid ... -%}` block with:

```liquid
{%- liquid
  if use_variant
    assign target = product.selected_or_first_available_variant
  else
    assign target = product
  endif

  assign compare_at_price = target.compare_at_price
  assign price = target.price | default: 1999
  assign available = target.available | default: false
  assign money_price = price | money
  if settings.currency_code_enabled
    assign money_price = price | money_with_currency
  endif

  assign discount_percentage = compare_at_price | minus: price | times: 100.0 | divided_by: compare_at_price | round: 0

  if target == product and product.price_varies
    assign money_price = 'products.product.price.from_price_html' | t: price: money_price
  endif

  assign eur_cents = price | divided_by: 1.95583 | round: 0
  assign compare_at_eur_cents = compare_at_price | divided_by: 1.95583 | round: 0
-%}
```

Only two lines added at the bottom of the block; everything else is identical.

### Step 2: Replace `.price__regular` div (lines 42-47)

Replace:
```liquid
    <div class="price__regular">
      <span class="visually-hidden visually-hidden--inline">{{ 'products.product.price.regular_price' | t }}</span>
      <span class="price-item price-item--regular">
        {{ money_price }}
      </span>
    </div>
```

With:
```liquid
    <div class="price__regular">
      <span class="visually-hidden visually-hidden--inline">{{ 'products.product.price.regular_price' | t }}</span>
      <span class="price-item price-item--regular price-item--eur">
        €{{ eur_cents | money_without_currency }}
      </span>
      <span class="price-item price-item--bgn">
        {{ money_price }}
      </span>
    </div>
```

### Step 3: Replace `.price__sale` div (lines 48-70)

Replace:
```liquid
    <div class="price__sale">
      <span class="visually-hidden visually-hidden--inline">{{ 'products.product.price.sale_price' | t }}</span>
      <span class="price-item price-item--sale">
        {{ money_price }}
      </span>
      {%- unless product.price_varies == false and product.compare_at_price_varies %}
        <span class="visually-hidden visually-hidden--inline">{{ 'products.product.price.regular_price' | t }}</span>
        <span class="price-item--last">
          <s class="price-item price-item--regular">
            {% if settings.currency_code_enabled %}
              {{ compare_at_price | money_with_currency }}
            {% else %}
              {{ compare_at_price | money }}
            {% endif %}
          </s>
        </span>
        {% if price_badge %}
          <span class="discount-badge badge text-color-secondary background--sale">
            {{ discount_percentage }}% Off
          </span>
        {% endif %}
      {%- endunless -%}
    </div>
```

With:
```liquid
    <div class="price__sale">
      <span class="visually-hidden visually-hidden--inline">{{ 'products.product.price.sale_price' | t }}</span>
      <span class="price-item price-item--sale price-item--eur">
        €{{ eur_cents | money_without_currency }}
      </span>
      {%- unless product.price_varies == false and product.compare_at_price_varies %}
        <span class="visually-hidden visually-hidden--inline">{{ 'products.product.price.regular_price' | t }}</span>
        <span class="price-item--last">
          <s class="price-item price-item--regular price-item--eur">
            €{{ compare_at_eur_cents | money_without_currency }}
          </s>
        </span>
        {% if price_badge %}
          <span class="discount-badge badge text-color-secondary background--sale">
            {{ discount_percentage }}% Off
          </span>
        {% endif %}
      {%- endunless -%}
      <span class="price-item price-item--bgn">
        {{ money_price }}
        {%- unless product.price_varies == false and product.compare_at_price_varies -%}
          &nbsp;<s>{{ compare_at_price | money }}</s>
        {%- endunless -%}
      </span>
    </div>
```

**Step 4: Push and verify**

```bash
python scripts/push_theme.py snippets/price.liquid
```
Expected: `✓ Uploaded snippets/price.liquid`

Wait ~2 minutes, then take a screenshot of a product card and the product detail page on viapharma.us to verify EUR appears first, BGN below in muted style.

**Step 5: Commit**

```bash
cd ../../viapharma.us-theme
git add snippets/price.liquid
git commit -m "feat: EUR-primary price display on product cards and detail pages"
```

---

## Task 3: Update cart page total (`sections/main-cart-footer.liquid`)

**Files:**
- Modify: `../../viapharma.us-theme/sections/main-cart-footer.liquid:121-124`

**Step 1: Replace the totals div**

Current code at lines 121-124:
```liquid
                <div class="totals">
                  <h2 class="totals__total">{{ 'sections.cart.estimated_total' | t }}</h2>
                  <p class="totals__total-value">{{ cart.total_price | money_with_currency }}</p>
                </div>
```

Replace with:
```liquid
                <div class="totals">
                  <h2 class="totals__total">{{ 'sections.cart.estimated_total' | t }}</h2>
                  {%- assign cart_eur_cents = cart.total_price | divided_by: 1.95583 | round: 0 -%}
                  <p class="totals__total-value">€{{ cart_eur_cents | money_without_currency }}</p>
                  <p class="totals__bgn-note">{{ cart.total_price | money_with_currency }}</p>
                </div>
```

**Step 2: Push and verify**

```bash
python scripts/push_theme.py sections/main-cart-footer.liquid
```

Open the cart page at viapharma.us/cart and confirm the total shows EUR prominently with BGN below.

**Step 3: Commit**

```bash
cd ../../viapharma.us-theme
git add sections/main-cart-footer.liquid
git commit -m "feat: EUR-primary total on cart page"
```

---

## Task 4: Update cart drawer total (`snippets/cart-drawer.liquid`)

**Files:**
- Modify: `../../viapharma.us-theme/snippets/cart-drawer.liquid:515-518`

**Step 1: Replace the totals div**

Current code at lines 515-518:
```liquid
          <div class="totals" role="status">
            <h2 class="totals__total h5">{{ 'sections.cart.estimated_total' | t }}</h2>
            <p class="totals__total-value h5">{{ cart.total_price | money_with_currency }}</p>
          </div>
```

Replace with:
```liquid
          <div class="totals" role="status">
            <h2 class="totals__total h5">{{ 'sections.cart.estimated_total' | t }}</h2>
            {%- assign cart_eur_cents = cart.total_price | divided_by: 1.95583 | round: 0 -%}
            <p class="totals__total-value h5">€{{ cart_eur_cents | money_without_currency }}</p>
            <p class="totals__bgn-note">{{ cart.total_price | money_with_currency }}</p>
          </div>
```

**Step 2: Push and verify**

```bash
python scripts/push_theme.py snippets/cart-drawer.liquid
```

Open viapharma.us, add a product to cart, open the cart drawer — confirm EUR total is displayed prominently with BGN below.

**Step 3: Commit**

```bash
cd ../../viapharma.us-theme
git add snippets/cart-drawer.liquid
git commit -m "feat: EUR-primary total in cart drawer"
```

---

## Task 5: Update Shopify notification email templates (manual — Shopify Admin)

**This step is done in the browser, not via code.** Email templates are not stored in the theme repo.

**Where:** Shopify Admin → Settings → Notifications

**Templates to edit:** Order confirmation, Shipping confirmation, Order edited

---

### Line items: add EUR

Find the line item price block. It will contain something like:

```liquid
{{ line_item.final_line_price | money }}
```

Replace each occurrence of a line item price with:

```liquid
{%- assign li_eur = line_item.final_price | divided_by: 1.95583 | round: 0 -%}
€{{ li_eur | money_without_currency }} × {{ line_item.quantity }}&nbsp;&nbsp;<small style="color:#999">{{ line_item.final_price | money }} лв.</small>
```

And for the line total (right column):

```liquid
{%- assign li_total_eur = line_item.final_line_price | divided_by: 1.95583 | round: 0 -%}
€{{ li_total_eur | money_without_currency }}<br><small style="color:#999">{{ line_item.final_line_price | money }} лв.</small>
```

---

### Order totals block: EUR primary

Find the subtotal/total rows. They'll look like:

```liquid
{{ subtotal_price | money }}
```

Replace:
```liquid
{%- assign sub_eur = subtotal_price | divided_by: 1.95583 | round: 0 -%}
€{{ sub_eur | money_without_currency }}<br><small style="color:#999">{{ subtotal_price | money }} лв.</small>
```

And for order total:
```liquid
{%- assign total_eur = total_price | divided_by: 1.95583 | round: 0 -%}
<strong>€{{ total_eur | money_without_currency }}</strong><br><small style="color:#999">{{ total_price | money }} лв.</small>
```

**Verify:** Use the "Send test notification" button in Shopify Admin after saving each template. Check the email shows EUR first, BGN second.

---

## Final Verification Checklist

- [ ] Product card on collection page: EUR large + BGN small below
- [ ] Product detail page: same as card
- [ ] Sale product: EUR sale + EUR struck-through compare-at; BGN sale + BGN compare-at below
- [ ] Cart page total: EUR primary, BGN muted below
- [ ] Cart drawer total: same
- [ ] Order confirmation email: line item EUR first, BGN secondary; totals same
- [ ] No visual regression on non-price elements (badges, unit prices, sold-out state)
