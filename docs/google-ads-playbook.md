# ViaPharma Google Ads Playbook — Golden Template

**Account:** 825-619-0101 (ViaPharma US, EUR)
**Manager account:** 966-252-5245
**Last audit:** 2026-04-08 | Score: 70/100 (Optmyzr / PPC Audit Tool)
**Target score:** 90+/100

This document is the authoritative reference for all Google Ads decisions on this account.
Every campaign change must align with the standards defined here.

---

## Account-Level Standards

### Budget Targets
| Metric | Current | Target |
|--------|---------|--------|
| Total daily budget | €10/day | Scale with ROAS — minimum €10/day |
| Impression share lost to budget (Search) | DSA 95%, PMax 43% | < 20% per campaign |
| Budget split | DSA 50% / PMax 50% | Adjust based on per-campaign ROAS |

**Rule:** If IS lost to budget > 20% on a profitable campaign (ROAS > break-even), increase budget.
Break-even ROAS at 5.3% gross margin = **18.87x**. Actual ROAS target: **20x+**.

### Bidding
- DSA: Manual CPC (€0.50 max). Graduate to Target ROAS only after 40+ real purchase conversions.
- PMax: Maximize Conversion Value (no tROAS until sufficient data).
- Never use Maximize Clicks — it optimizes for traffic, not revenue.

### Conversion Tracking (Critical — verify before any campaign change)
- **Only ONE Primary conversion action:** `Google Shopping App Purchase` (order value passed dynamically)
- All other events (page_view, search, view_item, add_to_cart, begin_checkout, add_payment_info) must be **Secondary**
- Attribution model: **Data-driven** (not Last Click)
- Auto-tagging: must be **ON** (verify in Account Settings)
- Watch for conversion rate > 100% — this signals double-counting (seen: 105.98% conv rate = tracking bug)

### Account-Level Assets (Required)
- [ ] Account-level sitelinks (currently missing — score 0)
  - These show with ANY ad in the account; add the 6 DSA sitelinks at account level too

---

## Campaign Standards

### Required for Every Campaign
1. **Specific location target:** Bulgaria (verified ✓)
2. **Language:** Bulgarian + All Languages (Chrome in English is common for Bulgarian users)
3. **Location option:** "Presence" only (not "Presence or interest")
4. **Ad schedule:** Set per campaign — no "always on" for PMax (currently missing — score 50)
5. **Negative keywords:** Minimum 50 negatives before launch; weekly review of search terms
6. **Sitelinks:** Minimum 4 per campaign (currently: DSA has 6 ✓, PMax has 8 ✓)

### Impression Share Monitoring
- Check weekly: Campaigns → Columns → add "Search IS lost (Budget)" and "Search IS lost (Rank)"
- Alert threshold: IS lost to budget > 20% on any campaign running > 7 days

---

## DSA Campaign (ID: 23713866882)

### Ad Group Structure
- **Target:** ≤ 20 active keywords per ad group (currently 32 — score 0, needs fixing)
- **Action:** Split "Ad group 1" into themed groups by URL category (see Phase 2 in `google-ads-dsa-optimization-checklist.md`)

### RSA (Responsive Search Ad) Standards
| Requirement | Target | Current |
|------------|--------|---------|
| Ad strength | Good or Excellent | Poor (score 0) |
| Headlines | ≥ 10 (max 15) | ✓ |
| Headline character count | ≥ 20 chars each | 2 headlines < 20 chars ("Витамини и Добавки" = 18, "Козметика и Здраве" = 18) |
| Descriptions | ≥ 4 (max 5) | ✓ |
| Description character count | ≥ 60 chars each | ✓ |
| No duplicate headlines | 0 duplicates | ✓ |
| No duplicate descriptions | 0 duplicates | ✓ |
| Pinned assets | Never pin single option | ✓ |

**Fix needed:** Expand short headlines to ≥ 20 characters:
- "Витамини и Добавки" (18) → "Витамини и Хранителни Добавки" or similar
- "Козметика и Здраве" (18) → "Козметика и Здравни Продукти" or similar

