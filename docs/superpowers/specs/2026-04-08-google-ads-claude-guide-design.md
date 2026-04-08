# Design Spec: Google Ads Claude Code Guide & Golden Template

**Date:** 2026-04-08
**Status:** Implemented
**Output files:**
- `docs/google-ads-claude-guide.md` — implementation reference for Claude Code sessions
- `docs/google-ads-playbook.md` — authoritative golden template for all campaign decisions

---

## Problem Statement

Running Google Ads for ViaPharma requires three distinct workflows: initial setup from scratch, daily/weekly optimization, and ongoing improvement decisions. Without a structured reference, Claude Code sessions start cold each time — repeating the same diagnostics, forgetting hard-won account context, and missing critical checks (e.g., conversion tracking verification, Bulgarian market constraints).

The PPC audit score of 70/100 (2026-04-08) and a 105.98% conversion rate (tracking bug) highlight that undocumented assumptions cause real money loss.

---

## Goals

1. **First-time setup:** Claude can create a correctly-configured DSA + PMax campaign pair from scratch without asking about basics already documented.
2. **Daily/weekly optimization:** Claude follows a structured workflow rather than ad-hoc analysis, using concrete thresholds (ROAS < 18.87x = alert) not vague guidelines.
3. **Improvement decisions:** Claude diagnoses symptoms (low QS, poor ad strength, conv rate >100%) with a decision tree that leads to specific fixes, not general advice.
4. **Institutional memory:** Account context (IDs, Bulgarian market constraints, break-even economics) is in the repo, not in conversation history.

---

## Non-Goals

- Automated campaign creation via API (Google Ads API token is test-only; browser automation is the path)
- Multi-account management (single account: 825-619-0101)
- Microsoft Ads / other platforms

---

## Approach

**Combined strategic + implementation doc** (`docs/google-ads-claude-guide.md`): strategic rules at the top (always apply), implementation patterns by task type below (consulted per workflow). Single file avoids context-switching between docs.

**Companion playbook** (`docs/google-ads-playbook.md`): authoritative standards table. Every campaign change must align with it. More structured/tabular than the guide; suitable for audit reference.

**Rejected alternatives:**
- *Separate strategic vs. implementation docs:* increases risk of drift between the two; Claude must check both
- *Pure implementation checklists only:* no "why" context leads to blindly following steps that don't fit changed circumstances

---

## Architecture

### `docs/google-ads-claude-guide.md` — 6 sections

| Section | Purpose | Key content |
|---------|---------|-------------|
| 1. Account Audit Snapshot | Current state reference | Strengths table, gaps table with P0/P1/P2 priority, 13 issues from 2026-04-08 audit |
| 2. Strategic Rules | Always-apply constraints | Conversion tracking rules, economics (18.87x break-even, 20x+ target), Bulgarian market constraints, quality targets, pre-change checklist |
| 3. Phase 1: First-Time Setup | Campaign creation workflow | Account URL anchors (campaign IDs), pre-flight checks, DSA config (Manual CPC €0.50, negative keywords 50+, 6 sitelinks), PMax config (asset group minimums, audience signals), post-creation verification |
| 4. Phase 2: Daily/Weekly Ops | Optimization workflow | Script commands with threshold responses, search terms workflow, QS checks, Optmyzr score breakdown, monthly PMax asset review |
| 5. Phase 3: Decision Tree | Symptom → fix | 6 failure modes: below break-even ROAS, low QS, Poor ad strength, conv rate >10%, PMax ROAS 0%, IS Lost >80% |
| 6. Browser Automation Patterns | UI interaction patterns | Navigation URLs, nativeInputValueSetter pattern, elementFromPoint, sitelink selection via role="option", save patterns, failure modes table, session workflow template |

### `docs/google-ads-playbook.md` — Golden Template

Tabular reference covering:
- Account-level standards (budget, bidding, conversion tracking)
- Campaign-level requirements (location, language, ad schedule, negatives, sitelinks)
- DSA campaign specifics (ad group structure, RSA standards, final URL, QS targets, keywords)
- PMax campaign specifics (asset group standards table, low-perf asset policy, audience signals, ad schedule)
- Recurring optimization workflow (daily/weekly/monthly)
- Pre-change checklist
- Known issues as of 2026-04-08 (P0/P1/P2)
- Bulgarian market limitations
- Key metrics reference table

---

## Data Flow

```
PPC Audit PDF (Optmyzr, 2026-04-08)
  + Browser session experience (sitelinks, Angular shadow DOM patterns)
  + Account economics (5.3% gross margin → 18.87x break-even)
  + Bulgarian market constraints (confirmed by Google partner 2026-04-03)
         ↓
google-ads-claude-guide.md    +    google-ads-playbook.md
         ↓                              ↓
Claude Code sessions              Pre-change checklist
(consult per workflow)            (every campaign change)
         ↓
CLAUDE.md (section: "Google Ads — Golden Template")
  → points to playbook as authoritative reference
  → lists all numeric targets for quick lookup
```

---

## Key Decisions

**Why nativeInputValueSetter pattern for Angular inputs?**
Angular Material uses shadow DOM for form controls. Direct `element.value = 'text'` bypasses Angular's change detection — the UI updates but the model doesn't. The native input value setter + dispatched `input`/`change` events is the only approach that reliably updates both.

**Why browser automation over the Google Ads API?**
Developer token `U8t0BWmbOgkKz9hga9_rkw` has test-only access — it cannot read or modify production accounts. Claude-in-Chrome MCP is the production path until a standard API token is approved.

**Why DSA as primary campaign type for Bulgaria?**
Google Shopping / Merchant Center feed is not available for Bulgaria. PMax campaigns show "No products for any locations" — this is a confirmed platform limitation, not a config error. DSA uses URL/content crawling with no Shopping feed dependency.

**Why Manual CPC (not Smart Bidding) for DSA?**
Smart bidding (Target ROAS, Target CPA) requires 40+ real purchase conversions for reliable ML signal. With a new campaign and <40 conversions, Manual CPC €0.50 gives cost control while data accumulates. Graduate to tROAS after threshold is met.

**Why 18.87x break-even ROAS?**
Gross margin = 5.3% (blended, confirmed 2026-04-04). Break-even: 1 / 0.053 = 18.87x. Any ROAS below this means the campaign loses money even before overhead. Target is 20x+ to ensure profitability after overhead.

---

## Testing / Verification

The guide is verified by use: each Claude Code session that follows the guide should produce actions consistent with the playbook standards. Verification checkpoints:
- After campaign creation: post-creation checklist passes
- After optimization session: no P0 issues remain open
- After monitoring: alerts correlate with real performance issues (no false positives after 2026-04-06 false-positive fix)

---

## Maintenance

- Update `docs/google-ads-playbook.md` "Known Issues" table after each monthly audit
- Update `CLAUDE.md` numeric targets if break-even economics change (margin rate change)
- Add new browser automation patterns to Section 6 as Google Ads UI evolves
- Archive snapshot of this spec when a major account restructure occurs (new campaign types, new budget splits)
