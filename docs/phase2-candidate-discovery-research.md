# Phase 2 — Candidate Discovery Sources and Evidence Constraints

Status: Bao research deliverable (external research supporting the repository).
Author role: Bao (research agent). No implementation, no commit, no credentials collected.
Verification date: 2026-10-24. Figures below are as published by the cited providers and may change.

Purpose: answer the open architecture question "which initial discovery adapters and marketplace
pairings are reliable enough for M1 beyond sample fixtures" (see `PHASE_2_ARCHITECTURE.md` §6), and
supply the source/evidence matrix, required-vs-optional fields, fail-closed conditions, credential
assumptions, and demo fixtures the Phase 2 batch pipeline needs.

Phase 1 remains the sole authority for identity, freshness, economics, scoring, and recommendations.
This document does not change any Phase 1 contract; it only describes where Phase 2 gets its inputs.

---

## 1. Executive recommendation (bounded M1 candidate set)

For the first milestone, keep discovery credential-free and deterministic, and add at most ONE live
read-only adapter later.

Recommended M1 discovery input (in priority order):

1. Deterministic sample/fixture adapter (default, no credentials). Source: the synthetic batch in
   `examples/phase2-demo-candidates.json`. This is the only discovery path required for M1.
2. Manual import (CSV/JSON seed list). A human pastes candidate references (title, store, URL,
   observed price, timestamp). No API, no credential, keeps Phase 1's manual-observation provenance.
3. Optional live adapter (only if a free eBay Developer Program key is configured): eBay Browse API
   for active-listing discovery plus eBay Deal API for eBay-side deals. Both are self-serve,
   client-credentials OAuth, 5,000 calls/day default. They return ACTIVE listings/deals, never sold data.

Sold evidence for M1 (the hard gate) is MANUAL by default:

- Terapeak / "Product Research" in eBay Seller Hub (free with a seller account, ~3 years aggregated
  sold data, browser-only, no API), recorded as authenticated-manual observations; OR
- a licensed third-party sold-comps API (CompsAPI, SoldComps, Trawl, or an Apify comps actor) after a
  permitted-use review, recorded as licensed-third-party observations.

Deferred from M1 (documented, not silently blocked): Amazon inferred-demand via Keepa (paid key),
Reddit/community discovery (commercial agreement required), deal aggregators like Slickdeals
(commercial affiliate agreement), and paid scanning suites like Tactical Arbitrage (Amazon
Professional seller account + subscription, no clean API). See §2 and §6 for constraints.

Why: the resale economics only make sense when sold evidence is real and fresh. Every clean official
API for sold data is either closed (Marketplace Insights) or non-programmatic (Terapeak), and every
automated "discovery" tool that produces good candidates (Tactical Arbitrage, SourceMogul) is a paid,
account-gated black box with no stable public API. The lowest-risk M1 proves the full pipeline on
deterministic fixtures and manual import, then layers one free eBay adapter, without depending on any
paid/partner credential.

---

## 2. Candidate discovery source matrix

Sources are listed by how they can feed the "discover" stage. "Self-serve" means a developer can get a
key without a business relationship. "ToS risk" means automated collection is restricted or prohibited
by the provider's terms, so it is not an approved path under Phase 1 policy.

