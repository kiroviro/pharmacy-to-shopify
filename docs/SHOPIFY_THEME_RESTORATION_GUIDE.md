# Shopify Theme Restoration Guide

**Theme:** Meka v5.0.3 by Muup (Mediva preset)
**Store:** viapharma-us (VIA Apteka -- Bulgarian online pharmacy)
**Export date:** 09 Feb 2026
**Export path:** `theme_export__viapharma-us-mediva__09FEB2026-1120pm/`

---

## How to Use This Guide

After updating the Meka/Mediva theme to a new version:

1. Work through each phase top-to-bottom
2. Check off each step as you complete it
3. Phase 1 is **critical** -- the store breaks without these
4. Phases 2-3 can be done incrementally
5. Keep the theme export folder as your reference backup

---

## Phase 1: Critical (Store Breaks Without These)

### 1.1 Restore Custom Assets

These files don't exist in the stock theme and must be re-uploaded to `assets/`:

- [ ] **Upload `custom-header-compact.css`** (1,958 B)
  - Header compaction overrides for mobile + desktop
  - Reduces header padding, logo size (85px mobile), announcement bar font/padding
  - Overrides collection banner min-height
  - Referenced by: `sections/header.liquid` line 1, `sections/announcement-bar.liquid` line 1

- [ ] **Upload `component-sidebar-mega-menu.css`** (8,241 B)
  - Custom sidebar mega menu styles
  - 260px wide sidebar panel, dark background, flyout max 740px
  - Multi-column subcategory grid (3 cols default, 4 on >= 1400px)
  - Referenced by: `snippets/header-sidebar-mega-menu.liquid`

- [ ] **Upload `sidebar-mega-menu.js`** (4,695 B)
  - Web component `<sidebar-mega-menu>` powering sidebar navigation
  - Toggle open/close, L1 hover with 150ms debounce, touch support
  - Auto-activates first L1 item on open
  - Referenced by: `sections/header.liquid` line 725

- [ ] **Upload `sparkle.gif`** (179 KB) -- decorative animated sparkle
- [ ] **Upload `cursor.svg`** (351 B) -- custom close cursor

### 1.2 Restore Custom Sections

- [ ] **Copy `sections/brands-list.liquid`** -- entirely custom
  - Displays all collections with handle containing `brand-` in a grid
  - Default heading: "Всички марки" (All brands)
  - Used by: `templates/page.brands.json`

### 1.3 Restore Modified Sections

These are Mediva sections with store-specific changes. After a theme update, **diff the new version against your backup** and re-apply the changes:

- [ ] **`sections/header.liquid`** -- HEAVILY MODIFIED
  - Line 1: Add `{{ 'custom-header-compact.css' | asset_url | stylesheet_tag }}`
  - Lines 455-508: Replace original mega-menu rendering with `{% render 'header-sidebar-mega-menu' %}`
  - Lines 38-50: Transparent header logic using `pages_transparent_header` block
  - Lines 727-870: Extended `StickyHeader` JS class with transparent header support (`header-at-top` class toggle, negative margin-bottom overlay)
  - Lines 692-706: Round borders with SVG corner decoration
  - Line 725: Add `<script src="{{ 'sidebar-mega-menu.js' | asset_url }}" defer="defer"></script>`
  - Schema additions: `link_list` block, `item_icon` block, `pages_transparent_header` block, `menu_font_weight`, `show_shadow`, `round_borders`, `mega_menu_image`, `image_ratio`, `drawer_product` settings

- [ ] **`sections/footer.liquid`** -- MODIFIED
  - Lines 72-99: Footer logo section with width control
  - Lines 43-53: Background image block support
  - Schema additions: `image` block, `background_image` block, `social_icon_style`, `newsletter_enable_top`, `social_label`, `heading_size`, `footer_subtext`, `policy_padding_top/bottom`
  - **BUG**: Line 332 has debug text `sdfasd` -- remove it

- [ ] **`sections/main-product.liquid`** -- MODIFIED
  - Line 38: Custom breadcrumbs CSS (`.breadcrumbs__item:last-child { color: rgb(var(--color-accent)); }`)
  - Lines 70-80: Breadcrumbs block rendering with Bulgarian default "Начало"
  - Lines 242-262: Countdown timer block rendering `countdown-bar` snippet
  - Lines 320-381: Delivery date block with `delivery_days * 86400` calculation
  - Lines 486-540: Two-column feature display with icons
  - Schema: `breadcrumbs` block with Bulgarian defaults, `countdown` block, `delivery_date` block, `features` block, `icon_with_text` block

