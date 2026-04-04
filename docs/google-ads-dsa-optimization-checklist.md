# ViaPharma DSA Campaign Optimization — Execution Checklist

**Date:** 2026-04-04
**Campaign:** ViaPharma DSA (ID: 23713866882)
**Account:** 825-619-0101

## Step 1: Run the Google Ads Script (automated bulk changes)

1. Disable ad blocker for ads.google.com
2. Go to **Tools → Scripts** (or navigate to `ads.google.com/aw/bulk/scripts`)
3. Click **+ New Script**
4. Paste contents of `scripts/google_ads_optimize_dsa.js`
5. Click **Preview** first to verify, then **Run**
6. Check the log output — should show all changes applied

**What the script does:**
- Sets budget: €10 → €20/day
- Adds 55 negative keywords (exact + phrase match) — research, controlled, competitor terms
- Adds 4 sitelinks (Намаления, Витамини, Козметика, BOX NOW)
- Adds 4 callout extensions (Оригинални продукти, 14 дни връщане, etc.)
- Adds structured snippet (Brands: La Roche-Posay, Eucerin, Bioderma, Solgar, etc.)
- Sets ad schedule (Mon-Fri 8-22 full bid, nights -30%, weekends -20%)

## Step 2: Switch bidding strategy (manual — 2 min)

1. Go to campaign **ViaPharma DSA → Settings** (or `ads.google.com/aw/campaigns/settings?campaignId=23713866882`)
2. Click **Bidding**
3. Change from "Maximize Clicks" to **Manual CPC**
4. Check the box **"Help increase conversions with Enhanced CPC"**
5. Set **Default max CPC bid: €0.35**
6. Save

## Step 3: Fix language targeting (manual — 1 min)

1. In campaign **Settings → Languages**
2. Currently: Bulgarian only
3. **Add "All languages"** — many Bulgarians run Chrome in English
4. Location targeting already ensures Bulgaria-only reach
5. Save

## Step 4: Fix location targeting option (manual — 1 min)

1. In campaign **Settings → Locations**
2. Click **Location options** (small link under the location list)
3. Change **Target** from "Presence or interest" to **"Presence: People in or regularly in your targeted locations"**
4. This prevents showing ads to tourists/expats researching Bulgaria
5. Save

## Step 5: Add audience signals — Observation mode (manual — 3 min)

1. Go to campaign → **Audiences** tab (left sidebar → Audiences, keywords and content → Audiences)
2. Click **Edit audience segments**
3. Set to **Observation** (not Targeting)
4. Add these segments:

**In-market audiences:**
- Health → Vitamins & Dietary Supplements
- Beauty & Personal Care → Skin Care Products
- Health → Cold & Flu Remedies
- Baby & Children's Products → Baby Care

**Life events:**
- New Parent
- Recently Moved

5. Save — no bid adjustments yet, just data collection for 2-3 weeks

## Step 6: Add remarketing audience (manual — 2 min)

*Requires Google Analytics 4 linked to Google Ads*

1. Go to **Tools → Audience manager**
2. Check if "All website visitors" audience exists
3. If not, create it: Source = GA4, include all visitors, membership duration = 540 days
4. Go back to campaign → Audiences → add "All website visitors" on **Observation**

## Phase 2: Ad group restructuring (do after 1 week of data)

Split the single "All Pages" ad group into category-specific groups. These are the URL rules to use:

| Ad Group | URL Contains | Max CPC |
|----------|-------------|---------|
| Козметика за лице | `/collections/grizha-za-litse` | €0.35 |
| Витамини и минерали | `/collections/vitamini-i-minerali` | €0.35 |
| Майка и дете | `/collections/mayka-i-dete` | €0.35 |
| Грип и настинка | `/collections/grip-i-nastinka` | €0.30 |
| Козметика за коса | `/collections/grizha-za-kosa` | €0.30 |
| Козметика за тяло | `/collections/grizha-za-tyalo` | €0.30 |
| Хомеопатия | `/collections/homeopatiya` | €0.30 |
| Намаления | `/collections/namaleniya` | €0.35 |
| Лечение и здраве | `/collections/lechenie-i-zdrave` | €0.30 |
| Catch-all | All web pages | €0.25 |

**How to create:** Campaign → Ad groups → + New ad group → Dynamic → set URL rule → set CPC → create ad with same descriptions.

## Phase 3: Switch to tROAS (after 40 purchases)

Once you accumulate ~40 real purchase conversions in this campaign:
1. Go to Settings → Bidding
2. Switch to **Target ROAS**
3. Set target: **500%** (5.0x) — conservative start
4. Monitor for 2 weeks, then lower to 400% if stable

## Verification (check after 48 hours)

- [ ] Budget showing €20/day in campaign settings
- [ ] Negative keywords visible in Keywords → Negative keywords tab
- [ ] Sitelinks showing in Ads & assets → Assets
- [ ] Callouts and structured snippets showing in Assets
- [ ] Ad schedule showing in Ad schedule tab
- [ ] Bidding shows "Manual CPC" with eCPC enabled
- [ ] Max CPC = €0.35
- [ ] Languages: Bulgarian + All languages
- [ ] Location option: "Presence" only
- [ ] Audiences: observation segments attached
- [ ] Search terms report: no junk queries leaking through
