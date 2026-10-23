# Canonical Phase 1 fixture reproducibility

This document is the repository-level guide for the canonical offline fixture package. The package is test evidence for deterministic-core implementation; it is not live marketplace data.

## Canonical package boundary

The canonical package consists of:

- `tests/fixtures/canonical_phase1/fixtures.json` — 18 synthetic machine-readable cases.
- `tests/fixtures/canonical_phase1/build_package.py` — the sole deterministic generator.
- `tests/fixtures/canonical_phase1/contract_probe.py` — offline validator and contract probe.
- `schemas/canonical-phase1-fixture-package.schema.json` — Draft 2020-12 shape authority.
- `docs/freshness-policy.md` — freshness/refusal authority.
- `docs/phase1-contract.md` — Phase 1 scope and decision contract.

Do not commit credentials, cookies, downloaded responses, personal source notes, or runtime state.

## Clean-checkout setup and probe

From the repository root, the standard-library fallback needs no installation:

    python tests/fixtures/canonical_phase1/contract_probe.py

For full JSON Schema validation, install the optional dependency:

    python -m pip install jsonschema
    python tests/fixtures/canonical_phase1/contract_probe.py

A disposable uv environment is equivalent:

    uv run --with jsonschema python tests/fixtures/canonical_phase1/contract_probe.py

A successful run reports schema validation, deterministic checks, recommendation counts, and reason-code counts. The fallback checks required structure and closed recommendation/marketplace enums. The full path adds Draft 2020-12 validation. Both paths execute the arithmetic, gate-conjunction, BUY human-recheck, and reason-code assertions.

## Regenerate and validate

The generator writes the canonical JSON in place:

    python tests/fixtures/canonical_phase1/build_package.py
    python tests/fixtures/canonical_phase1/contract_probe.py

To test byte-for-byte determinism without relying on a stored digest, copy the first output to a temporary location, run the generator again, and compare with `cmp` (or an equivalent byte-for-byte comparison). Review `git diff` afterward. Any fixture or policy change must be intentional; approved thresholds and fail-closed rules must not be silently changed.

## Downstream consumption

A deterministic core should:

1. Load `fixtures.json` as test input.
2. Validate it against `schemas/canonical-phase1-fixture-package.schema.json`.
3. Run the executable probe or equivalent cross-field assertions.
4. Feed source observations, resale evidence, identity audit, freshness audit, economics, and decision audit into deterministic tests.
5. Preserve UTC timestamps, provenance, evidence type, stable reason codes, and the exact required BUY human-recheck text.
6. Treat missing values as missing, never as zero or fresh; treat synthetic values as fixtures, never as current market observations.

The package does not authorize live adapters, credentials, scraping, purchases, or listings.

## Provenance and non-substitution

- Task `t_462dc2f7` is unrecoverable historical evidence. This package must not be described as an exact reconstruction of it, and that task is not an authority.
- Task `t_10487e87` is an older, different artifact and must not be substituted for this package.
- `opportunity_cases.json` with SHA-256 `31a0f8087b08d356ba6fbc908b187c8257921632c8408e4ee96207e5267f4a63` is an incomplete, non-authoritative reconstruction. It must not be used to complete or replace the canonical fixtures.
- `docs/freshness-policy.md` is authoritative for freshness/refusal semantics unless Veritas identifies an explicit contradiction. Its thresholds, boundary semantics, refusal ordering, and fail-closed BUY rules are normative.
- Package layout and deterministic cross-field assertions are test structure. They do not silently change approved thresholds, refusal rules, or decision gates.
