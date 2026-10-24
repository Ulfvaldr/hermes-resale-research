# Hermes Resale Research

A research-only Phase 1 workflow for evaluating resale opportunities from structured source and marketplace evidence. The repository contains deterministic contracts, policy documents, synthetic fixtures, and a thin optional n8n transport. It does not contain marketplace credentials, cookies, live responses, purchasing automation, listing automation, or dashboard UI.

## Architecture

```text
Hermes agent -> n8n (optional integration) -> Hermes Resale Python runtime -> structured result
```

The Python runtime is the source of truth for identity, freshness, evidence validity, economics, scoring, reason codes, and recommendations. n8n may route or present the contract, but must not duplicate those rules. A human remains the final decision-maker.

## Repository guide

- `src/hermes_resale_research/` — runtime models, evidence adapters, deterministic workflow, and optional n8n transport.
- `docs/freshness-policy.md` — normative freshness thresholds, boundary behavior, and refusal rules.
- `docs/phase1-contract.md` — Phase 1 scope, data contracts, and decision semantics.
- `docs/canonical-fixture-schema.md` — canonical fixture schema and rule origins.
- `docs/canonical-fixture-reproducibility.md` — clean-checkout setup, generation, validation, provenance, and consumption.
- `schemas/canonical-phase1-fixture-package.schema.json` — Draft 2020-12 machine-readable schema.
- `tests/fixtures/canonical_phase1/` — deterministic fixture package and executable contract probe.
- `examples/manual-evaluation.json` — offline input example.

## Quick start

From the repository root, run the standard-library contract probe:

```bash
python tests/fixtures/canonical_phase1/contract_probe.py
```

For full Draft 2020-12 validation when `jsonschema` is available:

```bash
uv run --with jsonschema python tests/fixtures/canonical_phase1/contract_probe.py
```

The package generator is deterministic:

```bash
python tests/fixtures/canonical_phase1/build_package.py
python tests/fixtures/canonical_phase1/contract_probe.py
```

Read the reproducibility document before changing fixtures or policy semantics. Synthetic fixtures are test evidence, not live market data.

## Offline evaluation

The reusable workflow accepts JSON-shaped manual input and makes no network calls:

```bash
PYTHONPATH=src python -m hermes_resale_research examples/manual-evaluation.json
```

The result includes identity, per-field freshness, economics, market provenance, score, recommendation, reason codes, and any human recheck requirements. Invalid or missing eBay sold evidence is classified as `UNAVAILABLE`; active asking prices are never substituted for sold prices.

## Optional n8n integration

The `--n8n` path is transport only. It sends the input JSON object unchanged to an existing local n8n webhook; it does not execute or duplicate the deterministic resale workflow:

```bash
PYTHONPATH=src python -m hermes_resale_research --n8n examples/manual-evaluation.json
```

This repository does not include an n8n workflow definition or import/export instructions. The intended local endpoint and workflow must already exist before using this mode.

Configuration is available in `config/.env.example`:

- `N8N_RESALE_WEBHOOK_URL` — webhook URL; defaults to `http://localhost:5678/webhook/hermes-resale-evaluate`.
- `N8N_RESALE_TIMEOUT_SECONDS` — request timeout; defaults to `15` seconds.

The client returns `{ok, status_code, data}` for a valid JSON object response. It fails closed with `{ok, status_code, error}` for connection failures, HTTP errors, invalid JSON, non-object JSON responses, and invalid request payloads. Error codes are stable: `CONNECTION_ERROR`, `HTTP_ERROR`, `MALFORMED_RESPONSE`, and `INVALID_PAYLOAD`.

The default URL assumes n8n is running on the same machine. For a remote endpoint, set an explicit URL and use an appropriate authenticated, private network; do not put credentials in the URL or commit them to the repository. The client sends only the supplied contract and does not add marketplace credentials.

## eBay and data boundaries

`config/.env.example` lists optional eBay Application-token variables. Keep real values in a local, gitignored `.env` file. Production credentials are not required for the offline workflow and must never be committed.

The official Browse API provides active listings only. Phase 1 sold evidence must be manual or come from a separately approved provider. This project does not automate source-price collection from Walmart or Best Buy, purchasing, listing, or marketplace dashboard actions.

## Validation

Run the complete test suite with:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

The canonical runtime test replays every fixture through the documented CLI and checks recommendation and reason-code outputs. It intentionally does not call the fixture contract probe. Keep runtime logic and policy documents aligned when changing either one.

## Limitations and next steps

- The n8n workflow is an external local prerequisite, not a repository artifact.
- Synthetic fixtures do not represent live market conditions.
- Sold-market evidence remains a manually supplied or separately approved input.
- Human review is required before acting on any recommendation.

Future work can add approved evidence providers or a versioned n8n workflow export, provided the deterministic Python runtime remains authoritative and secrets stay outside the repository. See `PROJECT_STATUS.md` and `HANDOFF.md` for the current closeout state.