- [ ] **`sections/main-article.liquid`** -- MODIFIED
  - Lines 2-8: Custom breadcrumb CSS + accent color override
  - Line 30: Hardcoded Bulgarian breadcrumb "Начало"
  - Lines 60-67: Social sharing with Facebook/Twitter direct links
  - Lines 16-22: Sticky title bar with reading progress indicator

- [ ] **`sections/announcement-bar.liquid`** -- MODIFIED
  - Line 1: Loads `custom-header-compact.css`
  - Lines 45-49: Renders `announcement-navigation` snippet
  - Lines 41-43: Social icons toggle option

- [ ] **`sections/main-collection-product-grid.liquid`** -- MODIFIED
  - Lines 18-100+: Subcollection navigation block (menu-based, two levels)
  - Lines 20-24: Up to 2 promo blocks interspersed in product grid
  - Configurable overlay opacity for subcollection images

### 1.4 Restore Custom Snippets

- [ ] **Copy `snippets/header-sidebar-mega-menu.liquid`** -- entirely custom (124 lines)
  - Sidebar mega menu with L1/L2/L3 navigation
  - Hardcoded Bulgarian: "ВСИЧКИ ПРОДУКТИ", "Категории", "Затвори меню", "Навигация по категории", "Виж всички"
  - Dependencies: `sidebar-mega-menu.js`, `component-sidebar-mega-menu.css`

- [ ] **Copy `snippets/breadcrumbs.liquid`** -- entirely custom (92 lines)
  - Breadcrumb with previous/next product navigation within collection
  - Dependencies: `component-breadcrumb.css`, `icon-arrow-short` snippet

- [ ] **Copy `snippets/countdown-bar.liquid`** -- entirely custom (55 lines)
  - Countdown timer web component
  - Dependencies: `countdown.js`

- [ ] **Copy `snippets/announcement-navigation.liquid`** -- entirely custom (24 lines)
  - Inline navigation menu for the announcement bar area

### 1.5 Restore Modified Snippets

- [ ] **`snippets/card-product.liquid`** -- MODIFIED
  - Lines 106-123, 313-330: Tag-based badge system matching `settings.badge_names`
  - Lines 128-151, 335-358: Sale badge with 3 styles (text/dollar/percentage)
  - Lines 226-234: Compare checkbox integration
  - Custom badge color settings: `blog_color_text/bg`, `sold_color_text/bg`, `sale_color_text/bg`

- [ ] **`snippets/product-badge.liquid`** -- CUSTOM/MODIFIED (70 lines)
  - Same tag-matching badge logic for product detail pages

- [ ] **`snippets/facets.liquid`** -- MODIFIED
  - Lines 681-703: Custom radio-based sort dropdown (replaces native `<select>`)
  - Lines 629-661: Grid/list view toggle with SVG icons
  - Lines 55-68: Custom filter label translation mapping
  - Settings: `sorting_color_scheme`, `sorting_inside_color_scheme`, `filter_color_scheme`, navigation label

- [ ] **`snippets/price.liquid`** -- MODIFIED
  - Line 28: Discount percentage calculation
  - Lines 64-68: Discount badge rendering (e.g., "25% Off")

- [ ] **`snippets/header-drawer.liquid`** -- MODIFIED
  - Lines 39-138: Additional drawer menu via `link_list` block (3 levels deep)
  - Lines 211-225: Featured product card inside mobile drawer

### 1.6 Restore All 11 Color Schemes

In **Theme Settings > Colors**, restore the complete brand palette:

