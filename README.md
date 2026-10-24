# Hermes Resale Research

A research-only Phase 1 workflow plus a bounded Phase 2 daily candidate batch for evaluating resale opportunities from structured source and marketplace evidence. The repository contains deterministic contracts, policy documents, synthetic fixtures, an optional local n8n transport, and a local read-only candidates viewer. It does not contain marketplace credentials, cookies, live responses, purchasing automation, listing automation, or a marketplace operations dashboard; the viewer only presents completed local Phase 2 reports.

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
- `examples/phase2-demo-candidates.json` — credential-free daily batch fixture.
- `n8n/workflows/daily-candidate-workflow.json` — importable n8n visual orchestration workflow.
- `PHASE_2_ARCHITECTURE.md` — Phase 2 component boundary, safety contract, and operating model.
- `docs/phase2-viewer-setup.md` — local viewer setup, input modes, and troubleshooting.
- `PROJECT_STATUS.md` — current milestone status and known limitations.
- `HANDOFF.md` — validation-backed handoff and recommended next steps.

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

## Daily candidate demo

This is the shortest clone/configure/start/view path. It needs only Python 3.11+ and the standard library; no marketplace credentials or n8n instance is required:

```bash
cp config/.env.example .env             # optional; keep real secrets local
PYTHONPATH=src python -m hermes_resale_research examples/phase2-demo-candidates.json --batch --limit 10 --markdown
```

The report is titled `Today's Resale Opportunity Candidates`. It shows ranked evidence-backed items and a rejected audit section. `research_only` and `human_approval_required` are always true; this repository has no purchase or listing command.

### Local candidates viewer

Serve the credential-free synthetic viewer with Python 3.11+:

```bash
PYTHONPATH=src python -m hermes_resale_research.viewer --demo
```

Then open `http://127.0.0.1:8765/`. To view an existing local Phase 2 JSON report without running any evaluation logic, use `--report path/to/report.json` instead. The viewer validates the read-only safety flags, preserves Phase 2 item order, renders unavailable values explicitly, and exposes provenance/reason codes in expandable sections. It makes no network requests and has no purchase, listing, checkout, or write-back behavior. Stop it with Ctrl-C.

The viewer has exactly two input modes: `--demo` runs the checked-in synthetic fixture through the existing Phase 2 batch CLI, while `--report` reads one JSON report already produced by that CLI. It does not discover files, call n8n, fetch marketplace pages, or calculate scores/economics. The report must contain `research_only: true` and `human_approval_required: true`; a missing, malformed, or unsafe report stops with an error instead of being partially displayed. A report with no ranked `items` is valid: use the rejected/skipped audit section to see why candidates failed, such as unavailable or stale sold evidence, identity failure, price/stock staleness, or out-of-stock status. See `docs/phase2-viewer-setup.md` for a copy/paste workflow and troubleshooting.

The page is a read-only review aid, not an execution console. It cannot purchase, checkout, order, pay, or list an item, and it never replaces n8n orchestration or the Phase 1/Phase 2 business logic. The human remains responsible for checking evidence, identity, freshness, economics, current price/stock, and approval before any external action.

### Batch output contract

Batch JSON contains `title`, `generated_at`, `bounded_limit`, `candidate_count`, `evaluated_count`, `items`, `rejected`, `research_only`, and `human_approval_required`. Each presented item includes the candidate/product identity, source store and price, expected resale price, estimated net profit, ROI, break-even price, recommendation, confidence, evidence quality, explanation, failed gates, reason codes, source provenance, resale provenance, `eligible`, and `human_approval_required`. Rejected candidates remain in the audit list and are never presented as eligible.

The batch path is fail-closed: duplicate IDs are deterministically deduplicated, malformed candidates become rejected `SKIP` records, missing or invalid sold evidence cannot produce a buy recommendation, stale critical observations route to `RECHECK`/`SKIP`, and active asking prices are never substituted for completed-sale evidence. A `BUY_CANDIDATE` still requires a final source price and stock recheck before purchase.

## Optional n8n integration

The `--n8n` path is transport only. It sends the input JSON object unchanged to an existing local n8n webhook; it does not execute or duplicate the deterministic resale workflow:

```bash
PYTHONPATH=src python -m hermes_resale_research --n8n examples/manual-evaluation.json
```

For visual orchestration, import `n8n/workflows/daily-candidate-workflow.json` into a local n8n instance. The workflow is `Trigger -> Discover candidates -> Research/enrich -> Evaluate batch -> Rank -> Present results`. Set the n8n process environment variables `HERMES_RESALE_REPO` to the absolute repository path and `PYTHONPATH` to `<repo>/src`, then run it manually. The Evaluate batch node invokes the Python application; n8n only transports status and presentation data. If it cannot run the command, the node error names the missing repository/Python setup. n8n's Execute Command node must be enabled (it is commonly disabled in hosted or queue-mode deployments).

The imported workflow is sample-mode by design and uses `examples/phase2-demo-candidates.json`. Replace the discovery/enrichment adapter only with an approved evidence source; do not put scoring, freshness, identity, economics, or recommendation rules into n8n.

The actual node behavior is: `Trigger` starts a manual run; `Discover candidates` selects the sample file and limit; `Research/enrich` marks fixture-backed, fail-closed evidence handling; `Evaluate batch` runs `python -m hermes_resale_research <repo>/examples/phase2-demo-candidates.json --batch --limit <limit>`; `Rank` parses stdout JSON and refuses a missing safety contract; and `Present results` emits the title, timestamp, ranked candidates, rejected audit, counts, and safety flags. The workflow is inactive on import and is not a live source connector. Hosted/queue-mode n8n commonly disables Execute Command, so this path requires a permitted self-hosted/local n8n execution environment.

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

- The included n8n workflow is a local/self-hosted demo and requires Execute Command permission; hosted n8n is not supported by this path.
- Synthetic fixtures do not represent live market conditions.
- Sold-market evidence remains a manually supplied or separately approved input.
- Human review is required before acting on any recommendation.
- A live n8n import/execution was not performed during Phase 2 validation; the artifact, node shape, command path, and local CLI were validated instead.
- Live source adapters remain outside the bounded milestone. Configure optional credentials only after reviewing provider terms, permitted use, and evidence provenance requirements.

Future work can add approved evidence providers, provided the deterministic Python runtime remains authoritative and secrets stay outside the repository. See `PROJECT_STATUS.md` and `HANDOFF.md` for the current closeout state.

## Human approval gate

This working tree is intentionally uncommitted and unpushed. Do not merge, push, publish, purchase, list, or otherwise operationalize recommendations without explicit human approval. A human must review evidence, identity, freshness, economics, provenance, and the final source price/stock before any external action.
