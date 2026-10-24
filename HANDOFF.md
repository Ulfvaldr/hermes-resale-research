# Human handoff

## What is complete

The bounded Phase 2 batch pipeline and optional Hermes-to-local-n8n integration are in place. `n8n/workflows/daily-candidate-workflow.json` is an importable sample workflow: Trigger -> Discover candidates -> Research/enrich -> Evaluate batch -> Rank -> Present results. Its Evaluate batch node invokes the Python CLI; n8n does not duplicate Phase 1 identity, freshness, evidence, economics, scoring, or recommendation logic.

The offline sample run remains usable without n8n, marketplace credentials, or network access. For n8n, set `HERMES_RESALE_REPO` and `PYTHONPATH=<repo>/src` in the n8n process environment and execute the imported workflow manually.

The batch output is a bounded JSON/Markdown report with ranked eligible items and a rejected audit. It carries product/source economics, recommendation, confidence, evidence quality, explanation, failed gates, reason codes, source/resale provenance, `eligible`, `research_only`, and `human_approval_required`. Invalid, duplicate, stale, identity-conflicting, out-of-stock, or sold-evidence-incomplete candidates are handled fail-closed; active asking prices cannot satisfy the sold-evidence gate.

## Validation reported by implementation work

- `PYTHONPATH=src python -m unittest discover -s tests` — 33 tests passed.
- `PYTHONPATH=src python -m hermes_resale_research examples/phase2-demo-candidates.json --batch --limit 10 --markdown` — sample report rendered with 7 evaluated, 4 presented, and 3 rejected candidates.
- `python -m json.tool n8n/workflows/daily-candidate-workflow.json` — workflow JSON validated.
- `git diff --check` — passed.
- n8n client, documentation, and final-newline checks passed during implementation.

These are implementation checks, not a final acceptance verdict. Independent review should rerun them against the final repository state.

Independent validation subsequently passed the same checks, including 18 canonical fixtures and a simulated n8n Execute Command path. It found no purchase, checkout, order, payment, or listing automation. Live n8n import/execution was not performed; hosted/queue-mode Execute Command availability remains an operational limitation.

## Architecture boundary

Hermes handles orchestration, n8n handles optional visual integration, and the Hermes Resale Python runtime remains authoritative for deterministic evaluation. n8n must not reimplement scoring, economics, freshness, or recommendation rules. A human makes the final decision.

## Human control gate

No commit, merge, or push has been performed. Do not merge or push without explicit human approval. Keep credentials, cookies, tokens, marketplace responses, and local runtime state out of the repository.

## Recommended next steps

1. Human-review the uncommitted diff and approve or reject the Phase 2 scope.
2. If approved, add only a separately approved, read-only evidence adapter with terms/provenance review and regression fixtures.
3. Validate that adapter locally, then perform any commit/merge/push only after explicit human authorization.

Until then, use sample mode or manually supplied approved evidence. No recommendation is an instruction to buy or list.
