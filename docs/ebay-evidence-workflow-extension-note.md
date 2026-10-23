# eBay evidence and workflow extension note

Status: design note for the existing Phase 1 deterministic core. No contract changes are proposed.

## Existing contracts to preserve

- `SourceCandidate`, `ResaleEvidence`, `IdentityResult`, `FieldFreshness`, `FreshnessResult`, `EconomicsResult`, `ScoreResult`, `Decision`, and `OpportunityAssessment` are the data boundary in `src/hermes_resale_research/models.py`.
- `ResaleEvidence.evidence_type` is explicitly one of `OBSERVED`, `INFERRED`, `ESTIMATED`, or `UNAVAILABLE`; active listing/asking fields remain separate from sold evidence.
- `docs/freshness-policy.md` (`freshness-v1`) is normative: UTC timestamps, preserved observation provenance, fail-closed missing/unverified/blocked semantics, and the 24-hour eBay sold/market-context BUY age limits.
- The canonical Phase 1 package remains `tests/fixtures/canonical_phase1/fixtures.json`, with exactly 18 unique cases. Its schema/probe and expected refusal/recommendation cases must not be replaced by the older `tests/fixtures/opportunity_cases.json`.

## Concrete extension points

1. `adapter.py`
   - Extend the `EbayEvidenceAdapter` protocol only for read-only evidence acquisition. Existing `fetch_active_listings(query)` and `fetch_sold_evidence(query)` are the boundary; adapters must return normalized `ResaleEvidence` or an equivalent raw mapping that is normalized immediately.
   - Keep `UnavailableEbayAdapter` as the deterministic no-network implementation. A live adapter must not contain identity, freshness, economics, scoring, or recommendation business logic.

2. `evidence.py`
   - Keep `normalize_resale_evidence()` as the single normalization boundary and `validate_resale_evidence()` as the fail-closed validation boundary.
   - Preserve the rule that `asking_price` without `recent_sold_median` becomes `evidence_type="UNAVAILABLE"`; never copy an active asking price into sold-price fields.
   - Preserve validation/provenance reason codes and downgrade malformed or unsupported evidence before it reaches economics or recommendation logic.

3. `identity.py`
   - `compare_identity(source, resale)` must run before economics and before a BUY decision. Extend identity extraction here if an adapter introduces additional identifiers/variation attributes; hard conflicts remain `REJECT`.

4. `freshness.py`
   - `classify_freshness(evidence, now)` remains the only timestamp classifier. Adapter output should be converted into the existing per-field observation shape (`value`, `observed_at`, timestamp quality, provider-live/blocked/conflict metadata).
   - Use the existing `POLICY_VERSION`, profiles, buy-gate flags, and reason-code semantics; do not infer freshness from adapter labels or retrieval time.

5. `economics.py`, `scoring.py`, and `recommendations.py`
   - `evaluate_economics()` consumes explicit assumptions and the validated sold-derived resale price only.
   - `score_opportunity()` scores after hard gates and exposes components/risk flags.
   - `recommend()` owns the final fail-closed mapping, including sold-count minimums, missing market context, economics thresholds, and the required BUY recheck text.

6. `workflow.py`
   - `evaluate_opportunity(source_candidate, resale_evidence, assumptions, now=None)` is the single end-to-end evaluation seam. Any adapter orchestration should resolve/fetch evidence before calling this function, or add a thin wrapper that fetches then delegates to it; it should not duplicate the decision pipeline.
   - The returned `OpportunityAssessment` is the complete audit object: identity, freshness, economics, score, decision, market evidence, evaluation time, and both source/resale provenance.

## Canonical UNAVAILABLE representation

When eBay evidence cannot be obtained, is asking-price-only, is invalid, or is not approved for the intended role, represent it as:

```python
ResaleEvidence(
    resale_marketplace="eBay",
    evidence_type="UNAVAILABLE",
    recent_sold_median=None,
    sold_count=None,
    evidence_observed_at=None,
    provenance={"reason": "<stable reason>", "query": "<non-secret query>"},
)
```

The reason must be auditable (for example, `LIVE_EBAY_ACCESS_NOT_CONFIGURED` or validation errors), but credentials, cookies, tokens, and raw live responses do not belong in the record or repository. Active listing counts may be retained when independently observed, but they cannot satisfy the sold-evidence gate. In the current flow, invalid evidence is downgraded in `workflow.evaluate_opportunity()` and carries validation errors into provenance; recommendation then refuses BUY through `SOLD_EVIDENCE_UNAVAILABLE`/related gate codes.

## Single-opportunity evaluation order

For one source candidate and one eBay evidence result, the end-to-end path is:

`adapter (optional, read-only) -> normalize_resale_evidence -> validate_resale_evidence -> workflow.evaluate_opportunity -> _source -> compare_identity -> classify_freshness -> evaluate_economics -> score_opportunity -> recommend -> OpportunityAssessment`

The adapter must be resolved before this path; the deterministic core must remain callable with manual JSON/models and no network, credentials, or UI. Run the canonical 18-case probe independently after changes so fixture packaging remains a separate approved contract.