| Discovery source | Type / what it yields | Access | Credential needed | Freshness | Constraint | M1 verdict |
|---|---|---|---|---|---|---|
| Sample/fixture adapter | Deterministic synthetic candidates | Local file | none | fixed `demo_now` | none | REQUIRED (default) |
| Manual import (CSV/JSON) | Human-curated seed list | Local file | none | human-entered timestamps | must preserve provenance/timestamp quality | REQUIRED |
| eBay Browse API | Active listings by query/category | Official REST, self-serve | eBay Developer Program app (client ID/secret) | real-time (active) | ACTIVE listings only; 5,000 calls/day default (100K after Compatible Application Check) | OPTIONAL (first live adapter) |
| eBay Deal API / Marketing / Merchandising API | eBay-side deals/promotions | Official REST, self-serve | same Developer Program key | real-time | 5,000 calls/day | OPTIONAL |
| eBay Feed API | Weekly snapshot of all active items | Official, AVRO files | Developer Program; `ITEM_ALL_ACTIVE_MARKETING` variant is EPN-partner-exclusive | weekly bootstrap | not daily; marketing feed gated to EPN partners | DEFER |
| Slickdeals | Vetted deals across ~10k merchants | Commercial API via team contact (affiliate rev-share); or third-party ReefAPI/scrapers | affiliate agreement (official) or paid credits (ReefAPI) | ~15-min refresh | not self-serve; scraping has ToS caveat | DEFER |
| Reddit (r/flipping, r/deals, r/buildapcsales) | Community deal/lead threads | Data API OAuth free tier | OAuth app; commercial use requires separate agreement; new apps need Responsible Builder Policy approval | near real-time | 100 QPM free tier; unauthenticated (incl. `.json`) blocked since May 2026; scraping prohibited, actively litigated | DEFER (needs agreement) |
| Tactical Arbitrage / Threecolts Seller 365 | Bulk store scans (1,400+ sites) matched to Amazon | Proprietary SaaS | Amazon Professional seller account + subscription ($59–$159/mo, or $69/mo bundle) | on-demand/cached | no clean public API; UI + Google Drive export; 40K scan-min/month | DEFER |
| SourceMogul | Retailer scan → Amazon match | Discontinued (no longer sold) | n/a | n/a | not available | EXCLUDE |
| SellerAmp SAS | Single-product grading | Proprietary SaaS | subscription $19.95–$49.95/mo | on-demand | one product at a time; not bulk discovery | EXCLUDE |
| Keepa | Amazon price history, sales rank/BSR, "deals", best-seller lists | REST API | paid API key (entry €49/mo, 20 tokens/min; no free tier) | near real-time | inferred demand only, never sold count; licensed third-party | DEFER |
| Walmart Marketplace API | Seller-side item/inventory/order/pricing for YOUR listings | Official, sellers/approved providers only | Walmart seller/partner OAuth 2.0 (15-min tokens) | real-time for own inventory | NOT a competitor-price/catalog discovery API; terms restrict to serving suppliers | EXCLUDE (manual only) |
| Best Buy Products API | Catalog, prices, availability, stores, open-box | Official REST, free key (email) | API key; commercial/affiliate relationship for non-affiliate use | near-real-time price | 5 calls/sec + 50,000/day; terms oriented to affiliate/selling Best Buy; ToU prohibits automated collection; caching capped at 72h; affiliate page currently 404 | MANUAL/RESEARCH-ONLY (affiliate path possible) |

Notes on the matrix:

- "Active listings" (eBay Browse) can seed candidates, but per Phase 1 policy an active asking price is
  never sold evidence. A Browse-only candidate will always fail the sold gate (§5).
- Walmart and Best Buy remain manual/research-only for automated source-price feed under Phase 1
  policy (`docs/freshness-policy.md` §4): Walmart's API is seller-scoped, and Best Buy's self-serve
  key is affiliate/selling-oriented and its ToU prohibits automated collection for price scraping.
  Neither is an approved automated source-price path without a human terms review.

---

## 3. Resale evidence (sold/comps) source matrix

The sold gate is the binding constraint. Current verified state of eBay sold-data access:

| Source | Sold data? | Programmatic? | Credential | Window | Notes |
|---|---|---|---|---|---|
| eBay Browse API | NO (active only) | yes | Developer key | n/a | never satisfies sold gate |
| eBay Finding API `findCompletedItems` | was yes | decommissioned Feb 2025 | n/a | n/a | removed; calls now error |
| eBay Marketplace Insights API (`item_sales/search`) | YES | yes | Business-level approval (Application Growth Check) | ~90 days | "Limited Release", closed to new applicants |
| Terapeak / "Product Research" (Seller Hub) | YES (aggregated: avg price, sell-through, volume) | NO (browser only, no export/JSON) | eBay seller account | ~3 years history | free with seller account; daily query caps; manual |
| CompsAPI (`api.compsapi.com`) | YES | yes (REST) | free key (100 searches/mo) | up to 1,095 days | third-party; reports real accepted best-offer price |
| SoldComps (`sold-comps.com`) | YES | yes | free tier / paid | ~90 days | third-party |
| Trawl | YES | yes | license | varies | third-party |
| Apify "eBay comps / sell-through" actors | YES (sold + active + sell-through) | yes | Apify account (pay per result, ~$0.05/product) | 7/30/90 days | third-party, licensed API not account-scraping |

