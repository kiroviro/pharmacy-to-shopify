# Google Ads — Claude Code Master Guide

**Account:** 825-619-0101 (ViaPharma US, EUR) | Manager: 966-252-5245
**Audit date:** 2026-04-08 | Score: 70/100 → Target: 90+/100
**Tooling:** Claude-in-Chrome MCP (Playwright) — Google Ads API has test-only access, cannot modify production
**Competitors tracked:** sopharmacy.bg, primepharmacy.bg, aptekanove.bg

This is the single authoritative guide Claude Code reads before any Google Ads session.
Strategic rules live here. Implementation patterns live here. Decisions are derived from here.

---

## Section 1 — Account Audit: What's Working vs. What's Broken

### ✅ Strengths (preserve these)

| What | Why it matters |
|------|---------------|
| Location targeting: Bulgaria (both campaigns) | Prevents spend on non-Bulgarian traffic |
| 146 negative keywords across 2 campaigns | Baseline protection against irrelevant queries |
| Attribution model: Data-driven (not Last Click) | More accurate credit distribution |
| Campaign-level sitelinks on DSA (6 sitelinks) | Improves CTR and ad quality |
| No duplicate ads or headlines | Clean RSA structure |
| Conversion tracking active (3 real conversions/30d) | Pipeline is wired up |
| Final URL Expansion ON for PMax | Google can optimise landing pages |
| Dynamic order value passed to conversion tag | Real revenue tracking, not fixed values |

### ❌ Gaps (fix in priority order)

| # | Issue | Score | Impact | Status |
|---|-------|-------|--------|--------|
| 1 | Conversion rate 105.98% (28,593 conv vs 26,631 clicks) | Critical | Entire bidding strategy is miscalibrated | **Fix immediately** |
| 2 | DSA final URL: `http://viapharma.us` (not https) | 0 | Ad disapproval risk | **Fix immediately** |
| 3 | DSA RSA ad strength: Poor | 0 | Lower ad rank, higher CPC | This week |
| 4 | PMax: No audience signals | 0 | Slower machine learning ramp-up | This week |
| 5 | No account-level sitelinks | 0 | Missing coverage on all ads | This week |
| 6 | IS lost to budget: DSA 95%, PMax 43% | 0 | Massive missed traffic | Increase budget when ROAS > break-even |
| 7 | DSA ad group: 32 keywords (limit: 20) | 0 | Quality Score dilution | This month |
| 8 | 2 RSA headlines < 20 chars ("Витамини и Добавки" 18ch, "Козметика и Здраве" 18ch) | 0 | Ad strength penalty | This week |
| 9 | Landing page score: Below Average (100% of keywords) | 0 | Highest QS lever | This month |
| 10 | PMax: No ad schedule | 50 | Wasted spend in off-peak hours | After 30d data |
| 11 | 14/42 PMax assets: Low performance label | 66 | Weak creative pulling down asset group | After 30d data |
| 12 | Only 3/32 keywords (9%) converting | — | 91% of keywords consuming budget with no return | Weekly review |
| 13 | 100% broad match keywords | — | Risky — add phrase/exact for top converters | This month |

---

## Section 2 — Strategic Rules (Non-Negotiables)

Claude never violates these. If a user request conflicts with a rule, explain the conflict first.

### 2.1 Conversion Tracking

```
RULE: One Primary conversion action — "Google Shopping App Purchase" only.
      All other events (page_view, search, view_item, add_to_cart, begin_checkout,
      add_payment_info) must be Secondary (observation).

VERIFY BEFORE EVERY CAMPAIGN CHANGE:
  → Goals → Conversions → check Primary column
  → If conv rate > 10% in any campaign: STOP. Audit for double-counting before any action.
  → Current anomaly: 105.98% conv rate = tracking bug. Fix before trusting any ROAS number.

Auto-tagging: must be ON (Account Settings → Auto-tagging)
Attribution: Data-driven (not Last Click)
```

### 2.2 Economics

