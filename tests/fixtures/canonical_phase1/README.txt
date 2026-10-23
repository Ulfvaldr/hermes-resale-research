Canonical Phase 1 fixture package

Status: NEW CANONICAL PACKAGE; not a reconstruction of any legacy task package.

Canonical files

- `fixtures.json` — 18 synthetic, machine-readable cases for the canonical package schema.
- `contract_probe.py` — offline deterministic validator and contract probe.
- `build_package.py` — reproducible generator for `fixtures.json`.
- `../../../schemas/canonical-phase1-fixture-package.schema.json` — Draft 2020-12 schema.
- `../../../docs/freshness-policy.md` — authoritative repository copy of freshness/refusal semantics.
- `../../../docs/phase1-contract.md` — Phase 1 contract and decision scope.

The package boundary is the three files in this directory plus the schema and policy documents listed above. Do not add downloaded responses, credentials, cookies, personal source notes, or runtime state to the package.

Clean-checkout installation and execution

From the repository root, no dependency is required for the fallback probe:

    python tests/fixtures/canonical_phase1/contract_probe.py

For full JSON Schema Draft 2020-12 validation, use the optional `jsonschema` dependency:

    python -m pip install jsonschema
    python tests/fixtures/canonical_phase1/contract_probe.py

or, with uv and without changing the checkout environment:

    uv run --with jsonschema python tests/fixtures/canonical_phase1/contract_probe.py

The probe must report schema validation, deterministic checks, recommendation counts, and reason-code counts. The fallback validates the required package structure and closed recommendation/marketplace enums; the full path additionally validates the complete schema. Both paths run the package's arithmetic, gate-conjunction, BUY recheck, and reason-code assertions.

Regeneration and validation

`build_package.py` is the sole generator. From the repository root:

    python tests/fixtures/canonical_phase1/build_package.py
    python tests/fixtures/canonical_phase1/contract_probe.py

To verify deterministic output without relying on a precomputed hash, run the generator twice and compare the two resulting `fixtures.json` files with `cmp` (or an equivalent byte-for-byte comparison). Review the diff after regeneration: fixture edits must be intentional, and approved thresholds or fail-closed rules must not be silently changed.

Downstream deterministic-core consumption

Consumers should load `fixtures.json`, validate it against `schemas/canonical-phase1-fixture-package.schema.json`, then run the contract assertions before using any case. Treat each case's source observations, resale evidence, identity audit, freshness audit, economics, and decision audit as explicit test inputs and expected outputs. Preserve UTC timestamps, provenance, evidence type, stable reason codes, and the required BUY human-recheck text. Do not treat synthetic fixture values as current marketplace observations, and do not infer missing values as zero or fresh.

Provenance and non-substitution rules

- This is a new canonical package. Task `t_462dc2f7` is unrecoverable historical evidence and must not be represented as exactly reconstructed or used as an authority.
- Older task `t_10487e87` is a different artifact and must not be substituted for this package.
- `opportunity_cases.json` with SHA-256 `31a0f8087b08d356ba6fbc908b187c8257921632c8408e4ee96207e5267f4a63` is an incomplete, non-authoritative reconstruction. It is not a source for completing or replacing these fixtures.
- `docs/freshness-policy.md` is authoritative for freshness and refusal semantics unless Veritas identifies an explicit contradiction. Its thresholds, boundary semantics, refusal ordering, and fail-closed BUY rules remain normative.
- Fixture packaging and deterministic cross-field assertions are packaging/test structure; they do not silently amend policy thresholds or decision gates.

All values in `fixtures.json` are synthetic and contain no credentials, tokens, cookies, live responses, or personal source notes.
