# Hermes Resale Research: executable freshness and refusal rules

Status: research-only MVP contract
Version: 1.0
Time basis: UTC, ISO-8601 timestamps

## Provenance and scope

This policy artifact preserves the freshness and refusal rules from the authoritative attachment `C:\Users\rvanb\AppData\Local\hermes\kanban\attachments\t_6932736a\freshness-refusal-rules.md` (`freshness-refusal-rules.md`). That attachment is the authority for this repository copy.

This repository artifact is not an exact reconstruction of any unrecoverable `t_462dc2f7` package, and it does not rely on that package as authority. It extracts and preserves the rules present in `freshness-refusal-rules.md` for use by the executable fixture contract.

Rule origin labels used below:

- PRESERVED: directly extracted from `freshness-refusal-rules.md`.
- NEWLY DEFINED: a minimum rule added because a required rule was genuinely absent from the authority; any such rule requires Veritas approval before implementation.

NEWLY DEFINED rules in this document: none. All normative rules below are PRESERVED from `freshness-refusal-rules.md`.

This document is normative for a first implementation. A producer MUST preserve the raw observation, source class, observed_at, retrieved_at, and policy version. A consumer MUST NOT infer freshness from a human-readable label or from an absent timestamp.

## 1. Configurable constants

Origin: PRESERVED from `freshness-refusal-rules.md`.

The defaults below are policy constants, not provider claims. They may be changed only by a versioned policy change.

```yaml
policy_version: freshness-v1
clock_skew_future_tolerance: 5m
source_price:
  live_max_age: 10m
  fresh_max_age: 30m
  aging_max_age: 2h
  stale_after: 7d
  buy_max_age: 30m
stock:
  live_max_age: 10m
  fresh_max_age: 30m
  aging_max_age: 1h
  stale_after: 24h
  buy_max_age: 30m
sold_evidence:
  snapshot_fresh_max_age: 24h
  snapshot_aging_max_age: 72h
  snapshot_stale_after: 7d
  buy_max_snapshot_age: 24h
  required_sales_window: 90d
  ebay_min_clean_comps_for_buy: 3
  amazon_inferred_demand_max_age: 24h
active_competition:
  fresh_max_age: 24h
  aging_max_age: 72h
  stale_after: 7d
  buy_max_age: 24h
seller_count:
  fresh_max_age: 24h
  aging_max_age: 72h
  stale_after: 7d
  buy_max_age: 24h
fees:
  fresh_max_age: 24h
  aging_max_age: 72h
  stale_after: 7d
  buy_max_age: 24h
shipping_estimate:
  fresh_max_age: 24h
  aging_max_age: 72h
  stale_after: 7d
  buy_max_age: 24h
identity_evidence:
  fresh_max_age: 30d
  buy_max_age: 30d
  hard_conflict_max_age: unlimited
conflict_tolerance:
  monetary_absolute: 0.01 USD
  source_price_relative: 1%
  stock_status: any disagreement
  identifiers: any disagreement
  counts_relative: 10%
  counts_absolute: 1
```

`buy_max_age` is the strictest age gate for BUY_CANDIDATE. `fresh_max_age` and `aging_max_age` control display and research routing. A record older than `stale_after` is stale even if it is still useful as historical context.

For a provider that supplies only one timestamp, use it as both observed_at and retrieved_at only when the provider explicitly documents that meaning; otherwise mark the timestamp quality UNVERIFIED.

## 2. Field contract and freshness evaluation

Origin: PRESERVED from `freshness-refusal-rules.md`.

Every observation has:

```json
{
  "field": "source_price",
  "value": 39.99,
  "currency": "USD",
  "observed_at": "2026-10-18T12:00:00Z",
  "retrieved_at": "2026-10-18T12:01:00Z",
  "source_kind": "official_api|authenticated_manual|licensed_third_party|manual_fallback|public_page",
  "source_id": "provider/request-or-note-id",
  "timestamp_quality": "PROVIDER_ASSERTED|USER_ENTERED|INFERRED|MISSING",
  "status": "LIVE|FRESH|AGING|STALE|MISSING|CONFLICTING|UNVERIFIED|BLOCKED"
}
```

