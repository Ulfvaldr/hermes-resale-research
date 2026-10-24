# Phase 2 viewer data contract

## Purpose and boundary

The Simple Daily Candidates Viewer is a local, read-only presentation layer over an existing Phase 2 batch report. It must not evaluate candidates or infer new business decisions. The Python Phase 1/Phase 2 runtime remains authoritative for identity, freshness, evidence validity, economics, scoring, ranking, recommendation, and fail-closed behavior.

The viewer must not implement or duplicate `evaluate_opportunity`, scoring, economics, freshness, identity matching, evidence thresholds, recommendation rules, or ranking. It only parses the report, preserves its `items` order, and renders values and provenance. It must not purchase, checkout, list, submit orders, call marketplace APIs, request credentials, or write back to the report.

## Input and discovery

Preferred input is a JSON report produced by the batch CLI:

```text
PYTHONPATH=src python -m hermes_resale_research examples/phase2-demo-candidates.json --batch --limit 10
```

For the credential-free demo, the viewer should default to the repository fixture `examples/phase2-demo-candidates.json`, run or load its deterministic batch result, and show an explicit synthetic/demo label. A simple implementation may instead consume a checked-in generated report if it is clearly identified as synthetic. No network, n8n instance, database, marketplace credential, `.env` secret, or live adapter is required for demo mode.

For normal local use, accept an explicit report path (recommended) or a configured local report directory. If a file is absent, malformed, or has the wrong safety contract, show a clear read error and do not invent or partially score candidates. A viewer fallback may show the bundled demo only when explicitly selected or when the UI labels the fallback prominently; it must never silently present demo data as live data.

The report envelope is:

```json
{
  "title": "Today's Resale Opportunity Candidates",
  "generated_at": "ISO-8601 timestamp",
  "bounded_limit": 10,
  "candidate_count": 7,
  "evaluated_count": 7,
  "items": [],
  "rejected": [],
  "research_only": true,
  "human_approval_required": true
}
```

The viewer should require both safety flags to be true before rendering recommendations. JSON numeric economics may be serialized as strings (for example, `"40.00"`); display them as supplied and do not recompute them.

## Ranked item fields

`items` is already deterministically ranked by Phase 2. Rank is the 1-based position in this array; do not sort, filter, or recalculate ranking in the UI. Each item can contain:

| Field | Required rendering | Meaning/source |
|---|---|---|
| `candidate_id` | optional audit identifier | Stable Phase 2 candidate identity. |
| `product_name` | required | Product name selected by Phase 2. |
| `source_store` | required | Source/store label normalized by Phase 2. |
| `source_price` | required; show unavailable explicitly if null | Observed acquisition/source price. |
| `expected_resale_price` | required; show unavailable explicitly if null | Phase 1 economics output. |
| `estimated_net_profit` | required; emphasize | Phase 1 economics output. |
| `roi` | required; emphasize | Phase 1 economics output; display as a value, not a newly calculated percentage. |
| `break_even_price` | required | Phase 1 economics output. |
| `recommendation` | required; emphasize | Existing decision label, such as `BUY_CANDIDATE`, `WATCH`, or `RECHECK`. Render it verbatim. |
| `confidence` | required | Existing decision confidence. Do not convert it into a new score. |
| `evidence_quality` | required | Existing Phase 2 presentation label (`HIGH`, `MEDIUM`, `LOW`, or `REJECTED`). |
| `explanation` | required | Short explanation assembled from authoritative score/reason codes. Render only; do not rewrite into a recommendation. |
| `failed_gates` | optional compact status | Existing gate failures; preserve exact codes. |
| `reason_codes` | optional compact status | Existing decision reason codes; preserve exact codes. |
| `eligible` | required safety/display flag | Phase 2 presentation eligibility. Never infer eligibility from profit or recommendation text. |
| `human_approval_required` | required safety/display flag | Must remain visible or represented by the global safety notice. |

Missing values must be shown as `Unavailable`/`Not provided`, not `0`, an empty string, or a derived estimate.

## Expanded evidence and provenance

An expandable details section for each item should expose the original objects without changing them:

- `source_provenance`: source URL/reference, store/discovery metadata, observation timestamps, and identity/source notes when present.
- `resale_provenance`: resale evidence source/reference, evidence type, observation timestamps, marketplace context, and provenance notes.
- `failed_gates` and `reason_codes`: exact machine-readable explanations for caution or rejection.
- `candidate_id`: useful for tracing the card back to the batch input.

Render external URLs as links only if they are present in the local report; do not fetch them automatically. Treat provenance as evidence/audit information, not as permission to act.

## Rejected, skipped, and missing evidence

Render `rejected` separately from ranked `items`, with its count and exact `recommendation`, `explanation`, `failed_gates`, `reason_codes`, and provenance. Rejected candidates are intentionally excluded from the ranked opportunity view. A `SKIP`/`REJECTED` record must never be promoted into `items` by the UI.

Missing or unavailable evidence is represented by null fields and/or exact codes such as `SOLD_EVIDENCE_UNAVAILABLE`, `SOLD_EVIDENCE_STALE`, `IDENTITY_NOT_PROVEN`, `SOURCE_PRICE_NOT_CURRENT`, `STOCK_NOT_CURRENT`, or `OUT_OF_STOCK`. Explain those values plainly, but do not substitute active asking prices for sold evidence or calculate replacement economics. If there are no ranked items, show that no evidence-backed candidates passed the presentation filter and retain the rejected audit view.

## Acceptance criteria for the viewer

1. Starts locally with Python 3.11+ and no credentials, network access, n8n, or database in demo mode.
2. Loads the Phase 2 report contract above and refuses malformed input or false/missing safety flags.
3. Preserves `items` array order exactly and displays a 1-based rank.
4. Displays every required ranked field, with explicit unavailable states for null/missing values.
5. Displays expandable source and resale provenance plus reason/gate details without mutation.
6. Shows rejected/skipped candidates separately and makes missing evidence understandable.
7. Contains no Phase 1/Phase 2 scoring, economics, freshness, identity, recommendation, or ranking implementation.
8. Is read-only: no purchase, listing, checkout, write-back, secret handling, or external fetch behavior.
9. Includes a clearly labeled credential-free synthetic demo path and documents the explicit report-path/local discovery mechanism.
10. Existing Phase 1/Phase 2 tests remain unchanged and passing; viewer parsing/rendering tests should cover order preservation, null evidence, safety flags, and rejected records.