```
Gross margin:       5.3%
Break-even ROAS:    18.87x  (1 / 0.053)
Target ROAS:        20x+
Daily budget:       €10 total (DSA €5 + PMax €5) — scale only when ROAS > break-even
Max CPC (DSA):      €0.50
Max CPC (PMax):     Algorithm (Maximize Conversion Value)

BUDGET RULE: Never increase budget on a campaign with ROAS < 18.87x.
             First fix quality (QS, landing page, ad strength). Budget follows performance.
```

### 2.3 Bulgarian Market Constraints

```
Google Shopping / Merchant Center: NOT available for Bulgaria.
  → PMax "no products for any locations" = platform limitation, not a config error.
  → Do not attempt to fix — it cannot be fixed.

Many Google Ads features disabled for Bulgaria (confirmed by Google partner 2026-04-03).
Recommended campaign types: DSA (primary) + PMax (secondary, uses Merchant Center for
creative assets only — not for placement).

Language targeting: Bulgarian + All Languages (Bulgarians often use Chrome in English).
Location option: "Presence" only (not "Presence or interest").
```

### 2.4 Quality Targets

```
Metric                   | Current      | Target
-------------------------|--------------|------------------
Quality Score            | 3–7          | 8+
Landing Page Score       | Below Avg    | Above Average   ← biggest lever
Ad Relevance             | Average      | Above Average
Expected CTR             | Average      | Above Average
RSA Ad Strength          | Poor         | Good or Excellent
PMax Asset Strength      | Average      | Excellent
IS Lost to Budget        | 95% / 43%   | < 20% per campaign
Keywords per ad group    | 32           | ≤ 20
Headlines (min chars)    | 18 chars     | ≥ 20 chars each
Conversion rate          | 105% (bug)   | 1–5% (realistic e-commerce)
```

### 2.5 Pre-Change Checklist

Before making ANY Google Ads change, run through this:
- [ ] Conversion tracking verified (only Purchase = Primary)
- [ ] Auto-tagging ON
- [ ] Final URL is https:// (not http://)
- [ ] No active policy violations that would block the change
- [ ] Change aligns with this guide — if not, document why before proceeding

---

## Section 3 — Phase 1: First-Time Campaign Setup

Use this when creating a new Google Ads campaign from scratch for ViaPharma.

### 3.1 Account Navigation

```
Account URL pattern:  ads.google.com/aw/[section]?ocid=8001809503&...&authuser=0
DSA Campaign ID:      23713866882
PMax Campaign ID:     23722367460
PMax Asset Group ID:  6697056066
Merchant Center:      5526048589 - ViaPharma

Claude-in-Chrome MCP navigation rules:
  → Use browser_navigate for direct URLs
  → Deep URLs sometimes redirect — navigate to campaign list first, then drill in
  → find() and browser_click() work; read_page() and javascript_tool blocked by Google CSP
  → Always take a screenshot before and after each significant action
```

### 3.2 Pre-Flight Checks (Before Creating Anything)

1. **Verify conversion tracking**
   - Navigate: Goals → Conversions
   - Confirm: only "Google Shopping App Purchase" = Primary
   - If any other event is Primary: fix it first, do not proceed

2. **Verify auto-tagging**
   - Navigate: Admin → Account Settings → Auto-tagging
   - Must show: ON

3. **Check existing campaigns**
   - Are DSA and PMax both active? If yes, do not create duplicates
   - Check budget split: DSA €5/day + PMax €5/day = €10/day total

### 3.3 DSA Campaign Creation

**Campaign settings:**
```
Name:            ViaPharma DSA
Type:            Search (with Dynamic Search Ads enabled)
Bidding:         Manual CPC, max €0.50
Budget:          €5/day
Location:        Bulgaria
Location option: Presence (not "Presence or interest")
Language:        Bulgarian + All Languages
Domain:          viapharma.us
DSA targets:     All web pages (Google crawls entire site)
Status:          PAUSED — enable manually after verification
```

**URL exclusions (add immediately after creation):**
```
/pages/
/blogs/
/cart
/policies/
/account
/search
```

**Ad copy (Bulgarian, descriptions only — headlines auto-generated by Google):**
```
Desc 1: Пазарувайте витамини, добавки, козметика и здравни продукти онлайн.
Desc 2: Доверена онлайн аптека. Хиляди продукти. Бърза доставка в България.
Desc 3: Витамини, козметика и бебешка грижа с бърза доставка в България.
Desc 4: Вашата онлайн аптека за здраве и красота. Европейско качество.
```