| Scheme | Background | Text | Accent | Primary Button | Purpose |
|--------|-----------|------|--------|---------------|---------|
| 1 | `#ffffff` | `#0a3244` | `#1da1d4` | `#1da1d4` (blue) | Default/white |
| 2 | `#ebf6fb` | `#0a3244` | `#1da1d4` | `#1da1d4` (blue) | Light blue bg |
| 3 | `#0a3244` | `#ffffff` | `#ffffff` | `#1da1d4` (blue) | Dark navy bg |
| 4 | `#0a3244` | `#ffffff` | `#1da1d4` | `#ffffff` (white) | Dark, inverted buttons |
| 5 | `#ffffff` | `#0a3244` | `#1da1d4` | `#0a3244` (dark) | White, dark primary |
| 6 | `#ebf6fb` | `#ffffff` | `#1da1d4` | `#1da1d4` (blue) | Light blue overlay |
| 7 | `#0c7eaa` | `#ffffff` | `#7ec636` | `#7ec636` (green) | Medium blue, green buttons |
| 8 | `#ebf6fb` | `#0a3244` | `#1da1d4` | `#1da1d4` (blue) | Light blue, dark input borders (`#0a3244`) |
| 9-11 | `#f4f9f0` | `#0a3244` | `#7ec636` | `#7ec636` (green) | Mint green bg (identical x3) |

**Full color values for each scheme** -- see `config/settings_data.json` in the theme export for all 18 properties per scheme (background, text, text_secondary, accent_color, button, button_label, button_hover, button_label_hover, button_2, button_label_2, button_2_hover, button_label_2_hover, secondary_button_label, slider_btn, slider_btn_label, slider_btn_hover, slider_btn_label_hover, input_border_color).

### 1.7 Restore Logo and Branding

- [ ] Upload `logo-VIA-apteka.png` to Shopify Files
- [ ] **Theme Settings > Logo**: Set logo to `logo-VIA-apteka.png`
- [ ] **Theme Settings > Logo**: Set transparent logo to same file
- [ ] **Theme Settings > Logo**: Set width to `100` px

### 1.8 Restore Bulgarian Locale Files

- [ ] **Copy `locales/bg-BG.json`** (613 lines) -- full Bulgarian translation
  - All UI strings: cart, products, facets, compare, newsletter, customer account, gift cards
  - ~11 strings still in English that should be translated (see Phase 3)
- [ ] **Copy `locales/bg.json`** (46 lines) -- sorting/facets supplement
  - Sorting labels: "Най-продавани", "Азбучен ред", "Цена", "Дата"

### 1.9 Restore Homepage (index.json)

- [ ] **Copy `templates/index.json`** or reconfigure 14 sections in order:
  1. `image-banner` -- Hero: "Вашата онлайн аптека", scheme-3, with calendula image
  2. `collection-list` -- 6 categories: lechenie-i-zdrave, kozmetika, mayka-i-dete, meditsinski-izdeliya, sport, zdravoslovno-hranene
  3. `featured-collection` -- "Грип и настинка" collection, 8 products, 4 cols
  4. `multicolumn` -- 2 promo banners (vitamins + cosmetics), scheme-4
  5. `scrolling-banner` -- **DISABLED** -- "Грижа за Здравето"
  6. `product-slider` -- 2 baby product slides, scheme-7
  7. `featured-product` -- BIODERMA ABCDerm with custom description
  8. `collection-tabs` -- "Популярни продукти" with 3 tabs (vitamins, face care, hair care)
  9. `collage` -- **DISABLED** -- 3 collection image blocks
  10. `multicolumn` -- "Марки" brand showcase (10 brands with product counts)
  11. `image-banner` -- **DISABLED** -- "Над 9 000 продукта"
  12. `product-comparison` -- "Сравни и избери"
  13. `testimonials` -- **DISABLED** -- 3 Bulgarian customer reviews
  14. `featured-blog` -- "Здравни съвети" health tips

### 1.10 Restore Header Group

- [ ] **Copy `sections/header-group.json`** or reconfigure:
  - **Announcement bar**: scheme-4, 2 messages (free delivery over 35 euro, 11k+ products), auto-rotate 5s
  - **Header**: logo middle-left, `categories-menu`, mega menu type, font weight 400, always sticky, scheme-2 background, 4px padding, no shadow/separator/round-borders

### 1.11 Restore Footer Group

- [ ] **Copy `sections/footer-group.json`** or reconfigure:
  - scheme-3 (dark navy), h6 headings
  - 3 link lists: "Категории" (footer-categories), "Популярни марки" (footer-brands), "Информация" (footer)
  - Social: "Последвайте ни" label
  - Newsletter: "Бюлетин" title, Bulgarian description
  - Subtext: "ViaPharma -- Вашата онлайн аптека..."
  - Payment icons enabled, policy links shown

