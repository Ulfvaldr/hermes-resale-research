# Human handoff

## What is complete

The optional Hermes-to-local-n8n transport and its documentation are in place. `n8n_client.py` sends the supplied JSON contract to an existing local n8n webhook; it does not duplicate Phase 1 identity, freshness, evidence, economics, scoring, or recommendation logic.

The repository does not include an n8n workflow definition or import/export instructions. Integration use requires the intended local endpoint and workflow to already exist. The offline workflow remains usable without n8n, marketplace credentials, or network access.

## Validation reported by implementation work

- `PYTHONPATH=src python -m unittest discover -s tests` — 30 tests passed.
- `git diff --check` — passed.
- n8n client, documentation, and final-newline checks passed during implementation.

These are implementation checks, not a final acceptance verdict. Independent review should rerun them against the final repository state.

## Architecture boundary

Hermes handles orchestration, n8n handles optional visual integration, and the Hermes Resale Python runtime remains authoritative for deterministic evaluation. n8n must not reimplement scoring, economics, freshness, or recommendation rules. A human makes the final decision.

## Human control gate

No commit, merge, or push has been performed. Do not merge or push without explicit human approval. Keep credentials, cookies, tokens, marketplace responses, and local runtime state out of the repository.