**RSA (Responsive Search Ad) — minimum for Good strength:**
```
Headlines (15 total, each ≥ 20 chars):
  ViaPharma Онлайн Аптека      (23)
  Витамини и Хранителни Добавки (30)
  Козметика и Здравни Продукти  (28)
  Вашата Онлайн Аптека          (20)
  Аптеки в България             (20)
  Аптеки БГ Онлайн              (20)
  Безплатна Доставка            (20)  [only if true at time of creation]
  10000+ Здравни Продукта       (22)
  Оригинални Продукти           (21)
  Бърза Доставка до Вас         (21)
  [5 more unique, ≥ 20 chars]

Descriptions (4 total, each ≥ 60 chars):
  [use the 4 descriptions above]
```

**Sitelinks (minimum 4, use existing DSA sitelinks):**
```
Намаления      → /collections/namaleniya
Витамини       → /collections/all/витамини
Козметика      → /collections/all/грижа-за-лице
Box Now        → viapharma.us
Бебешка грижа → /collections/all/бебешка-грижа
Bella Baby крем → /products/бела-бебе-крем-bella-baby-cream
```

**Negative keywords (add 50+ from existing list before launch):**
```
Core competitors: гален, галена, софарма, framar, benu, бену, ремедиум
Irrelevant: гръцка аптека, марешки, гръцки, гръцка
[add more from scripts/dsa_search_terms.py output]
```

### 3.4 PMax Campaign Creation

**Campaign settings:**
```
Name:         ViaPharma PMax
Type:         Performance Max
Bidding:      Maximize Conversion Value (no tROAS until 40+ real purchases)
Budget:       €5/day
Location:     Bulgaria
Language:     Bulgarian + All Languages
Merchant:     5526048589 - ViaPharma
Status:       PAUSED — enable manually after asset group complete
```

**Asset Group minimum requirements (for Excellent strength):**
```
Asset Type          | Minimum | Target
--------------------|---------|-------
Headlines           | 3       | 15 (each ≥ 20 chars)
Long headlines      | 1       | 5
Descriptions        | 2       | 5 (each ≥ 60 chars)
Images (1.91:1)     | 1       | 20
Images (1:1 square) | 1       | 20
Images (4:5 portrait)| 1      | 5
Logo                | 1       | 1
Videos              | 1       | 3 (need horizontal + square + vertical)
Sitelinks           | 4       | 8+
Audience signals    | 1       | 3 (REQUIRED — currently missing, score 0)
```

**Audience signals to add (always add before enabling):**
```
Custom intent:  viapharma.us visitors, competitor URLs (galen.bg, benu.bg, sopharma.bg)
In-market:      Health/Vitamins & Supplements
                Beauty & Personal Care
                Baby & Children's Products
Remarketing:    All website visitors (tag: AW-17931842941)
```

### 3.5 Post-Creation Verification Checklist

Before enabling any campaign:
- [ ] Conv tracking: only Purchase = Primary
- [ ] Final URL: https:// (never http://)
- [ ] RSA ad strength: Good or Excellent (not Poor/Average)
- [ ] Sitelinks: ≥ 4 attached
- [ ] Negative keywords: ≥ 50 added
- [ ] Location: Bulgaria, option = Presence
- [ ] Language: Bulgarian + All Languages
- [ ] URL exclusions on DSA: /pages/, /blogs/, /cart, /policies/, /account, /search
- [ ] Audience signals on PMax: at least custom intent + in-market
- [ ] Budget: ≤ €10/day total across all campaigns
- [ ] Status: PAUSED until human reviews and enables

---

## Section 4 — Phase 2: Daily & Weekly Optimization

### 4.1 Daily Monitoring (08:00 UTC+3, automated via launchd)

```bash
# Automated — runs via ~/Library/LaunchAgents/com.viapharma.dsa-daily-report.plist
python scripts/dsa_daily_report.py

# Manual check
python scripts/monitor_dsa_campaign.py --days 1
python scripts/monitor_dsa_campaign.py --days 7
```