### Final URL
- **Must use https://** (currently using http:// — score 0, immediate fix required)
- Target landing page: `https://viapharma.us` (not `http://viapharma.us`)

### Landing Page Quality (score 0 — most impactful fix)
- 100% of keywords have **below average** Landing Page Score
- Root cause: landing pages not optimized for search intent of matched queries
- Actions:
  1. Review Google Ads → Keywords → Quality Score columns
  2. Ensure product/collection pages have: keyword in H1, descriptive meta, fast load time
  3. DSA URL exclusions: /pages/, /blogs/, /cart, /policies/, /account, /search (already set ✓)
  4. Consider URL inclusions to focus only on high-quality product pages

### Quality Score Targets
| Component | Current | Target |
|-----------|---------|--------|
| Overall Quality Score | 3-7 (score 50) | 8+ |
| Ad Relevance | Average (score 50) | Above Average |
| Landing Page Experience | Below Average (score 0) | Average or Above |
| Expected CTR | Average (score 50) | Above Average |

### Keywords
- Only 3 of 32 (9%) keywords have received conversions — regularly pause non-converting keywords after 30+ days
- 100% broad match (risky) — add phrase match and exact match for top converting terms
- Review search terms weekly, add negatives from irrelevant queries
- Current negatives: 146 across 2 campaigns (good foundation ✓)

---

## PMax Campaign (ID: 23722367460)

### Asset Group Standards
| Asset Type | Minimum | Target | Current |
|-----------|---------|--------|---------|
| Headlines | 3 | 15 | 11 ✓ (enough for Excellent) |
| Long headlines | 1 | 5 | 2 ✓ |
| Descriptions | 2 | 5 | 4 ✓ |
| Images (landscape 1.91:1) | 1 | 20 | 20 ✓ |
| Images (square 1:1) | 1 | 20 | ✓ |
| Images (portrait 4:5) | 1 | 5 | ✓ |
| Logo | 1 | 1 | 1 ✓ |
| Videos | 1 | 3+ | 1 (vertical only — needs horizontal) |
| Sitelinks | 4 | 8+ | 8 ✓ |
| Target ad strength | Good | Excellent | Average→Excellent (pending) |

### Low-Performance Assets
- 14/42 assets have "Low" performance label (score 66)
- **Action:** After 30+ days of data, replace Low-labeled assets with new creative alternatives
- Keep Good/Best assets, never delete them
- For images: use real product photos, not stock images

### Audience Signals (score 0 — critical gap)
- Currently: "No signals provided"
- **Must add before campaign has run 30 days:** Google needs signals to ramp up faster
- Recommended segments:
  - **Custom intent:** viapharma.us visitors, competitor URLs (galen.bg, benu.bg, sopharma.bg)
  - **In-market:** Health/Vitamins & Supplements, Beauty & Personal Care, Baby & Children's Products
  - **Remarketing:** All website visitors (from Google Ads tag AW-17931842941)

### Ad Schedule
- Currently: no ad schedule (score 50)
- Add schedule targeting peak hours once 30+ days of data collected
- Start with all hours enabled (observe data first), then restrict to high-conversion windows

### Final URL Expansion
- Current setting: Expansion enabled (score 100 ✓)
- Keep this ON — allows Google to test landing pages

---

## Recurring Optimization Workflow

### Daily (automated)
- `scripts/monitor_dsa_campaign.py` runs via launchd at 08:00 UTC+3
- `scripts/dsa_daily_report.py` sends email with ROAS and alerts

### Weekly
1. Review search terms: `python scripts/dsa_search_terms.py --csv ~/Downloads/search_terms.csv`
2. Add new negatives from irrelevant/competitor queries
3. Check impression share: any campaign > 20% IS lost to budget?
4. Review Quality Score in Keywords tab (target: 8+)
5. Check PMax asset performance labels — replace any newly "Low" labeled assets