Age is `evaluation_time - observed_at`. A negative age beyond the five-minute clock-skew tolerance is `UNVERIFIED`. Retrieved_at does not make an old observation fresh.

Time basis is UTC with ISO-8601 timestamps.

The evaluator runs in this order:

1. If policy or access rules prohibit use of the source for the intended role, status is `BLOCKED`.
2. If two usable observations for the same field disagree beyond the field tolerance, status is `CONFLICTING`.
3. If the value or observed_at is absent, status is `MISSING`.
4. If timestamp quality is INFERRED, USER_ENTERED without a supporting record, or otherwise cannot be authenticated, status is `UNVERIFIED`.
5. If age exceeds stale_after, status is `STALE`.
6. If age exceeds aging_max_age, status is `AGING`.
7. If age exceeds fresh_max_age, status is `AGING`; otherwise use `LIVE` only when the provider explicitly claims real-time state and age <= live_max_age, else `FRESH`.

Boundary semantics: the preserved rule uses `exceeds` for stale_after, aging_max_age, and fresh_max_age thresholds. Therefore an observation exactly at the relevant maximum age is still within that threshold; the next worse status begins only when age is greater than the threshold. BUY gates use the same maximum-age semantics: age must be less than or equal to `buy_max_age` / `buy_max_snapshot_age` to pass.

The severity order for decisions is:

`BLOCKED > CONFLICTING > MISSING > UNVERIFIED > STALE > AGING > FRESH > LIVE`.

The worst status wins across observations for one field and across required fields for a route. A later observation does not erase an earlier conflict; it must supersede it by matching the same identity, variation, currency, and source scope. Apply `conflict_tolerance`: monetary values conflict when absolute difference exceeds $0.01 and source price also differs by more than 1%; stock or identifiers conflict on any disagreement; counts conflict when both the absolute and relative thresholds are exceeded.

## 3. Required field thresholds and consequences

Origin: PRESERVED from `freshness-refusal-rules.md`.

| Field | Timestamp source | Display treatment | BUY max age | Missing/old/conflicting consequence |
|---|---|---:|---:|---|
| source_price | source observation | show through 7d with label | 30m | MISSING/UNVERIFIED/STALE/CONFLICTING => no BUY; RECHECK |
| stock_status | source observation | show through 24h with label | 30m | MISSING/STALE => no BUY; RECHECK; explicit OUT_OF_STOCK => SKIP |
| sold evidence snapshot | sold provider/manual result | show through 90d if marked historical | 24h | no usable evidence => route-specific SKIP or WATCH; stale => RECHECK/SKIP |
| sold price/count/window | evidence's own sale dates | historical window 90d | 90d sale window | asking price is not sold evidence; count < 3 clean eBay comps => no BUY |
| active listing count | destination snapshot | show through 7d | 24h | missing => WATCH/RECHECK; conflict => no BUY |
| seller count | destination snapshot | show through 7d | 24h | missing => WATCH/RECHECK unless policy marks optional; conflict => no BUY |
| fees | fee schedule/quote observation | show through 7d | 24h | missing or stale => no BUY; RECHECK |
| shipping estimate | source/destination quote | show through 7d | 24h | missing or stale => no BUY; RECHECK |
| product identity evidence | identifiers + matching observation | show through 30d | 30d | missing/unverified => SKIP; conflict => SKIP |
| inferred Amazon demand | Keepa/other permitted provider | show through 7d | 24h | missing/stale => SKIP for Amazon route |

For active listing count and seller count, zero is a valid value only when the provider explicitly reports zero. An absent value is MISSING, not zero.

## 4. Source class and access/refusal rules

Origin: PRESERVED from `freshness-refusal-rules.md`.

`source_kind` is not a confidence score and cannot bypass freshness or compliance gates.

- `official_api`: usable only after account, purpose, and terms approval for this research role. eBay Browse is active-listing evidence only. Amazon Creators API is conditional on an active Associates account and current terms review.
- `licensed_third_party`: usable only after provider license and permitted-use review. Keepa is inferred demand, not sold count. SoldComps/Trawl are third-party sold evidence and require explicit approval.
- `authenticated_manual`: allowed as a human research fallback when the operator has the required account. Terapeak/Sold items can supply sold evidence, but every observation must record user, timestamp, and evidence reference.
- `manual_fallback`: allowed for research display and WATCH/RECHECK. It cannot produce BUY_CANDIDATE unless timestamp, identity, evidence reference, and required fields satisfy the same gates as automated data.
- `public_page` or scraped data: not an approved primary path. If used at all, status is BLOCKED unless compliance review explicitly approves the source and terms.