### 1.12 Restore App Embed

- [ ] Install **BGN-EUR Dual Display** app
- [ ] Enable its app embed block in theme settings

---

## Phase 2: Functional (Features/Behavior Changes)

### 2.1 Restore Product Template (product.json)

- [ ] **Copy `templates/product.json`** or reconfigure 9 sections:
  1. `main-product` with 10 blocks:
     - Breadcrumbs: "Начало", scheme-8, collection enabled
     - Title: h2
     - Price: medium, accent color
     - Inventory bar: base 100, threshold 9, green `#2cb683` / red `#ff353c`
     - Countdown: "Побързайте! Офертата изтича след", Bulgarian labels (Дни/Часа/Минути/Секунди), scheme-5, cycle mode
     - Variant picker: button type, square swatch, outlined
     - Buy buttons: dynamic checkout, gift card recipient, scheme-8 quantity
     - Description: small text
     - Complementary: "Може да купите и тези продукти", 10 products
     - Delivery date: "Очаквана дата на доставка:", "Обикновено готов за 2-3 дни.", max 8 days
  2. `compare-product` -- "Производител", "Тип продукт", "Описание"
  3. `multicolumn` -- **DISABLED** promo banners
  4. `scrolling-banner` -- **DISABLED**
  5. `image-with-text` -- **DISABLED** "За нас" about section
  6. `help-and-feedback` -- **DISABLED** 5 FAQ + 3 testimonials (Bulgarian)
  7. `related-products` -- "Подобни продукти", 10 products, 4 cols, scheme-2
  8. `sticky-add-to-cart` -- right side, width 56, weight 600
  9. `multicolumn` -- Trust bar: 4 icons (original medicines, support, fast delivery, affordable healthcare) with custom SVGs

### 2.2 Restore Collection Template (collection.json)

- [ ] **Copy `templates/collection.json`** or reconfigure 6 sections:
  1. `main-collection-banner` -- scheme-3, breadcrumbs top, h3, description hidden, small, 40% overlay
  2. `main-collection-product-grid` -- 10/page, 3 cols, scheme-8, subcollections (scheme-3, 5 cols), 2 promo cards, vertical filtering
  3. `image-banner` -- **DISABLED** collection discount banner
  4. `help-and-feedback` -- **DISABLED** FAQ/testimonials
  5. `rich-text` -- **DISABLED** collection description
  6. `multicolumn` -- Trust bar (same 4 icons)

### 2.3 Restore Custom Page Templates

- [ ] **Copy `templates/page.about.json`** -- About page: our story, wellness vision, team (5 members), testimonials, blog
- [ ] **Copy `templates/page.contact.json`** -- Contact: "София, България", "Пон-Пет 9:00-18:00", contact form "Пишете ни"
- [ ] **Copy `templates/page.faq.json`** -- FAQ: 5 sections (Ordering, Product, Payment, Shipping, Returns), 15 Q&A pairs, all Bulgarian
- [ ] **Copy `templates/page.brands.json`** -- Uses custom `brands-list` section
- [ ] **Copy `templates/page.gift-page.json`** -- Gift page with collection and gift card product

### 2.4 Restore Other Templates

- [ ] **Copy `templates/cart.json`** -- "Безплатна доставка за поръчки над 100 лв!", promoted collection `gummies`
- [ ] **Copy `templates/search.json`** -- Vertical filtering, scheme-8 grid, scheme-3 sorting, "ПРОЧЕТИ ПОВЕЧЕ"
- [ ] **Copy `templates/blog.json`** -- Newsletter "Абонирайте се за нашия бюлетин", trust bar
- [ ] **Copy `templates/article.json`** -- Navigation progress line, "Сподели"
- [ ] **Copy `templates/article.article-template-2.json`** -- Author block variant
- [ ] **Copy `templates/list-collections.json`** -- "Всички категории", dark overlay, "ПАЗАРУВАЙ СЕГА"
- [ ] **Copy `templates/password.json`** -- "Очаквайте скоро", countdown, Bulgarian labels

### 2.5 Restore Theme Settings (Non-Color)

