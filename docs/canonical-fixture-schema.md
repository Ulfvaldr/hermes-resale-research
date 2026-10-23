# Canonical Phase 1 fixture schema

The authoritative machine-readable schema for the new Phase 1 fixture package is:

`schemas/canonical-phase1-fixture-package.schema.json`

It defines one package containing deterministic fixture cases. Each case must include:

- fixture and evaluation metadata;
- source observations (price, stock, identity, provenance and timestamps);
- eBay resale/market evidence (sold comps kept separate from active asking listings);
- identity audit;
- per-field and aggregate freshness audit;
- complete economics inputs and expected calculations;
- decision audit with expected recommendation, stable reason codes, hard-gate booleans, refusal state, first failing gate, confidence, and human recheck requirements.

Timestamp and freshness constraints are grounded in `docs/freshness-policy.md`: UTC `Z` timestamps, the `freshness-v1` policy, the eight preserved observation states, source/access provenance, and the stable reason-code enum. The schema deliberately does not treat the older `t_10487e87` 10-case package or `tests/fixtures/opportunity_cases.json` as authoritative.

Schema annotations use `x-rule-origin`:

- `PRESERVED` means the constraint is taken from `docs/freshness-policy.md` or the existing Phase 1 contract.
- `NEWLY DEFINED` marks a schema-level determinism constraint that the policy requires but does not spell out as a machine-readable shape: explicit economics threshold fields, a named rounding mode, and the exact required BUY human-recheck text. These are structural fixture rules, not new freshness or decision policy, and are tied to the cited policy/contract sections in the schema.

A validator should validate the package against JSON Schema draft 2020-12 and additionally execute arithmetic, cross-field freshness, gate, and recommendation assertions. JSON Schema alone cannot calculate ages or verify that `all_required_gates_pass` is the conjunction of the individual gate fields.