Any source with an unresolved terms restriction is `BLOCKED` for the affected role, not merely low confidence. Walmart and Best Buy source-price APIs are therefore manual-only pending human terms approval. Scraping is never an automatic fallback.

## 5. Identity rules and critical evidence requirements

Origin: PRESERVED from `freshness-refusal-rules.md`.

Identity must be evaluated before economics and before freshness can enable a decision.

Required identity evidence for a BUY_CANDIDATE:

- exact product identifier match where available: GTIN/UPC/EAN, ASIN, or manufacturer part number;
- matching model and variation attributes;
- source and destination evidence refer to the same condition, pack count, region, and version;
- `identity_confidence >= 0.95` and no hard conflict.

A title-only match is UNVERIFIED and results in SKIP. A conflicting UPC/model/variation is CONFLICTING and results in SKIP, regardless of profit. Identity evidence older than 30 days requires RECHECK; a catalog identity conflict is always a hard refusal.

## 6. Sold-evidence rules by destination

Origin: PRESERVED from `freshness-refusal-rules.md`.

### eBay destination

A BUY_CANDIDATE requires:

- at least three clean, like-condition completed-sale comps;
- sale dates within the 90-day required sales window;
- sold snapshot age <= 24 hours;
- sold price statistic and count, with asking prices excluded;
- active listing count and seller count no older than 24 hours, or an explicit WATCH/RECHECK result.

Terapeak/manual or an approved third party may satisfy the evidence requirement. eBay Browse active listings alone never satisfies it. If `sold_count < 3`, return WATCH when evidence is otherwise recent and RECHECK when the source may be refreshed; never BUY. If there are no qualifying sales in 90 days, return SKIP.

### Amazon destination

Amazon has no native sold feed in this contract. A BUY_CANDIDATE requires all of:

- permitted current source price and stock;
- inferred demand observation (for example BSR/rank-drop evidence) <= 24 hours;
- realized-price history or equivalent permitted corroboration;
- evidence confidence tier C or better, explicitly labeled inferred;
- no claim that inferred demand is a literal sold count.

Missing or stale inferred demand is SKIP. An asking-price-only observation, coarse “bought in past month” text without a permitted supporting use, or price history without demand evidence is not enough for BUY.

## 7. Decision algorithm and route mappings

Origin: PRESERVED from `freshness-refusal-rules.md`.

The route evaluator returns exactly one of `BUY_CANDIDATE`, `WATCH`, `RECHECK`, or `SKIP`, plus stable reason codes.

```text
if any required access is BLOCKED:
    decision = SKIP (ACCESS_BLOCKED)
else if identity is MISSING, UNVERIFIED, or CONFLICTING:
    decision = SKIP (IDENTITY_NOT_PROVEN)
else if source_price is not LIVE or FRESH:
    decision = RECHECK (SOURCE_PRICE_NOT_CURRENT)
else if stock_status is STALE, MISSING, or UNVERIFIED:
    decision = RECHECK (STOCK_NOT_CURRENT)
else if stock_status explicitly says OUT_OF_STOCK:
    decision = SKIP (OUT_OF_STOCK)
else if fees or shipping are MISSING, STALE, UNVERIFIED, or CONFLICTING:
    decision = RECHECK (COST_INPUT_NOT_CURRENT)
else if route requires eBay sold evidence and sold gate fails:
    decision = WATCH or RECHECK or SKIP according to section 6
else if route is Amazon and inferred demand gate fails:
    decision = SKIP (DEMAND_EVIDENCE_UNAVAILABLE)
else if active competition or seller count is MISSING/STALE/CONFLICTING:
    decision = RECHECK (MARKET_CONTEXT_NOT_CURRENT)
else if economics net_profit < min_net_profit or ROI < min_roi or margin < min_margin:
    decision = SKIP (ECONOMICS_FAIL)
else if volatility is HIGH and no current recheck resolves it:
    decision = WATCH (VOLATILITY_HIGH)
else:
    decision = BUY_CANDIDATE
```

