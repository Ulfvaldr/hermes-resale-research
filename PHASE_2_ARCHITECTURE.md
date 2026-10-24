# Phase 2 architecture and operating notes

## Scope

Phase 2 is a bounded daily candidate batch. It discovers a limited set of JSON-shaped candidates, optionally enriches them, evaluates each through the existing Phase 1 workflow, ranks eligible results, and presents a human-readable report. It is research-only: no purchase, checkout, payment, listing, order, or dashboard action exists in this repository.

## Component boundary

```text
sample or approved adapter input
        -> discover_candidates / enrich_candidates
        -> workflow.evaluate_opportunity (authoritative decision seam)
        -> deterministic rank + rejected audit
        -> JSON or Markdown presentation
        -> optional local n8n transport/orchestration
        -> optional local read-only candidates viewer
```

`src/hermes_resale_research/batch.py` owns bounded selection, adapter error capture, presentation fields, deterministic ordering, and rejected-candidate retention. `workflow.py` remains authoritative for identity, freshness, evidence, economics, score, reason codes, and recommendation. n8n transports and presents; it must not duplicate those rules.

`src/hermes_resale_research/viewer.py` is downstream of the JSON report. In `--report` mode it loads and validates the safety envelope, preserves the `items` array order, and renders values/provenance without recalculation. In `--demo` mode it invokes the existing batch CLI against the checked-in synthetic fixture. The viewer is not another evaluator, scheduler, source adapter, or n8n replacement.

## Safety and fail-closed contract

- Every report sets `research_only` and `human_approval_required` to true.
- Malformed candidates are rejected as `SKIP`; duplicate IDs keep the first record.
- Missing, invalid, asking-price-only, or stale sold evidence cannot produce `BUY_CANDIDATE`.
- Identity conflicts, unavailable/out-of-stock sources, and invalid economics are hard refusals.
- Rejected candidates remain in `rejected` for audit and are excluded from `items` unless explicitly requested by library callers.
- A buy recommendation always requires a final source price and stock recheck before purchase.

## Demo and live-source modes

Demo mode uses `examples/phase2-demo-candidates.json`, needs Python 3.11+ and no credentials, network, n8n, or database. Live sources are not included in this milestone. Any future adapter must be read-only, approved for its provider terms and research role, and must normalize evidence with timestamps, identifiers, condition/pack/region, source references, and confidence before calling the Python evaluator.

## n8n workflow

The importable workflow is inactive sample mode with the exact sequence `Trigger -> Discover candidates -> Research/enrich -> Evaluate batch -> Rank -> Present results`. `Evaluate batch` invokes the repository CLI through Execute Command. `Rank` parses stdout JSON and checks both safety flags. `Present results` emits the ranked items, rejected audit, counts, title, timestamp, and safety flags. Local/self-hosted n8n with Python, `HERMES_RESALE_REPO`, `PYTHONPATH=<repo>/src`, and Execute Command enabled is required; hosted/queue-mode n8n may not support this node.

## Validation and known limitations

Phase 2 implementation and independent review reported 36 unit tests passing, canonical 18-fixture checks passing, deterministic sample output of 7 evaluated/4 ranked/3 rejected, valid workflow JSON, and a simulated n8n command path. Live n8n import/execution and live marketplace acquisition were not performed. Synthetic fixtures are not market data, sold evidence remains manual or separately approved, and provider terms/credentials are unresolved until a future adapter is approved.

For viewer operation, start from the repository root with Python 3.11+: `PYTHONPATH=src python -m hermes_resale_research.viewer --demo`. For a real local report, generate or obtain Phase 2 JSON first and use `--report`; an absent/malformed report or false/missing safety flag is an operator error, not a reason to add fallback scoring. Null evidence remains `Unavailable`, and rejected records remain separate for audit.

## Human control

This working tree must not be merged or pushed without explicit human approval. Human review is also required before credentials are enabled, a live adapter is used, or any recommendation is acted upon. The human verifies evidence, provenance, identity, freshness, economics, and final source price/stock.