### Monthly
1. Run full Optmyzr audit at `tools.optmyzr.com/account-dashboard/overview?account=8256190101&type=adwords`
2. Review PPC Audit score — target 90+/100
3. Pause keywords with 0 conversions after 30+ days and significant spend
4. Review audience signal performance in PMax
5. Check if conversion rate is realistic (should be < 5% for e-commerce; if > 10%, check for double-counting)

### Before Any Campaign Change
Checklist (from `feedback_google_ads_setup.md`):
- [ ] Conversion tracking: only Purchase = Primary
- [ ] Auto-tagging ON
- [ ] Final URL: https://
- [ ] Negative keywords added (50+ minimum)
- [ ] Sitelinks added (4+ minimum)
- [ ] Location: Bulgaria, option = Presence
- [ ] Language: Bulgarian + All Languages
- [ ] Budget: conservative start, scale with data

---

## Known Issues (as of 2026-04-08) — Prioritized Fix List

### P0 — Fix This Week
| Issue | Impact | How to Fix |
|-------|--------|-----------|
| DSA final URL uses http:// | Score 0 | Change to https://viapharma.us in ad settings |
| DSA RSA ad strength: Poor | Score 0 | Add 5+ more unique headlines, expand short headlines to 20+ chars |
| PMax: No audience signals | Score 0 | Add custom intent + in-market + remarketing segments |
| Conversion rate 105.98% (>100%) | Data integrity | Audit Goals → Conversions; remove duplicate tracking events |
| No account-level sitelinks | Score 0 | Add 6 DSA sitelinks at account level too |

### P1 — Fix This Month
| Issue | Impact | How to Fix |
|-------|--------|-----------|
| DSA ad group: 32 keywords (>20) | Score 0 | Split into themed ad groups by URL category |
| Landing Page Score: below average | Score 0 | Improve page relevance, load speed, and content matching |
| DSA headline < 20 chars (2 headlines) | Score 0 | Expand to ≥ 20 characters |
| IS lost to budget: DSA 95%, PMax 43% | Revenue loss | Increase budget if ROAS > break-even, or improve Quality Score |
| PMax: no ad schedule | Score 50 | Add schedule based on conversion data after 30 days |
| 14/42 PMax assets: Low label | Score 66 | Replace with new creative after identifying patterns |

### P2 — Track and Improve
| Issue | Impact | How to Fix |
|-------|--------|-----------|
| QS 3-7 (not 8+) | Higher CPC | Improve ad relevance + landing pages |
| Only 9% keywords converting | Wasted spend | Pause non-converters, expand matching types on winners |
| No DKI in ads | Missed relevance | Note: DSA auto-generates headlines, DKI not applicable here |
| No Microsoft Ads | Missed traffic | Create account for additional reach (Optmyzr recommends) |

---

## Bulgarian Market — Platform Limitations
- Google Shopping / Merchant Center feed: **not available for Bulgaria** — Shopping Ads won't serve
- Many Google Ads features disabled for Bulgarian market (confirmed by Google partner 2026-04-03)
- Recommended campaign types: **DSA** (primary) + **PMax** (secondary, uses Merchant Center feed for creative assets but not placement)
- Google Ads API developer token has **test-only access** — use Claude-in-Chrome MCP for campaign management

---

## Key Metrics Reference
| Metric | Current | Target |
|--------|---------|--------|
| Account audit score | 70/100 | 90+/100 |
| Gross margin | 5.3% | — |
| Break-even ROAS | 18.87x | — |
| Target ROAS | — | 20x+ |
| DSA daily budget | €5/day | Scale with ROAS |
| PMax daily budget | €5/day | Scale with ROAS |
| Total daily budget | €10/day | Scale with ROAS |
| DSA CPC cap | €0.50 | — |
| Negative keywords | 146 total | 200+ |
| Quality Score | 3-7 | 8+ |
| Landing Page Score | Below Average | Above Average |
| Ad Strength (RSA) | Poor | Good/Excellent |
| Ad Strength (PMax) | Average | Excellent |
| IS lost to budget | DSA 95%, PMax 43% | < 20% |
| Conversion rate | ~105% (inflated) | 1-5% (realistic) |
