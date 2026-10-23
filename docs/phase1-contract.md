# Hermes Resale Research — Phase 1 implementation contract

Status: planning contract; intentionally uncommitted until human review.
Branch: `phase-1-contract` (created from `main`). Human controls merge and push.

## 1. Approved scope and non-goals

Phase 1 is a small, agent-first, research-only workflow:

1. A human supplies a source candidate (a Walmart and/or Best Buy public-page observation, including its observed price and stock).
2. The core normalizes and verifies product identity.
3. Deterministic freshness gates validate timestamps and provenance.
4. Normalized eBay resale evidence is ingested; active asking prices are never treated as sold evidence.
5. Deterministic economics and transparent scoring produce one of `BUY_CANDIDATE`, `WATCH`, `RECHECK`, or `SKIP`.

Retained resale channel: eBay. Walmart and Best Buy are manual/research-only source inputs; no automated source-price feed is in Phase 1. Live eBay access is an adapter boundary and requires external approval/setup; fixtures and manual evidence must run without credentials.

Explicitly out of scope: automatic purchasing, automatic listing, automated Walmart/Best Buy price adapters or scraping, dashboard-first UI, additional marketplaces, and LLM arithmetic or production freshness decisions. Do not claim live access that has not been legitimately configured.

## 2. Branch/worktree discipline

- Never develop directly on `main`.
- The Phase 1 integration line is `phase-1-contract`; implementation workers should use a dedicated feature branch/worktree based on it (one active writer per worktree).
- Keep the planning document and implementation changes uncommitted unless the human explicitly requests a commit.
- Veritas reviews the implementation before any human-controlled merge/push.
- Generated output, runtime state, credentials, cookies, API tokens, downloaded marketplace responses, personal source notes, and local caches must remain outside Git. Use fixtures with synthetic or deliberately redacted values for reproducible tests.

## 3. Target module layout

```
src/hermes_resale_research/
  models.py          # dataclasses/enums for all contracts
  identity.py        # deterministic identity comparison and conflict handling
  freshness.py       # timestamp/provenance classification and gates
  evidence.py        # eBay evidence normalization and adapter protocol
  economics.py       # documented, deterministic formulas and rounding
  scoring.py         # explainable score after hard gates
  recommendations.py # decision mapping and reason codes
  workflow.py        # evaluate_opportunity entry point
  adapters/          # optional read-only eBay adapter; no business logic

tests/
  fixtures/          # machine-readable deterministic contract cases
  ...
```

The core must be callable without a UI, network, paid service, or credential. A CLI is optional and thin.

## 4. Data contracts

### SourceCandidate

Required/known fields: `source_marketplace`, `source_url`, `product_name`, `brand`, `model`, optional `asin`, `upc`, `ean`, `gtin`, `manufacturer_part_number`, `variation_attributes` (including pack quantity, size, color, generation/version, and bundle contents), `condition`, `source_price`, `stock_status`, `source_observed_at`, `source_notes`, `provenance`, and `confidence`.

Manual input must retain the supplied timestamp, provenance, and confidence. It must not be represented as automatically live or verified.

### ResaleEvidence

Fields: `resale_marketplace` (eBay), product identifiers, `recent_sold_median`, `sold_count`, `sold_window`, `active_listing_count`, `seller_count`, `evidence_observed_at`, explicit `evidence_type` (`OBSERVED`, `INFERRED`, `ESTIMATED`, or `UNAVAILABLE`), `source/provenance`, and `confidence`. Active listings are separate fields and cannot satisfy sold-evidence requirements.

### IdentityResult

Return `status` (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`, `REJECT`), `matched_fields`, `conflicting_fields`, and deterministic `reason_codes`. Exact ASIN/UPC/EAN/GTIN/model/variation/pack-size/generation conflicts fail closed. Title similarity alone cannot produce `VERIFIED` or `HIGH`.

### FreshnessResult

Return per-field status, overall status, observed timestamps, age/window metadata, provenance, and reason codes. States are `LIVE`, `FRESH`, `AGING`, `STALE`, and `UNKNOWN`. Critical fields include source price, stock, resale evidence, fees/shipping assumptions, and identity evidence.

### EconomicsResult / ScoreResult / OpportunityAssessment

Economics must expose acquisition cost, tax, inbound/outbound shipping, marketplace/payment fees, packaging, return allowance, expected resale price, break-even resale price, expected net profit, ROI, margin, and capital at risk, with explicit missing-data behavior and documented rounding. Scoring must expose component values, risk flags, and explanation; hard gates run before weighted scoring.

The final assessment must include `identity`, `freshness`, `economics`, `market`, `decision`, and metadata (`evaluated_at`, source provenance, resale provenance). `decision` contains recommendation, score, reason codes, failed gates, confidence, and human recheck requirements.

## 5. Interfaces and decision rules

Recommended callable interfaces (names may be adapted without changing semantics):

```python
compare_identity(source, resale_product) -> IdentityResult
classify_freshness(evidence, now) -> FreshnessResult
normalize_resale_evidence(raw) -> ResaleEvidence
evaluate_economics(source, resale, assumptions) -> EconomicsResult
score_opportunity(identity, freshness, economics, market) -> ScoreResult
recommend(identity, freshness, economics, score) -> Decision
evaluate_opportunity(source_candidate, resale_evidence, assumptions, now=None) -> OpportunityAssessment
```

`BUY_CANDIDATE` requires every critical identity, freshness, evidence, and economics gate to pass. It must always include: “final source price and stock recheck required before purchase”. `RECHECK` is for stale/uncertain critical observations or missing confirmation that may be resolved by a new observation. `WATCH` is a potentially viable opportunity that does not yet meet buy thresholds without being a hard failure. `SKIP` is for hard identity conflicts, unavailable/out-of-stock source, insufficient or invalid evidence, failed economics, or disqualifying risk. No recommendation may bypass a failed hard gate merely because the spread or score is large.

## 6. Freshness blocker to resolve before coding

The repository currently contains no approved machine-readable freshness thresholds, age windows, timezone/clock policy, or exact boundary behavior. The earlier readiness contract says these semantics are approved and must be deterministic, but this repository does not yet carry their authoritative values. Before implementing `freshness.py` or encoding fixture expectations, the implementer must locate the approved freshness artifact/fixture package and copy its exact thresholds, critical-field rules, and reason codes into the repository contract. Do not invent thresholds, silently substitute “recent”, or use an LLM to decide freshness. If the authoritative semantics cannot be located, stop and report the blocker rather than coding guessed behavior.

## 7. Required validation

Bring in the canonical 18 machine-readable cases: strong valid opportunity; stale source price; stale stock; exact identifier mismatch; variation/pack-size mismatch; fees destroy margin; shipping destroys margin; insufficient sold evidence; out-of-stock source; high volatility; borderline ROI; borderline net profit; missing critical timestamp; inferred-only evidence; and valid `WATCH`, `RECHECK`, `SKIP`, and `BUY_CANDIDATE` cases. Normal tests must be offline and deterministic, prove fail-closed behavior, and verify identity, freshness, economics, scoring, recommendation, reason codes, and same-input determinism.

External setup remains a later gate: eBay Developer Program/EPN approval for any live read-only integration and a compliant sold-data route (Terapeak UI or approved provider). No credential, token, cookie, or live response belongs in the repository.
