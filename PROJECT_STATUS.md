# Project status

## Hermes to n8n integration

The resale decision remains the deterministic Phase 1 workflow in `src/hermes_resale_research/workflow.py`. `n8n_client.py` is transport only: it accepts the supplied JSON contract, POSTs it to an existing n8n webhook, and returns a compact structured result. It does not reimplement identity, freshness, evidence, economics, scoring, or recommendation logic.

Configuration:

- `N8N_RESALE_WEBHOOK_URL` (default: `http://localhost:5678/webhook/hermes-resale-evaluate`)
- `N8N_RESALE_TIMEOUT_SECONDS` (default: `15`)

Run locally with:

```bash
PYTHONPATH=src python -m hermes_resale_research --n8n examples/manual-evaluation.json
```

The client fails closed for connection errors, non-2xx HTTP errors, invalid JSON responses, non-object responses, and invalid payloads. A live n8n instance is not required for unit tests. This repository does not include an n8n workflow definition or export/import instructions, so the local endpoint and workflow must already exist for integration use. No marketplace credentials are needed.

## Current validation state

The documented n8n integration cleanup is complete. The current verification run reports 30 unit tests passing and `git diff --check` passing, including n8n client and final-newline checks. Independent review should rerun these checks against the final repository state before issuing a final acceptance verdict.

## Boundaries and limitations

Hermes handles orchestration, n8n handles optional visual integration, and the Python runtime is the deterministic source of truth. n8n must not duplicate scoring, economics, freshness, or recommendation logic. Synthetic fixtures are not live market data, sold evidence remains manual or separately approved, and a human remains the final decision-maker.

No commit, merge, or push has been performed. Do not merge or push these changes without explicit human approval. Keep credentials, cookies, tokens, marketplace responses, and local runtime state out of the repository.
