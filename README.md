Hermes Resale Research

This repository contains the research-only Phase 1 contracts and the canonical offline fixture package. It does not contain live marketplace credentials, cookies, API responses, or purchasing/listing automation.

Canonical documentation

- docs/freshness-policy.md — normative freshness and refusal semantics; preserve its thresholds, boundary behavior, and fail-closed rules.
- docs/phase1-contract.md — Phase 1 scope, data contracts, and decision semantics.
- docs/canonical-fixture-schema.md — schema overview and rule-origin notes.
- docs/canonical-fixture-reproducibility.md — clean-checkout setup, regeneration, validation, provenance, and downstream consumption.
- schemas/canonical-phase1-fixture-package.schema.json — machine-readable Draft 2020-12 schema.
- tests/fixtures/canonical_phase1/ — canonical package files and executable probe.

Quick check from the repository root

    python tests/fixtures/canonical_phase1/contract_probe.py

This uses a standard-library structural fallback when `jsonschema` is unavailable. For full Draft 2020-12 validation, install the optional validator or run:

    uv run --with jsonschema python tests/fixtures/canonical_phase1/contract_probe.py

The package generator is deterministic:

    python tests/fixtures/canonical_phase1/build_package.py
    python tests/fixtures/canonical_phase1/contract_probe.py

Read the reproducibility document before changing fixtures or policy semantics. Synthetic fixtures are test evidence, not live market data.

Thin local invocation

The reusable workflow accepts JSON-shaped manual input and makes no network calls:

    PYTHONPATH=src python -m hermes_resale_research examples/manual-evaluation.json

The output is a JSON OpportunityAssessment containing identity, per-field freshness,
economics, market provenance, score, recommendation, reason codes, and any human
recheck requirements. Invalid or missing eBay sold evidence is classified as
UNAVAILABLE; active asking prices are never substituted for sold prices.

External eBay setup

config/.env.example lists the optional Application-token variables. Production
credentials are not required for the offline workflow and must never be committed.
The official Browse API provides active listings only; sold evidence for Phase 1 is
manual or from a separately approved provider. This project does not automate source
price collection from Walmart or Best Buy, purchasing, listing, or dashboard UI.

Runtime contract alignment

The production workflow consumes the canonical observation contract directly: source
price and stock retain separate observation timestamps, market-context observations
retain separate timestamps from sold evidence, and canonical gate codes are emitted
once from the centralized recommendation path. The regression test
`tests/test_canonical_runtime.py` replays every canonical fixture through the documented
CLI and compares both recommendation and reason-code outputs; it intentionally does
not call the fixture contract probe.
