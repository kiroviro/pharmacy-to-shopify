# Design: Bulgarian Blog Post — Spring Cold/Flu for Children

**Date:** 2026-03-26
**Status:** Approved

## Overview

Create a Bulgarian-language blog post for viapharma.us targeted at parents dealing with spring colds or flu in children. The post is warm and empathetic (parent-to-parent tone), covers four doctor-prescribed products with linked product pages, and includes a medical disclaimer. A reusable Python script publishes it via the Shopify API.

## Deliverables

1. `scripts/create_blog_post.py` — Shopify API publisher script
2. `content/blog/spring-cold-2026.html` — Bulgarian blog post body (HTML)

## Script Design (`scripts/create_blog_post.py`)

**CLI usage:**
```bash
python scripts/create_blog_post.py content/blog/spring-cold-2026.html [--blog "Здравни съвети"] [--dry-run]
```

**Arguments:**
- Positional: path to HTML content file (required)
- `--blog`: blog title to publish under (default: "Здравни съвети")
- `--dry-run`: print article metadata + first 200 chars of body, skip the POST

**Flow (five steps in order):**
1. Load credentials from `.env` (`SHOPIFY_SHOP_URL` + `SHOPIFY_ACCESS_TOKEN`) using `python-dotenv`. Use direct `requests` calls (not `ShopifyAPIClient`) — this script is standalone and doesn't need the shared client's retry/GraphQL machinery.
2. Read the HTML file (`encoding="utf-8"`). On `FileNotFoundError`: print a clear message ("File not found: <path>") and `sys.exit(1)`
3. Find or create the blog via GET `/blogs.json` → POST if no blog with matching title
4. Duplicate guard: GET `/blogs/{id}/articles.json` — iterate all returned articles and compare `title` case-insensitively (client-side); if a match is found, print an error and `sys.exit(1)`. Note: the Shopify REST API does not support a `?title=` filter; filtering must be done locally. For this use case (new blog, <250 articles expected) a single page is sufficient — pagination is out of scope.
5. Publish article via POST `/blogs/{id}/articles.json` (skipped if `--dry-run`)

**Article metadata (hardcoded in script):**
- `title`: "Пролетна настинка при деца: какво препоръча нашият лекар"
- `author`: "Виафарма"
- `tags`: "настинка, грип, деца, пролет, ибупром, назик, ноктитус, регулат"
- `published`: true (no `published_at` — Shopify defaults to now)

**Error handling contract:**
- All failures (403 scope error, network error, Shopify API `errors` in response body, file not found) must print a human-readable message and call `sys.exit(1)`
- On 403: print "Missing write_content scope. Add it in Shopify Admin → Apps → [app] → Configuration → Admin API access scopes, then regenerate the token."
- On success: print the published article URL

**Prerequisite:** Shopify access token must have `write_content` + `read_content` scopes (see Token Scope Requirement section).

**Reuse pattern:** Pass a different HTML file path for future posts. Use `--blog` to target a different blog (e.g. "Промоции").

## Content File Design (`content/blog/spring-cold-2026.html`)

`content/blog/` is a new directory (does not exist yet — create with `mkdir -p content/blog/`). Plain HTML body (no `<html>`/`<head>`) — Shopify renders this inside the article template. File must be saved as UTF-8.

**Structure:**
1. **Warm opening** — empathetic parent-to-parent intro: "Като родители, всички сме минавали през онези неспокойни нощи когато детето ни е болно..." Sets tone, establishes relatability.
2. **Context paragraph** — пролетна настинка/грип при деца: типични симптоми, кога да потърсите лекар (не заменя лекарска консултация).
3. **Four product sections** (each as `<h2>` with linked product name → viapharma.us):
   - **[Ибупром Синус](https://viapharma.us/products/ibuprom-sinus-tabletki-200mg-30mg-h-12)** — болкоуспокояващ + деконгестант; при главоболие, запушен нос, температура
   - **[Назик назален спрей за деца](https://viapharma.us/products/nazik-nazalen-sprej-za-deca-10ml)** — назална конгестия; 3–4 пъти на ден; бързо облекчение
   - **[Ноктитус сироп](https://viapharma.us/products/noktitus-sirop-za-suha-kaslica-200-ml)** — суха кашлица; дозировка на всеки 5–6 часа
   - **[Регулатпро Био](https://viapharma.us/products/regulatpro-bio-solucio-350ml)** — пробиотик; защо е важен при вирусно заболяване (имунна подкрепа, чревен баланс)
4. **Disclaimer** — "Тази статия е с информационна цел. Консултирайте се с Вашия лекар или фармацевт преди употреба на всяко лекарство."
5. **Closing CTA** — "Всички препоръчани продукти ще намерите в нашата онлайн аптека [viapharma.us](https://viapharma.us)."

## Product URLs (confirmed live on viapharma.us)

| Product | Handle |
|---|---|
| Ибупром Синус х12 | `ibuprom-sinus-tabletki-200mg-30mg-h-12` |
| Назик спрей за деца | `nazik-nazalen-sprej-za-deca-10ml` |
| Ноктитус сироп 200мл | `noktitus-sirop-za-suha-kaslica-200-ml` |
| Регулатпро Био 350мл | `regulatpro-bio-solucio-350ml` |

## Shopify Blog

- Blog name: "Здравни съвети" (created by script if it doesn't exist)
- Article template: default (`article.json`) — already in theme

## Token Scope Requirement

Current token (`SHOPIFY_ACCESS_TOKEN` in `.env`) only has product/theme scopes. Before running the script, add `write_content` (and `read_content`) in Shopify Admin → Apps → Develop apps → [app] → Configuration → Admin API access scopes. Regenerate the token after saving.

## Out of Scope

- SEO meta title/description (can be set manually in Shopify Admin after publishing)
- Featured image (can be added manually)
- Scheduling (post publishes immediately)