**Interpret the output:**
```
DSA ROAS (est) > 18.87x  → Campaign profitable. Check IS lost to budget.
                            If IS lost > 20%, propose budget increase to user.
DSA ROAS (est) 1–18.87x → Below break-even. Review search terms. Add negatives.
                            Do NOT increase budget.
DSA ROAS (est) < 1x      → Losing money on ad spend alone. Review search terms urgently.
                            If trend continues 3 days, propose pausing to user.
Conv rate > 10%           → STOP. Conversion tracking bug. Audit Goals → Conversions.
Conv rate = 0 for 3+ days → Check campaign status, ad approval, auto-tagging.
Zero orders all channels  → Check Shopify API connectivity and store status.
```

**Alert thresholds (trigger immediate action):**
```
IS Lost to Budget > 80%   → Budget too low for demand (fix: increase budget if ROAS > 18.87x)
ROAS < 1x for 3 days      → Propose pausing campaign to user
Conversion rate > 100%    → Conversion tracking double-counting — audit immediately
Zero DSA orders 3+ days   → Campaign broken — check Google Ads UI
```

### 4.2 Weekly Search Terms Review

```bash
# Export from Google Ads UI: Campaigns → DSA → Search terms → Download CSV
python scripts/dsa_search_terms.py --csv ~/Downloads/search_terms.csv --email

# Review output and add flagged negatives in Google Ads UI:
# Campaigns → ViaPharma DSA → Keywords → Negative keywords
```

**What to add as negatives:**
```
Competitor brands:    гален, галена, софарма, framar, benu, бену, ремедиум, субра, марви, афия
Low-intent browsing:  аптеки (without product intent), pharmacy bg, online apteka
Drug names:           specific prescription drug names (not OTC products)
Irrelevant:           ветеринар, очила, лещи, зъболекар, медицински обеци
```

**What to protect (never add as negative):**
```
Product categories:   витамини, козметика, бебешка грижа, крем, шампоан, добавки
Brand of products:    la roche-posay, eucerin, bioderma, bella baby, solgar, pampers
High-intent:          цена, купи, онлайн, доставка, аптека [specific product]
```

### 4.3 Weekly Quality Score Check

Navigate: Campaigns → ViaPharma DSA → Keywords → Columns → add QS columns
```
Check for each keyword:
  Quality Score < 5  → Pause keyword (not worth paying for bad placement)
  Quality Score 5–7  → Investigate: is the landing page relevant? Is the ad text matching?
  Quality Score 8+   → Keep, protect from being paused

Root cause of low QS (in order of impact):
  1. Landing Page Experience (biggest lever — 100% below average currently)
  2. Ad Relevance (match search intent in RSA headlines)
  3. Expected CTR (improve headlines to be more compelling)
```

### 4.4 Weekly Optmyzr Check

Navigate to: tools.optmyzr.com/account-dashboard/overview?account=8256190101&type=adwords

**Express Optimizations to act on:**
```
"Fix Impression Share Lost Due To Budget"  → Only if ROAS > 18.87x. Propose budget increase to user.
"PMax Asset Groups with no Audience Signal" → Add immediately (score 0, zero downside).
"Fix Ads with Issues (RSA)"                → Fix immediately (http URL, short headlines).
"Add New Keywords"                         → Review suggestions, add relevant ones as phrase/exact match.
```

**PPC Audit Score breakdown to monitor:**
```
Category             | Current | Target | Action if dropping
---------------------|---------|--------|-------------------
Campaigns            | 0       | 80+    | Fix IS lost to budget
Performance Max      | 80      | 90+    | Add audience signals, improve asset strength
Ad Groups            | 75      | 90+    | Split 32-keyword group into ≤20 themed groups
Responsive Search Ads| 80      | 90+    | Fix http URL, expand short headlines
Keywords             | 100     | 100    | Maintain
Performance          | 37      | 60+    | Improve landing pages (biggest impact)
```

### 4.5 Monthly PMax Asset Review

Navigate: Campaigns → ViaPharma PMax → Asset groups → Asset Group 1 → View assets

