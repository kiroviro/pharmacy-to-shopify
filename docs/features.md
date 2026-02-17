# Features

## Extraction
- **Structured data parsing** -- JSON-LD, HTML content, breadcrumb navigation
- **Complete product data** -- title, brand, SKU, barcode (EAN), price (BGN + EUR), categories, descriptions, images, application form, target audience
- **Content sections** -- product details, composition, usage instructions, contraindications
- **Brand matching** -- 450+ known pharmacy brands
- **Image URL resolution** -- rewrites vendor `uploads/` paths to CDN `product_view_default/` for higher quality images that work for all products, with HEAD-request validation and automatic fallback
- **High compliance** with Shopify product specification (validated via `src/extraction/validator.py`)

## Shopify Integration
- **56-column CSV format** -- Shopify product import template with 2 custom metafields for storefront filters
- **Original image URLs** -- Shopify fetches and caches images from source during import
- **Sidebar filters** -- Brand (Vendor), Product Type (L1 category), Application Form, and Target Audience as storefront filters with Bulgarian labels
- **Smart collections** -- breadcrumb categories exported as tags for automatic collection rules
- **Dual currency** -- BGN (primary) and EUR prices exported to CSV for Bulgaria's Euro transition
- **Clean data** -- source site references automatically stripped from text fields

## Workflow Tools
- **Demo script** -- interactive showcase with sample HTML (no setup required)
- **Bulk extraction** with progress tracking and resume capability
- **Selective brand export** -- import by brand, top-N, or exclude specific brands
- **Tag cleanup** -- normalize casing, remove promotional tags, infer missing categories
- **Collection creation** -- automated Shopify collection setup via Admin API
- **Navigation menus** -- automated Shopify menu creation from category hierarchy
- **Filter configuration** -- create custom metafield definitions and translate theme filter labels to Bulgarian via Admin API
- **Theme customization** -- modify theme locale strings and assets via Admin API (e.g., storefront labels, tax/shipping messages)
- **Filter label translation** -- patched `snippets/facets.liquid` in the Mediva theme to use locale-based translations for sidebar filter labels (Availability -> Наличност, Price -> Цена, Vendor -> Марка, Product Type -> Категория)

## Development & Deployment
- **Docker support** -- multi-stage Dockerfile and docker-compose with service profiles
- **Pre-commit hooks** -- automatic linting, formatting, and secret detection
- **CI/CD pipeline** -- GitHub Actions with lint and test jobs (Python 3.9, 3.11, 3.13)
- **Environment templates** -- `.env.example` for secure credential management
- **GitHub templates** -- bug reports, feature requests, and pull request templates
- **Comprehensive documentation** -- architecture, workflows, configuration guides

## Required Shopify Apps

| App | Purpose | Cost |
|-----|---------|------|
| **Shopify Search & Discovery** | Collection sidebar filters + product recommendations | Free |

The Mediva theme (by MUUP, preset of Meka) depends on Search & Discovery for:
- **Collection filters** -- the sidebar with Availability, Price, Vendor, Product Type, and custom metafield filters
- **Product recommendations** -- the "Подобни продукти" (Related Products) section on product pages

Filters must be enabled manually in the app: **Apps -> Search & Discovery -> Filters tab -> Add filter** (Product vendor, Product type, custom.application_form, custom.target_audience).
