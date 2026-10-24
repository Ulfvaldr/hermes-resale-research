# Local Phase 2 candidates viewer

## What it is

The candidates viewer is a small local web page for reviewing an already-produced Phase 2 daily candidate report. It is read-only. It displays the values supplied by the Phase 2 report, preserves ranked order, shows missing values as `Unavailable`, and keeps rejected or skipped records available for audit with evidence provenance and reason codes.

The viewer is not a second evaluator. The Python Phase 1/Phase 2 runtime remains authoritative for product identity, freshness, evidence validity, economics, scoring, ranking, and recommendation. The viewer does not recalculate or repair any of those values. It also does not replace n8n: n8n may orchestrate or transport a batch run, while the viewer only presents the resulting local JSON.

There is no purchasing, checkout, payment, ordering, listing, marketplace write-back, credential handling, or automatic external action. The human is always the final decision-maker.

## Requirements

- Python 3.11 or newer.
- A clone of this repository.
- No Python package, database, n8n instance, marketplace credential, or network connection is needed for demo mode.

Run commands from the repository root. On Windows, use the equivalent `set PYTHONPATH=src` syntax if your shell does not support `PYTHONPATH=src command`.

## Credential-free demo

Start the server with the checked-in synthetic fixture:

```bash
PYTHONPATH=src python -m hermes_resale_research.viewer --demo
```

Open `http://127.0.0.1:8765/` in a browser. The demo command runs the existing batch CLI against `examples/phase2-demo-candidates.json`; it does not call a marketplace or n8n. The page is labeled `CREDENTIAL-FREE SYNTHETIC DEMO`, so demo data cannot be mistaken for live market data. Stop the server with Ctrl-C.

To use another local port or bind address:

```bash
PYTHONPATH=src python -m hermes_resale_research.viewer --demo --host 127.0.0.1 --port 8877
```

Only bind to a non-loopback address when the local network exposure is intentional. The viewer still has no write or purchase capability, but report contents may contain local research data.

## Viewing Phase 2 output

Generate a JSON report with the existing Phase 2 CLI, or use a report produced by n8n/local orchestration:

```bash
PYTHONPATH=src python -m hermes_resale_research examples/phase2-demo-candidates.json --batch --limit 10 > report.json
PYTHONPATH=src python -m hermes_resale_research.viewer --report report.json
```

Open `http://127.0.0.1:8765/`. In `--report` mode the viewer reads exactly one path at startup. It does not run evaluation, search for a newer file, fetch URLs shown in provenance, or write a modified report. The report must be a JSON object with `items` and `rejected` arrays and both safety flags set to `true`:

```json
{
  "research_only": true,
  "human_approval_required": true,
  "items": [],
  "rejected": []
}
```

The full envelope and item fields are defined in `docs/phase2-viewer-data-contract.md`. The viewer displays the `items` array in the order supplied by Phase 2 and assigns a 1-based display rank. It does not sort by profit or ROI. Numeric values are displayed as supplied; they are not recomputed.

## Understanding the page

- Top opportunities: ranked items that Phase 2 presented as eligible.
- Estimated net profit, ROI, recommendation, confidence, and evidence quality: authoritative Phase 2 values, not viewer calculations.
- Evidence and provenance: expand a card to see source/resale provenance, candidate ID, eligibility, failed gates, and reason codes.
- Rejected / skipped audit records: candidates excluded by Phase 2. They are not promoted into opportunities by the viewer.
- `Unavailable`: a null or missing value. It is not zero and is not an estimate.

A report with zero `items` is valid. It means no evidence-backed candidate passed the Phase 2 presentation filter; inspect the rejected audit records for the exact explanation.

## Troubleshooting

### `choose exactly one of --report or --demo`

Use one and only one input mode. Demo mode is explicit and synthetic. Report mode requires a path:

```bash
PYTHONPATH=src python -m hermes_resale_research.viewer --report report.json
```

### Report file cannot be read or is malformed

Check that the command is being run from the repository root, that the path exists, and that the producer emitted JSON rather than Markdown or log text. Regenerate a clean report by redirecting only the batch command's JSON stdout. Do not paste partial output into the viewer or add fallback scoring.

### Safety-contract error

The viewer refuses reports unless `research_only` and `human_approval_required` are exactly `true`. This is intentional. Use the Phase 2 batch output, not a hand-edited or unsafe report. A viewer error is not permission to change a safety flag.

### The page shows no ranked candidates

Read the `Rejected / skipped audit records` section. Common fail-closed reasons include `SOLD_EVIDENCE_UNAVAILABLE`, `SOLD_EVIDENCE_STALE`, `IDENTITY_NOT_PROVEN`, `SOURCE_PRICE_NOT_CURRENT`, `STOCK_NOT_CURRENT`, and `OUT_OF_STOCK`. Active asking prices cannot substitute for sold evidence. Obtain or approve better evidence in the upstream Phase 2 input, rerun the authoritative evaluator, and then open the new report.

### Phase 2 output is unavailable

The viewer cannot create a real report without upstream Phase 2 output. For a credential-free smoke test, use `--demo`. For normal local use, run the Phase 2 CLI or the approved local n8n workflow first. If n8n is unavailable, run the Python CLI directly; n8n is optional. Do not treat synthetic demo output as live data.

### Port is already in use

Choose another local port, for example `--port 8877`, and open the matching URL. No external service is required.

### Browser cannot connect

Confirm that the terminal still shows `Viewer listening at ...`, that the URL uses the selected port, and that the process was not stopped with Ctrl-C. The HTTP server serves only `/`; other paths return 404.

## Boundaries and next steps

The viewer is a review surface only. It does not replace n8n orchestration, Phase 1/Phase 2 logic, approved evidence adapters, or human review. Before any external action, a human must independently verify identity, source price and stock, freshness, resale evidence, economics, provenance, and policy. No automatic purchasing or listing is supported by this project.