```
Asset label "Low"  → Flag for replacement. Create 2 new alternatives.
                     Never delete Good/Best assets.
Asset label "Best" → Analyze what makes it work. Create more like it.
Asset label "Good" → Keep as-is.
Asset label "Low" + image → Replace with product photo (not stock images).

After replacing:  Wait 4 weeks for new label assignment before evaluating.
```

---

## Section 5 — Phase 3: Campaign Improvement Decision Tree

Use this when ROAS is below target or audit score is declining.

### 5.1 Symptom → Diagnosis → Fix

```
SYMPTOM: ROAS below 18.87x (break-even)
  ↓
  Is IS Lost to Budget > 50%?
    YES → Budget is the constraint, not quality.
          Is current ROAS > 10x?
            YES → Increase budget gradually (+€2/day). Monitor for 3 days.
            NO  → Fix quality first (go to "Low QS" branch below).
    NO  → Budget is not the issue. Go to search terms.
          Review search terms: any competitor/irrelevant queries spending budget?
            YES → Add negatives. Wait 7 days. Check ROAS again.
            NO  → Landing page quality issue. See "Landing Page" branch below.

SYMPTOM: Low Quality Score (< 8)
  ↓
  Check the three QS components:
  - Landing Page Experience "Below Average"
    → Is the landing page directly relevant to the search query?
    → Does it load fast? (check PageSpeed Insights for viapharma.us)
    → DSA: ensure URL exclusions cut /pages/ /blogs/ /cart /policies/
    → DSA: consider URL inclusions to focus only on product/collection pages
  - Ad Relevance "Average"
    → Are RSA headlines matching the search intent?
    → Add headlines that include the product category words being searched
    → Use Dynamic Keyword Insertion ({KeyWord:ViaPharma}) for broad terms
  - Expected CTR "Average"
    → Headlines not compelling enough. A/B test stronger CTAs.
    → Bulgarian CTAs that work: "Поръчай онлайн", "Виж цената", "Бърза доставка"

SYMPTOM: RSA Ad Strength is Poor or Average
  ↓
  Check which assets are missing:
  - Headlines < 15 → Add more unique headlines (≥ 20 chars each)
  - Duplicate headlines → Remove duplicates, replace with unique variants
  - Short headlines (< 20 chars) → Expand: "Витамини и Добавки" → "Витамини и Хранителни Добавки"
  - Descriptions < 4 → Add descriptions (≥ 60 chars each)
  - No sitelinks → Add from asset library
  Target: Good = can serve. Excellent = optimal placement.

SYMPTOM: Conversion rate > 10% (or > 100%)
  ↓
  STOP all budget increases immediately.
  Navigate: Goals → Conversions → check all conversion actions
  → Is "Google Shopping App Purchase" the only Primary? If not → fix it.
  → Are there multiple purchase events firing? Remove duplicates.
  → Cross-check: Google Ads conversions vs Shopify orders in monitor script.
  → Do not trust ROAS numbers until conv rate is in 1–5% range.

SYMPTOM: PMax ROAS 0% (as of 2026-04-08, 0 conversions, €11 spent)
  ↓
  PMax is newly created and needs data to optimise.
  Actions (in order):
  1. Add audience signals (currently missing — score 0)
  2. Verify all asset types filled (headlines, descriptions, images, video, sitelinks)
  3. Wait 4–6 weeks for machine learning to ramp up
  4. Do not judge PMax performance before 30 days + 50 conversions
  5. If 0 conversions after 30 days: check conversion tracking, not campaign

SYMPTOM: Impression Share Lost to Budget > 80%
  ↓
  Is this DSA or PMax?
  DSA (currently 95%): Is DSA ROAS > 18.87x?
    YES → DSA is profitable. Propose to user: increase DSA budget to €10/day.
    NO  → DSA not profitable. Fix quality first. Budget increase would waste money.
  PMax (currently 43%): Is PMax generating conversions?
    NO (current state) → Don't increase budget. Add audience signals first.
    YES → Is ROAS > 18.87x? Increase if yes.
```

### 5.2 Competitor Intelligence