Phase 1 policy classification of these routes:

- Terapeak/manual = `authenticated_manual` (confidence cap 85; every observation needs operator,
  timestamp, evidence reference).
- CompsAPI / SoldComps / Trawl / Apify = `licensed_third_party` (confidence cap 80; requires permitted
  use review; must record provider + license reference + whether the value is direct, modeled, or
  scraped-derived).
- Marketplace Insights = `official_api`, but effectively BLOCKED until eBay approves a business case.

---

## 4. Required vs optional evidence fields

Phase 1 already owns this normatively in `docs/freshness-policy.md` §3 and the runtime
`recommend()`/`validate_resale_evidence()` gates. The table below is the Phase 2-facing summary; it
does not override the policy. BUY max ages are the strictest gates; FRESH/AGING/STALE control display.

### Required for a BUY_CANDIDATE (hard gates; missing/stale/conflicting => no BUY)

| Field | BUY max age | Consequence if missing/stale/conflicting |
|---|---:|---|
| identity (exact GTIN/UPC/EAN/ASIN/MPN + model + variation + condition + pack + region/version, confidence ≥ 0.95) | 30d | SKIP (`IDENTITY_NOT_PROVEN` / `IDENTITY_CONFLICT`) |
| source_price | 30m | RECHECK (`SOURCE_PRICE_NOT_CURRENT`) |
| stock_status | 30m | RECHECK (`STOCK_NOT_CURRENT`); explicit OUT_OF_STOCK => SKIP |
| sold evidence (median + count + 90d window, ≥3 clean like-condition comps, asking prices excluded) | snapshot ≤ 24h; sales within 90d | SKIP/WATCH/RECHECK per §5 |
| fees (marketplace + payment) | 24h | RECHECK (`COST_INPUT_NOT_CURRENT`) |
| shipping estimate (in + outbound) | 24h | RECHECK (`COST_INPUT_NOT_CURRENT`) |
| active listing count | 24h | RECHECK (`MARKET_CONTEXT_NOT_CURRENT`) |
| seller count | 24h | RECHECK (`MARKET_CONTEXT_NOT_CURRENT`) unless policy marks optional |
| (Amazon route only) inferred demand: BSR/rank-drop ≤ 24h + realized-price corroboration, tier ≥ C | 24h | SKIP (`DEMAND_EVIDENCE_UNAVAILABLE`) |

### Optional / supportive (never satisfy a required gate; only refine display or reduce confidence)

- `source_notes`, descriptive title, images, `source_url`.
- `volatility` (HIGH => WATCH; -10 confidence).
- `estimated_sold_quantity` (active-listing signal; not sold count).
- `asking_price` / `asking_currency` (active-listing market context only; must be scope-tagged
  `ACTIVE_ASKING`/`COMBINED` or it is rejected and downgraded to UNAVAILABLE).
- `seller_count` may be optional if an explicit policy marks it so; its absence is then a
  display-only -10 confidence, but a present-and-conflicting seller count still blocks BUY.

Zero is only a valid value when the provider explicitly reports zero; an absent value is MISSING, not
zero.

---

## 5. Fail-closed conditions (missing or stale resale evidence)

The system must emit no BUY when any of these hold (deterministic, from Phase 1):

1. Sold evidence is missing, invalid, or asking-price-only => evidence_type `UNAVAILABLE`; SKIP with
   `SOLD_EVIDENCE_UNAVAILABLE`. Active asking prices are never copied into sold fields
   (enforced in `evidence.normalize_resale_evidence` and `workflow.evaluate_opportunity`).
2. Sold snapshot older than the 24h buy gate => `SOLD_EVIDENCE_STALE`; RECHECK/SKIP.
3. `sold_count < 3` clean like-condition comps => WATCH when snapshot is fresh, RECHECK when it can be
   refreshed; never BUY (`SOLD_COUNT_BELOW_MINIMUM`).