- [ ] **Badges**: Sale bg `#7EC636` (green), Sold bg `#CC3333` (bright red), Blog bg `#1DA1D4` (blue)
- [ ] **Search**: `show_search_filter: false` (disabled)
- [ ] **Cart**: `currency_code_enabled: false`, drawer bg `#0A3244`
- [ ] **Social links**: Update from Shopify demo to actual store profiles

### 2.6 Restore Featured Group

- [ ] **Copy `sections/featured-group.json`** or reconfigure:
  - Scroll-to-top: round, arrow, white on `#088599`, hover `#067182`
  - Notification: **DISABLED** -- "Отстъпка за добре дошли 10%"
  - Social share: **DISABLED** -- LinkedIn/Facebook/Twitter
  - Promo popup: **DISABLED** -- "Добре дошли във ВИА Фарма!", 10% discount, 15s timeout

---

## Phase 3: Cosmetic (Visual Tweaks, Minor Styling)

### 3.1 Restore Simple Page Templates

- [ ] **Copy `templates/page.delivery.json`** -- Simple main-page
- [ ] **Copy `templates/page.support.json`** -- text_color secondary
- [ ] **Copy `templates/page.returns-exchanges.json`** -- "Връщане и замяна", secondary text
- [ ] **Copy `templates/page.terms-of-service.json`** -- Simple main-page, secondary text
- [ ] **Copy `templates/page.shipping-information.json`** -- Simple main-page, secondary text

### 3.2 Restore Minor Templates

- [ ] **Copy `templates/404.json`** -- "Моля, върнете се на началната страница."
- [ ] **Copy `templates/customers/login.json`** -- scheme-2 background, custom padding
- [ ] Copy remaining customer templates (register, account, addresses, order, activate_account, reset_password) -- all default settings

### 3.3 Fix Untranslated Strings in bg-BG.json

The following are still in English and should be translated to Bulgarian:

| Key | Current (English) | Suggested Bulgarian |
|-----|-------------------|-------------------|
| `sections.cart.description` | "Free shipping on all orders above $50!" | "Безплатна доставка за поръчки над 35€!" |
| `sections.cart.remove` | "Remove" | "Премахни" |
| `sections.cart.estimated_subtotal` | "Sub-total" | "Междинна сума" |
| `sections.cart.login.link_title` | "Login to checkout faster" | "Влезте за по-бързо плащане" |
| `blogs.article.comment_form_description` | "All comments are moderated..." | "Всички коментари се преглеждат..." |
| `templates.search.articles` | "Articles" | "Статии" |
| `localization.country_results_count` | "{{ count }} countries/regions found" | "Намерени {{ count }} държави/региони" |
| `customer.order.counter_title` | "Total products" | "Общо продукти" |
| `customer_accounts.orders.order_list.pagination.next` | "NEXT" | "СЛЕДВАЩ" |
| `customer_accounts.orders.order_list.pagination.previous` | "PREV" | "ПРЕДИШЕН" |
| `customer_accounts.orders.order_list.sort_by` | "Sort By" | "Сортирай по" |

### 3.4 Fix Bug

- [ ] **`sections/footer.liquid` line 332**: Remove debug text `sdfasd`

---

## Settings & Configuration Reference

### Theme Settings Summary (settings_data.json)

| Category | Status |
|----------|--------|
| Typography | Default (Instrument Sans) |
| Layout | Default (1540px) |
| Animations | Default (reveal on scroll) |
| Buttons | Default (uppercase, 700 weight, 10px radius) |
| Variant pills | Default |
| Inputs | Default (10px radius) |
| Product cards | Default |
| Collection cards | Default |
| Blog cards | Default |
| Content containers | Default |
| Media | Default |
| Popups/Drawers | Default |
| **Color schemes** | **FULLY CUSTOMIZED** (11 schemes) |
| **Badges** | **3 colors changed** |
| **Search** | **Filter disabled** |
| **Cart** | **Drawer bg changed, currency code disabled** |
| **Logo** | **Custom VIA Apteka logo, 100px** |

### Required Shopify Resources

**Menus (must exist in Navigation):**
- `categories-menu` -- main header navigation
- `footer-categories` -- footer column 1
- `footer-brands` -- footer column 2
- `footer` -- footer column 3 (information)

