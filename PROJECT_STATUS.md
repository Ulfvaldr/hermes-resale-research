# Project status

## Phase 2 milestone: bounded daily candidate batch

Phase 2 is implemented as a deterministic, bounded batch on top of the Phase 1 evaluator. The default sample path is credential-free and offline: discovery selects at most the requested limit, enrichment is adapter-owned, and `batch.evaluate_batch()` delegates every identity, freshness, evidence, economics, scoring, and recommendation decision to `workflow.evaluate_opportunity()`. Ranked items are evidence-backed and eligible; rejected candidates remain auditable but are excluded from presentation.

## Hermes to n8n integration

The resale decision remains the deterministic Phase 1 workflow in `src/hermes_resale_research/workflow.py`, with bounded batch orchestration in `batch.py`. `n8n_client.py` is transport only. The importable `n8n/workflows/daily-candidate-workflow.json` invokes the Python batch CLI through an Execute Command node and uses n8n for visible orchestration/status/presentation; it does not reimplement identity, freshness, evidence, economics, scoring, or recommendation logic.

Configuration:

- `N8N_RESALE_WEBHOOK_URL` (default: `http://localhost:5678/webhook/hermes-resale-evaluate`)
- `N8N_RESALE_TIMEOUT_SECONDS` (default: `15`)

Credential-free sample run:

```bash
PYTHONPATH=src python -m hermes_resale_research examples/phase2-demo-candidates.json --batch --limit 10 --markdown
```

For n8n, import the workflow, set `HERMES_RESALE_REPO` to the absolute repository path and `PYTHONPATH` to `<repo>/src` in the n8n process environment, and execute manually. Its nodes are Trigger -> Discover candidates -> Research/enrich -> Evaluate batch -> Rank -> Present results. The sample path needs no marketplace credentials; Execute Command permission and Python on the n8n host are required. The separate webhook client still fails closed for connection errors, non-2xx HTTP errors, invalid JSON responses, non-object responses, and invalid payloads.

The imported workflow uses `examples/phase2-demo-candidates.json`, runs inactive until manually started, and calls the CLI from the Evaluate batch node. Rank parses the CLI JSON and requires `research_only=true` and `human_approval_required=true`; Present results exposes `items`, `rejected`, and counts. It does not acquire live listings or implement business rules. A live n8n execution remains an operator prerequisite, not a claimed validation result.

## Current validation state

The Phase 2 batch implementation reports 36 unit tests passing, plus the existing n8n client and canonical fixture checks. Independent validation also confirmed the sample result shape (7 evaluated, 4 ranked, 3 rejected), deterministic ranking, evidence/provenance fields, canonical 18-fixture checks, CLI output, and workflow JSON structure. Re-run `PYTHONPATH=src python -m unittest discover -s tests -q`, the sample batch command, the canonical contract probe, `python -m json.tool n8n/workflows/daily-candidate-workflow.json`, and `git diff --check` against the final repository state before issuing a final acceptance verdict.

## Local candidates viewer

The local viewer in `src/hermes_resale_research/viewer.py` is a thin, read-only presentation layer over a Phase 2 JSON report. `--demo` runs `examples/phase2-demo-candidates.json` through the existing batch CLI with no credentials, network, n8n, or database. `--report path/to/report.json` loads an already-generated local report and does not rerun evaluation. Both modes require the report safety contract (`research_only=true` and `human_approval_required=true`); malformed or unsafe input fails closed.

Start it from the repository root with `PYTHONPATH=src python -m hermes_resale_research.viewer --demo`, then browse to `http://127.0.0.1:8765/`. Use `--host` and `--port` only when a different local bind is needed. The page preserves Phase 2 ranking order, displays null/missing evidence as `Unavailable`, and keeps rejected/skipped records in a separate audit section with provenance, failed gates, and reason codes. It does not sort, score, estimate, fetch links, write reports, purchase, checkout, or list.

If Phase 2 output is unavailable, generate it first with `PYTHONPATH=src python -m hermes_resale_research examples/phase2-demo-candidates.json --batch --limit 10 > report.json`, then pass `--report report.json`. If the report has no `items`, the evaluator found no evidence-backed candidates that passed presentation filters; inspect `rejected`. Do not “fix” missing evidence in the viewer or substitute active asking prices for sold evidence. Detailed setup and troubleshooting are in `docs/phase2-viewer-setup.md`.

## Boundaries and limitations

Hermes handles orchestration, n8n handles optional visual integration, the Python runtime is the deterministic source of truth, and the local viewer only presents completed Phase 2 output. n8n and the viewer must not duplicate scoring, economics, freshness, identity, or recommendation logic. Synthetic fixtures are not live market data, sold evidence remains manual or separately approved, and a human remains the final decision-maker.

No commit, merge, or push has been performed. Do not merge or push these changes without explicit human approval. Keep credentials, cookies, tokens, marketplace responses, and local runtime state out of the repository.

## Operating decision and next steps

The current safe operating mode is offline sample mode or manually supplied/approved evidence. Optional eBay credentials in `config/.env.example` are not required for the demo and must remain local. Before enabling a live adapter, confirm provider terms, permitted research use, timestamp/provenance capture, sold-comps quality, and a human review procedure. The next implementation step is an approved read-only evidence adapter; it must preserve the Python evaluator as the source of truth and add tests before any cutover.

Human approval is required before commit, merge, push, deployment, credential use, or any purchase/listing action.