```
Top competitors (from Optmyzr, 2026-04-08):
  sopharmacy.bg    → online pharmacy, overlapping keywords
  primepharmacy.bg → online pharmacy, overlapping keywords
  aptekanove.bg    → online pharmacy, overlapping keywords

Defensive actions:
  - These competitor names should be KEPT as negative keywords
    (prevent showing on "sopharmacy намаления" type queries)
  - Monitor their ad copy monthly for positioning changes
  - Our differentiators: Bella Baby (official importer), BoxNow delivery, EU quality
```

---

## Section 6 — Browser Automation Patterns

Claude uses Playwright (plugin_playwright MCP) to operate Google Ads UI.
These patterns were discovered through trial and error — use them to avoid re-discovering failures.

### 6.1 Navigation

```javascript
// Always navigate to campaign list first, then drill in
// Direct deep URLs sometimes redirect unexpectedly

// Standard account URL pattern
const BASE = 'https://ads.google.com/aw';
const PARAMS = '?ocid=8001809503&euid=91825682&__u=1077014018&uscid=8001809503&__c=2120683047&authuser=0';

// Campaign list
browser_navigate(`${BASE}/campaigns${PARAMS}`)

// Asset group editor (PMax)
browser_navigate(`${BASE}/assetgroup/edit${PARAMS}&assetgroupId=6697056066&campaignId=23722367460`)

// DSA ad editor
browser_navigate(`${BASE}/ads${PARAMS}&campaignId=23713866882`)
```

### 6.2 Filling Angular Form Fields (nativeInputValueSetter pattern)

Google Ads uses Angular — direct `element.value = 'text'` does NOT trigger change detection.
**Always use this pattern:**

```javascript
const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
  window.HTMLInputElement.prototype, 'value'
).set;

// Find the empty input
const input = Array.from(document.querySelectorAll('input[type="text"], textarea'))
  .find(i => i.value === '' && i.closest('[class*="headline"], [class*="description"]'));

nativeInputValueSetter.call(input, 'Your text here');
input.dispatchEvent(new Event('input', {bubbles: true}));
input.dispatchEvent(new Event('change', {bubbles: true}));
```

### 6.3 Clicking Buttons (Shadow DOM pattern)

Google Ads uses Shadow DOM — `querySelector` often returns null inside dialogs.
**Use elementFromPoint for elements inside dialogs:**

```javascript
// Click by visual position (reliable for dialog elements)
const el = document.elementFromPoint(x, y);
let current = el;
for (let i = 0; i < 8; i++) {
  if (!current) break;
  const tag = current.tagName;
  if (['MATERIAL-BUTTON', 'EXTENSION-ASSET-CONTAINER', 'MATERIAL-LIST'].includes(tag)) {
    current.click();
    break;
  }
  current = current.parentElement;
}
```

**Click tab-button elements (work with .click()):**
```javascript
document.querySelectorAll('tab-button').forEach(btn => {
  if (btn.textContent.trim() === 'Asset library') btn.click();
});
```

### 6.4 Selecting Sitelinks / Assets from Asset Library

```javascript
// After opening the "Add sitelinks" dialog and switching to "Asset library" tab:
const targets = ['Bella Baby крем', 'Бебешка грижа', 'Box Now доставка',
                 'Козметика за лице', 'Витамини', 'Намаления'];

document.querySelectorAll('[role="option"]').forEach(opt => {
  const text = opt.textContent.trim();
  for (const target of targets) {
    if (text.startsWith(target) && !opt.querySelector('[aria-checked="true"], [checked]')) {
      opt.click();
      break;
    }
  }
});
// Then click Save using browser_click with the ref from browser_snapshot
```

### 6.5 Saving Changes

**Two-step save pattern:**
1. First save the dialog (sitelinks/images/videos picker) using the dialog's Save button
2. Then save the whole asset group using "Save this ad" button

```javascript
// Step 1: Save dialog — find Save inside dialog
const dialogSave = document.querySelectorAll('material-button')
  .find(b => b.textContent.trim() === 'Save');
// Do NOT click all Save buttons at once — this caused "Something went wrong" error
// Use browser_click with ref from browser_snapshot instead

// Step 2: After dialog closes, click "Save this ad" (ref from snapshot)
// browser_click({ ref: 'e1029', element: 'Save this ad button' })
```