4. No qualifying sales in the 90-day window => SKIP.
5. `evidence_observed_at` missing on a non-UNAVAILABLE record => validation error; record downgraded to
   UNAVAILABLE before economics (`EVIDENCE_TIMESTAMP_MISSING`).
6. `provenance` absent => validation error (`PROVENANCE_MISSING`); record downgraded.
7. Identity missing/unverified/conflicting (UPC/model/variation disagreement) => SKIP
   (`IDENTITY_NOT_PROVEN`), regardless of profit.
8. source_price not LIVE/FRESH (age > 30m) => RECHECK (`SOURCE_PRICE_NOT_CURRENT`); never BUY even when
   the computed spread is large.
9. stock MISSING/STALE/UNVERIFIED => RECHECK (`STOCK_NOT_CURRENT`); OUT_OF_STOCK => SKIP.
10. fees/shipping missing or stale => RECHECK (`COST_INPUT_NOT_CURRENT`).
11. Any required access is terms-BLOCKED (unapproved scraping, unresolved affiliate use, closed
    Marketplace Insights) => SKIP (`ACCESS_BLOCKED`), not a soft downgrade.
12. Any UNVERIFIED/MISSING/CONFLICTING/BLOCKED required field => confidence cap 0 and no BUY.
13. Confidence < 70 after caps => WATCH (`CONFIDENCE_BELOW_MINIMUM`), not BUY.

Discovery-layer additions (Phase 2 must enforce, independent of Phase 1):

- A discovery record with no source/store/URL reference and no observation timestamp is not a
  candidate: drop it before evaluation.
- A discovery "observed price" older than the source-price freshness window cannot be reused as a
  current source_price; it must be re-observed or the candidate routed to RECHECK.
- The batch pipeline must isolate per-candidate failures: one malformed candidate must not abort or
  silently poison the rest; it becomes an excluded/rejected diagnostic.

---

## 6. Marketplace constraints and credential assumptions

Credential assumptions (nothing has been collected or configured in this run; values are for the
operator to decide):

- eBay Developer Program: free sign-up; client-credentials OAuth for Browse/Deal/Marketing APIs
  (5,000 calls/day default). Sold data via Marketplace Insights requires Business approval and is
  currently closed. Sold data via Terapeak requires an eBay SELLER account (manual). Keep
  `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET` out of the repo (already handled in `config/.env.example`).
- Keepa: paid API key (entry ~€49/mo), inferred demand only; not required for M1.
- CompsAPI/SoldComps/Trawl/Apify: third-party keys; require a permitted-use/license review before
  they may feed the sold gate; record provider + license reference + data provenance in each record.
- Walmart: seller/approved-provider OAuth only; no competitor-price path. Manual.
- Best Buy: free key but affiliate/selling-oriented terms + ToU prohibition on automated collection;
  affiliate program page currently 404. Manual/research-only unless a human establishes an affiliate
  relationship.
- Slickdeals: commercial affiliate agreement (contact team); not self-serve.
- Reddit: commercial use requires a separate agreement; not an M1 source.
- Tactical Arbitrage: Amazon Professional seller account + subscription; no stable API.

Secrets never belong in opportunity records or the repo; the audit record carries `account_scope`,
`accessed_at`, and a statement that the account was authorized, but never credentials/cookies/tokens
(`docs/freshness-policy.md` §9).

---

## 7. Demo / sample mode

`examples/phase2-demo-candidates.json` is a verified 7-candidate synthetic batch. Each entry is a
complete Phase 1 `evaluate_opportunity` input (`source_candidate` + `resale_evidence` + `assumptions`)
plus a `discovery` reference and a documented `expected_outcome`. All 7 were executed through the live
Phase 1 runtime (`workflow.evaluate_opportunity`) and produced exactly these results:

| candidate_id | recommendation | reason code |
|---|---|---|
| demo-01-valid-buy | BUY_CANDIDATE | ALL_REQUIRED_GATES_PASS |
| demo-02-stale-source-price | RECHECK | SOURCE_PRICE_NOT_CURRENT |
| demo-03-stale-stock | RECHECK | STOCK_NOT_CURRENT |
| demo-04-missing-sold-evidence | SKIP | SOLD_EVIDENCE_UNAVAILABLE |
| demo-05-identity-mismatch | SKIP | IDENTITY_NOT_PROVEN |
| demo-06-low-sold-count | WATCH | SOLD_COUNT_BELOW_MINIMUM |
| demo-07-out-of-stock | SKIP | OUT_OF_STOCK |

The batch intentionally spans the full recommendation label set and the key fail-closed modes
(missing sold evidence, identity conflict, out-of-stock, stale price/stock), so rejection behavior is
visible in demo mode. All values are synthetic (`example.test` URLs, fake brands/UPCs); they are not
live market data. A verification driver that replays the batch through the runtime is available at
`examples/phase2-demo-candidates.json` consumers: the batch is shaped to feed the same normalization →
evaluation → ranking path as live mode; only the discovery/research inputs differ, matching
`PHASE_2_ARCHITECTURE.md` §3 "Demo/sample mode".

---

## 8. Uncertainty and conflicts

- eBay sold-data programmatic access is the single highest-uncertainty dependency. Marketplace Insights
  is "not open to new users"; third-party sold APIs exist but are not first-party and their
  longevity/ToS are not guaranteed. This is why M1 defaults to manual sold evidence.
- Keepa "free tier": a third-party GitHub project advertises "100 tokens/min free", but Keepa's own
  docs and a pricing review describe no free API tier (entry €49/mo; Keepa Pro includes 1 token/min).
  Treat "no free tier" as authoritative; do not build against a free tier that may not exist.
- Best Buy affiliate program link was reported 404 as of mid-Oct 2026; affiliate status is not
  confirmed. Treat Best Buy source-price as manual/research-only until a human confirms the program.
- "Deal" discovery quality (whether Slickdeals/Tactical Arbitrage produce resalable margin) is
  operational judgment, not something verified here; no profit claim is made for any live source.

---

## 9. Sources (provenance)

- eBay Developers Program — API call limits:
  https://developer.ebay.com/develop/api/buy/api_call_limits (Browse/Deal/Marketing 5,000/day).
- eBay Partner Network — optimizing/automating (free tier, Compatible Application Check to 100K/day):
  https://partnernetwork.ebay.com/solutions/step-4-optimizing-and-automating
- eBay Feed API (ITEM_ALL_ACTIVE / ITEM_ALL_ACTIVE_MARKETING EPN-only):
  https://developer.ebay.com/api-docs/buy/static/api-feed.html
- Sold-data state (Finding API decommissioned Feb 2025; Marketplace Insights limited release;
  Terapeak browser-only): sold-comps.com/alternatives and dev.to articles (multiple, cross-checked).
- CompsAPI: https://api.compsapi.com (100 searches/mo free, up to 1,095 days, accepted-offer price).
- Apify eBay comps/sell-through actor: https://apify.com/doesaiknow/ebay-comps-sell-through
- Keepa API docs and pricing: https://keepa.com/api-docs/ and revenuegeeks.com/software/keepa/api
- Slickdeals API (commercial): https://corp-site.slickdeals.net/api-sales/ ; third-party ReefAPI:
  https://reefapi.com/docs/slickdeals
- Reddit User Agreement / Data API Terms / free-tier limits:
  https://redditinc.com/policies/user-agreement-june-28-2025 , https://redditinc.com/policies/data-api-terms
- Walmart Marketplace API (seller/partner scope + OAuth):
  https://developer.walmart.com/us-marketplace/docs/introduction-to-marketplace-apis and terms page
- Best Buy Developer API (Products API, limits, terms):
  https://developer.bestbuy.com/apis , https://developer.bestbuy.com/legal , apis.io/providers/best-buy
- Arbitrage tool pricing/capabilities: tacticalarbitrage.com/pricing-plan , threecolts.com blog ,
  arbitragehero.com/blog/best-online-arbitrage-software (SourceMogul discontinued; SellerAmp SAS scope)