The exact economics minimums belong to the economics policy, but they MUST be explicit numeric configuration. This evaluator never treats unknown as zero and never lets a positive headline spread override a failed net-profit calculation.

A BUY_CANDIDATE is prohibited if any required field has status other than LIVE or FRESH, if any refusal reason exists, if any evidence is BLOCKED, or if a required value was manually substituted without an auditable observation.

BUY_CANDIDATE gates preserved for executable fixtures:

- no required access is BLOCKED;
- identity is proven, with required exact identifier/model/variation/condition/pack/region/version evidence and `identity_confidence >= 0.95`;
- every required field has status LIVE or FRESH;
- source_price and stock_status pass their 30-minute buy max ages;
- fees, shipping, sold snapshot, active competition, and seller count pass their 24-hour buy max ages where required;
- eBay sold evidence has at least three clean like-condition completed-sale comps within 90 days, with asking prices excluded;
- Amazon inferred-demand route, if used, has permitted current source price/stock, inferred demand <= 24 hours, realized-price corroboration, confidence tier C or better, and no claim that inferred demand is literal sold count;
- deterministic economics pass explicit numeric `min_net_profit`, `min_roi`, and `min_margin` configuration;
- volatility is not unresolved HIGH;
- confidence is at least 70 after deterministic caps and deductions;
- no refusal reason exists and no required value was manually substituted without an auditable observation.

WATCH/RECHECK/SKIP mapping preserved for sold-evidence and market-context failures:

- `sold_count < 3`: WATCH when the snapshot is fresh; RECHECK when the snapshot is stale or the source may be refreshed; never BUY.
- no qualifying sales in the 90-day sales window: SKIP.
- missing or stale Amazon inferred demand: SKIP.
- active competition or seller count missing/stale/conflicting: RECHECK for route-level market context unless an explicit policy marks the field optional; conflicts still prohibit BUY.

## 8. Confidence computation

Origin: PRESERVED from `freshness-refusal-rules.md`.

Confidence is a deterministic cap, not an invitation to override refusal rules.

Start with `100` and apply the largest applicable cap:

- official approved current data plus approved sold data: cap 95;
- authenticated manual sold evidence: cap 85;
- licensed third-party sold evidence: cap 80;
- inferred Amazon demand: cap 70;
- manual fallback source price/stock: cap 60;
- any AGING required field: cap 49 and no BUY;
- any UNVERIFIED/MISSING/CONFLICTING/BLOCKED required field: cap 0 and no BUY.

Additional deterministic deductions: 10 points for HIGH volatility, 10 for seller/competition data being optional-but-missing, and 5 for a borderline economics result. Confidence is rounded down to an integer. `BUY_CANDIDATE` requires confidence >= 70; this does not override any field gate.

## 9. Manual, third-party, and authenticated handling

Origin: PRESERVED from `freshness-refusal-rules.md`.

Manual records require `operator_id`, `captured_at`, source URL or evidence reference, exact value, currency, condition, and a free-text note only as supporting context. The note cannot replace a required structured field.

Third-party records require `provider`, `license_reference`, permitted-use review status, and whether the value is direct, modeled, or scraped-derived. Unapproved or terms-gray data is BLOCKED, not merely downgraded.

Authenticated sources require `account_scope` (seller/affiliate/research account), `accessed_at`, and a statement that the account was authorized for the operation. Credentials, cookies, and tokens MUST NOT be stored in the opportunity record.

If a source is unavailable, record `availability: UNAVAILABLE` and the attempted source. Do not synthesize a value from another field. An unavailable required source produces the route-specific refusal above.

## 10. Examples

Origin: PRESERVED from `freshness-refusal-rules.md`.

### Example A: normal eBay candidate

- identity: exact UPC and variation, FRESH, confidence 0.99;
- source price $40 and stock IN_STOCK, observed 8 minutes ago: LIVE;
- fees and shipping observed 10 minutes ago: FRESH;
- eBay sold snapshot observed 20 minutes ago, 12 clean comps in 90 days: FRESH;
- active listings/sellers observed 20 minutes ago: FRESH;
- economics pass thresholds, volatility NORMAL.

