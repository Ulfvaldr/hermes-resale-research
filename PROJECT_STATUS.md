# Project status

## Hermes to n8n integration

The resale decision remains the deterministic four-agent Phase 1 workflow in
`src/hermes_resale_research/workflow.py`. `n8n_client.py` is transport only:
it accepts an already validated JSON contract, POSTs it to the local n8n
webhook, and returns a compact structured result. It intentionally does not
reimplement identity, freshness, economics, scoring, or recommendation logic.

Configuration:

- `N8N_RESALE_WEBHOOK_URL` (default:
  `http://localhost:5678/webhook/hermes-resale-evaluate`)
- `N8N_RESALE_TIMEOUT_SECONDS` (default: `15`)

Run locally with:

    PYTHONPATH=src python -m hermes_resale_research --n8n examples/manual-evaluation.json

The client fails closed for connection errors, non-2xx HTTP errors, invalid
JSON responses, and non-object/non-serializable payloads. A live n8n instance is
not required for the unit tests; this repository does not include an n8n workflow
definition or export/import instructions, so the local endpoint and workflow must
already exist for integration use. No marketplace credentials are needed.

## Current validation state

The documented n8n integration cleanup is complete. The current verification
reported by the implementation work is 29 unit tests passing and
`git diff --check` passing, including the n8n client tests and final-newline
checks. This is not a final acceptance result: independent Veritas review is
still pending, so this document must not be read as a final PASS.

No commit, merge, or push has been performed. Do not merge or push these changes
without explicit human approval. Final acceptance remains owned by the
independent reviewer; any issues found there must be resolved before a human
approves integration.
