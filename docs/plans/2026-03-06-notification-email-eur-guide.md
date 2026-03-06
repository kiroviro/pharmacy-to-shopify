# EUR Pricing — Notification Email Template Guide

**Status:** Pending manual edit in Shopify Admin
**Path:** Admin → Settings → Notifications → [template] → Edit code

Shopify notification templates cannot be updated via the API.
This document gives exact find/replace instructions for each template.

---

## How to open a template

1. Go to `https://61a7bb-4d.myshopify.com/admin/settings/notifications`
2. Click the template name (e.g. **Order confirmation**)
3. Click **Edit code** (top right of the template preview)
4. Use your browser's **Ctrl+F** / **Cmd+F** to locate the strings below
5. Click **Save** when done, then **Send test notification** to verify

---

## Conversion snippet (add once at the top of each template's `{% for line_item %}` block)

Every price in Shopify notification templates is in **BGN cents** (integer).
`divided_by: 1.95583 | round: 0` converts to EUR cents; `money_without_currency` formats as `X.XX`.

---

## Template 1 — Order confirmation

### Line item prices

**Find:**
```liquid
{{ line_item.quantity }} × {{ line_item.title }}
```
or
```liquid
{{ line_item.final_price | money }}
```

**Context:** Inside the `{% for line_item in line_items %}` loop in the product table.

**Pattern — wrap each price output like this:**
```liquid
{%- assign li_eur = line_item.final_price | divided_by: 1.95583 | round: 0 -%}
€{{ li_eur | money_without_currency }} <small style="color:#999;">({{ line_item.final_price | money }} лв.)</small>
```

**For line total** (right-side column or end of line):
```liquid
{%- assign li_total_eur = line_item.final_line_price | divided_by: 1.95583 | round: 0 -%}
€{{ li_total_eur | money_without_currency }} <small style="color:#999;">({{ line_item.final_line_price | money }} лв.)</small>
```

### Subtotal row

**Find:**
```liquid
{{ subtotal_price | money }}
```

**Replace with:**
```liquid
{%- assign sub_eur = subtotal_price | divided_by: 1.95583 | round: 0 -%}
€{{ sub_eur | money_without_currency }} <small style="color:#999;">({{ subtotal_price | money }} лв.)</small>
```

### Discount rows (if present)

**Find:**
```liquid
-{{ discount_application.value | money }}
```
or
```liquid
{{ total_discounts | money }}
```

**Replace each** with the same pattern:
```liquid
{%- assign disc_eur = total_discounts | divided_by: 1.95583 | round: 0 -%}
-€{{ disc_eur | money_without_currency }} <small style="color:#999;">(-{{ total_discounts | money }} лв.)</small>
```

### Shipping row

**Find:**
```liquid
{{ shipping_price | money }}
```

**Replace with:**
```liquid
{%- assign ship_eur = shipping_price | divided_by: 1.95583 | round: 0 -%}
{% if shipping_price > 0 %}€{{ ship_eur | money_without_currency }} <small style="color:#999;">({{ shipping_price | money }} лв.)</small>{% else %}Безплатна{% endif %}
```

### Order total (most important)

**Find:**
```liquid
{{ total_price | money }}
```

**Replace with:**
```liquid
{%- assign total_eur = total_price | divided_by: 1.95583 | round: 0 -%}
<strong>€{{ total_eur | money_without_currency }}</strong> <small style="color:#999;">({{ total_price | money }} лв.)</small>
```

---

## Template 2 — Shipping confirmation

This template shows an order summary. Apply the **same replacements** as Order confirmation:

- `line_item.final_price | money` → EUR + BGN
- `line_item.final_line_price | money` → EUR + BGN
- `subtotal_price | money` → EUR + BGN
- `total_price | money` → EUR + BGN (bold)

---

## Template 3 — Order edited

Same structure as Order confirmation. Apply the same replacements.

---

## Verification

After saving each template:
1. Click **Send test notification** (button appears after saving)
2. Check the email — confirm EUR appears first, BGN in small grey text

---

## Example — what the order confirmation email should look like after

```
Адирекс х6 дози Neopharm             €5.18  (10.12 лв.)  × 1    €5.18  (10.12 лв.)
Адирекс за деца саше Neopharm        €4.14  (8.10 лв.)   × 6   €24.86  (48.60 лв.)

Междинна сума     €30.04  (58.72 лв.)
Изпращане         Безплатна
Обща сума         €30.04  (58.72 лв.)
```

---

## Notes

- The exact Liquid variable names (`line_item.final_price`, `total_price`, etc.) are standard Shopify — they work in all notification templates.
- If the template uses `order.line_items` instead of `line_items`, prefix accordingly: `order.subtotal_price`, `order.total_price`.
- Do NOT use `| money_with_currency` for the EUR values — it will append "BGN" to them.