Result: `BUY_CANDIDATE`; reason `ALL_REQUIRED_GATES_PASS`.

### Example B: stale price

All fields above pass, but source price is 3 hours old. Status is STALE relative to the 30-minute buy threshold.

Result: `RECHECK`; reason `SOURCE_PRICE_NOT_CURRENT`. No BUY is emitted even when calculated profit is high.

### Example C: missing sold evidence

Source price and stock are current; eBay has active listings but no completed-sale evidence.

Result: `SKIP`; reason `SOLD_EVIDENCE_UNAVAILABLE`. Active asking prices are recorded but never relabeled as sold evidence.

For a recent but insufficient three-or-fewer-comps result, the deterministic result is `WATCH` with `SOLD_COUNT_BELOW_MINIMUM`; if a refresh can materially change it, use `RECHECK` instead. The implementation must choose one configured branch and keep it stable; this version uses WATCH when the snapshot is fresh and RECHECK when it is stale.

### Example D: conflicting observations

Two current source-price observations for the same identifier report $39.99 and $59.99, with no provider precedence configured. Status is CONFLICTING.

Result: `RECHECK`; reason `SOURCE_PRICE_CONFLICT`. If the conflict is not resolved, the final disposition becomes SKIP after the configured retry limit; never BUY.

### Example E: identity mismatch

Titles are similar, but UPC differs and one listing is a two-pack. Identity status is CONFLICTING.

Result: `SKIP`; reason `IDENTITY_NOT_PROVEN`. No amount of freshness or profitability can repair this.

### Example F: restricted access

A Walmart affiliate observation is technically available, but the intended competitor-price research use has not passed terms review.

Result: `SKIP`; reason `ACCESS_BLOCKED`. Manual review may create a new policy version; it cannot silently convert the existing observation to approved.

### Example G: Amazon inferred demand

Current Amazon source price/stock is approved and current. Keepa demand data is 30 hours old.

Result: `SKIP`; reason `DEMAND_EVIDENCE_UNAVAILABLE`. The record may be displayed as historical WATCH data, but it is not a BUY candidate.

## 11. Stable reason codes

Origin: PRESERVED from `freshness-refusal-rules.md`.

Implementations SHOULD emit these machine-readable codes, preserving the code when the human message changes:

`ACCESS_BLOCKED`, `IDENTITY_NOT_PROVEN`, `IDENTITY_CONFLICT`, `SOURCE_PRICE_NOT_CURRENT`, `STOCK_NOT_CURRENT`, `OUT_OF_STOCK`, `SOLD_EVIDENCE_UNAVAILABLE`, `SOLD_EVIDENCE_STALE`, `SOLD_COUNT_BELOW_MINIMUM`, `DEMAND_EVIDENCE_UNAVAILABLE`, `MARKET_CONTEXT_NOT_CURRENT`, `COST_INPUT_NOT_CURRENT`, `SOURCE_PRICE_CONFLICT`, `ECONOMICS_FAIL`, `VOLATILITY_HIGH`, `ALL_REQUIRED_GATES_PASS`.

## 12. Minimum audit record

Origin: PRESERVED from `freshness-refusal-rules.md`.

For every evaluated route, persist or emit:

- policy_version and evaluation_time;
- source and resale marketplace/role;
- all field values with status, observed_at, retrieved_at, and source_kind;
- identity match result;
- economics output from deterministic code;
- decision and ordered reason codes;
- confidence and cap reasons;
- whether any manual fallback or third-party evidence was used;
- refusal flag and the first failing gate.

The record is incomplete if it says only “stale” or “low confidence”; it must identify the field, threshold, observation age, and rule that fired.

## Provenance

This canonical policy was materialized from the authoritative attachment supplied by Hermes task t_6932736a (`freshness-refusal-rules.md`). This repository artifact does not claim exact reconstruction of any unrecoverable t_462dc2f7 package and does not use t_462dc2f7 as authority for the policy rules above. The policy rules are labeled PRESERVED from `freshness-refusal-rules.md`; no NEWLY DEFINED policy rules were added in this artifact.