**Getting element refs reliably:**
```javascript
// Use browser_snapshot, then grep the output:
// python3 -c "
// import json
// with open('snapshot.json') as f: data = json.load(f)
// text = data[0]['text']
// for i, line in enumerate(text.split('\n')):
//     if 'Save' in line and 'ref=' in line: print(i, line[:120])
// "
```

### 6.6 Adding Headlines / Descriptions to RSA

```javascript
// Click "+ Headline" button using its ref from browser_snapshot
// Then fill the new empty input using nativeInputValueSetter:

async function addHeadline(text) {
  // 1. Click the Add Headline button (find ref via browser_snapshot)
  await browser_click({ ref: 'ADD_HEADLINE_REF', element: 'Add Headline button' });

  // 2. Fill the newly created empty input
  await browser_evaluate({ function: `() => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    const input = Array.from(document.querySelectorAll('input'))
      .find(i => i.value === '' && i.placeholder && i.placeholder.includes('Headline'));
    if (input) {
      setter.call(input, '${text}');
      input.dispatchEvent(new Event('input', {bubbles: true}));
      input.dispatchEvent(new Event('change', {bubbles: true}));
    }
  }` });
}
```

### 6.7 Common Failure Modes & Fixes

| Failure | Root cause | Fix |
|---------|-----------|-----|
| `querySelector` returns null in dialog | Shadow DOM isolation | Use `elementFromPoint(x, y)` + walk parentElement |
| `element.value = 'text'` doesn't persist | Angular change detection | Use `nativeInputValueSetter` + dispatch input/change events |
| Clicking "Save" causes "Something went wrong" | Multiple Save buttons clicked simultaneously | Use `browser_click` with specific ref, not `querySelectorAll('button').find(b => b.text === 'Save').click()` |
| Tab click does nothing | Custom `tab-button` element needs `.click()` not a Playwright click | Use `document.querySelectorAll('tab-button').forEach(...)` |
| Deep URL redirects to wrong page | Google Ads redirects some deep links | Navigate to campaign list first, then use UI to drill in |
| Screenshot shows loading spinner | Page still loading | Wait 2–3 seconds before next action |
| browser_click times out | Element intercepted by sticky header | Use JS `.click()` or scroll element into view first |

### 6.8 Session Workflow Template

Every Google Ads session with Claude should follow this order:

```
1. BRIEF      → Read this guide. Read docs/google-ads-playbook.md for targets.
2. AUDIT      → python scripts/monitor_dsa_campaign.py --days 7
3. DIAGNOSE   → Apply Section 5 decision tree to current symptoms
4. PLAN       → Tell user exactly what you will change and why (cite Section 2 rules)
5. EXECUTE    → Use Section 6 browser patterns to make changes
6. VERIFY     → Screenshot after every change. Confirm save succeeded.
7. REPORT     → Summarise: what was changed, what metric it should improve, when to check
```

---

## Quick Reference Card

```
Campaign IDs:        DSA=23713866882  PMax=23722367460  AssetGroup=6697056066
Budget:              €5+€5=€10/day total
Break-even ROAS:     18.87x (5.3% margin)
Target ROAS:         20x+
Max CPC (DSA):       €0.50
Conversion Primary:  Google Shopping App Purchase ONLY
Auto-tagging:        Must be ON
Final URL:           https://viapharma.us (never http)
Competitors:         sopharmacy.bg, primepharmacy.bg, aptekanove.bg

Audit score:         70/100 → target 90+/100
Biggest gap:         Landing Page Score (Below Average — 0 points)
Next P0 fixes:       Fix conv tracking anomaly → Fix http URL → Add PMax audience signals

Monitoring script:   python scripts/monitor_dsa_campaign.py --days 7
Search terms script: python scripts/dsa_search_terms.py --csv ~/Downloads/search_terms.csv
Daily report:        python scripts/dsa_daily_report.py --no-email
Optmyzr dashboard:   tools.optmyzr.com/account-dashboard/overview?account=8256190101&type=adwords
```