**Collections referenced across templates:**
- Categories: `lechenie-i-zdrave`, `kozmetika`, `mayka-i-dete`, `meditsinski-izdeliya-i-konsumativi`, `sport`, `zdravoslovno-hranene-chayove-i-bilki`
- Featured: `grip-i-nastinka`, `vitamini-i-minerali`, `grizha-za-litse`, `grizha-za-kosa`, `gummies`
- Brands: `brand-boiron`, `brand-bioderma`, `brand-avene`, `brand-nivea`, `brand-garnier`, `brand-vichy`, `brand-solgar`, `brand-eucerin`, `brand-uriage`, `brand-la-roche-posay`

**Products referenced:**
- `pansoral-za-parvi-zabki-15ml`
- `wellkid-peppa-pig-zhelirani-tabletki-multivitamini-s-vkus-na-yagoda-za-detsa-h30-vitabiotics`
- `bioderma-abc-derm-hidratant-200ml`

**Shop images (must be in Shopify Files):**
- `logo-VIA-apteka.png`
- `calendula_flowers_vitamin_E_capsules_png.png`
- `promo-vitamini_bd0e0d7c-a9ec-4c30-a284-6ba2861e34df.png`
- `promo-kozmetika_a0db6acb-a931-4fc1-a1a0-62495794ee95.png`
- `slider-pansoral-baby.webp`
- `slider-wellkid-peppa-pig.webp`
- `collection-grizha-za-litse.png`
- `collection-mayka-i-dete.webp`
- `collection-meditsinski-izdeliya.png`
- `Promo_card_2.png`, `Promo_card_11.png`
- `Discount_banner.png`
- `icon-original-medicines.svg`
- `icon-support.svg`
- `icon-fast-delivery.svg`
- `icon-affordable-healthcare.svg`

**Blog referenced:**
- `добре-дошли-в-света-на-нежната-грижа-за-вашето-бебе-🌸👶`

**App required:**
- BGN-EUR Dual Display (currency conversion)

---

## Quick Restoration Strategy

For the **fastest possible restoration**, rather than manually reconfiguring each setting:

1. **After theme update**, use Shopify CLI to pull the updated theme:
   ```bash
   shopify theme pull --store viapharma-us
   ```

2. **Copy JSON templates directly** from the backup export folder to the new theme:
   - All `templates/*.json` files
   - `sections/header-group.json`, `sections/footer-group.json`, `sections/featured-group.json`
   - `config/settings_data.json` (WARNING: may need manual merge if schema changed)

3. **Copy custom files** that won't exist in the new theme:
   - `sections/brands-list.liquid`
   - `snippets/header-sidebar-mega-menu.liquid`
   - `snippets/breadcrumbs.liquid`
   - `snippets/countdown-bar.liquid`
   - `snippets/announcement-navigation.liquid`
   - `assets/custom-header-compact.css`
   - `assets/component-sidebar-mega-menu.css`
   - `assets/sidebar-mega-menu.js`
   - `assets/sparkle.gif`, `assets/cursor.svg`
   - `locales/bg-BG.json`, `locales/bg.json`

4. **Diff and merge modified files** (these exist in both old and new themes):
   - `sections/header.liquid`
   - `sections/footer.liquid`
   - `sections/main-product.liquid`
   - `sections/main-article.liquid`
   - `sections/announcement-bar.liquid`
   - `sections/main-collection-product-grid.liquid`
   - `snippets/card-product.liquid`
   - `snippets/product-badge.liquid`
   - `snippets/facets.liquid`
   - `snippets/price.liquid`
   - `snippets/header-drawer.liquid`

5. **Push the merged theme**:
   ```bash
   shopify theme push --store viapharma-us
   ```

6. **Verify** by checking homepage, product page, collection page, and all custom pages in the browser.

---

## Files That Need NO Restoration

The following are **stock Mediva files** with no store-specific changes:

- `layout/theme.liquid` -- stock, no tracking scripts or custom code
- `layout/password.liquid` -- stock
- `config/settings_schema.json` -- stock Meka v5.0.3 schema
- All standard Mediva sections (before-after, card-slider, collection-tabs, compare-drawer-product, compare-product, featured-promotion, help-and-feedback, etc.)
- All standard snippets (article-card, buy-buttons, card-collection, icons, meta-tags, pagination, etc.)
- All non-Bulgarian locale files (shipped with theme)
- `templates/gift_card.liquid` -- stock Liquid template
