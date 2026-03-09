# Backlog

Tracked items that are not yet planned or scheduled.

---

## Theme: Show BGN (лв) prices alongside EUR everywhere after EUR currency switch

**Added:** 2026-03-09
**Context:** After switching Shopify store base currency from BGN to EUR, the current theme manually computes EUR from BGN (divides by 1.95583). Post-switch, this logic inverts: EUR is native, BGN must be computed by multiplying by 1.95583.

**Scope — must show BGN alongside EUR in all of:**
- Product cards and product detail pages (`snippets/price.liquid`)
- Cart page (`sections/main-cart-items.liquid`, `sections/main-cart-footer.liquid`)
- Cart drawer (`snippets/cart-drawer.liquid`)
- Savings/discount badges (currently show `€X.XX / Y.YY лв` — formula reverses)
- Order confirmation email template
- Shipping confirmation email template
- Order edited email template

**What changes:** Replace `| divided_by: 1.95583` with `| times: 1.95583` everywhere BGN is derived. EUR display becomes native Shopify formatting (no manual math needed).

**Dependency:** Must be done as part of or immediately after the EUR currency switch — not after, since the existing manual computation will produce wrong prices the moment the store currency flips to EUR.
