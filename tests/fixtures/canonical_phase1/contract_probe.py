#!/usr/bin/env python3
"""Deterministic executable contract probe for canonical Phase 1 fixtures."""
from __future__ import annotations
import json, sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PACKAGE = HERE / "fixtures.json"
SCHEMA = ROOT / "schemas" / "canonical-phase1-fixture-package.schema.json"
BUY_RECHECK = "final source price and stock recheck required before purchase"

def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def validate_schema(data):
    try:
        import jsonschema
    except ImportError:
        # Keep the probe runnable from a clean Python checkout. This fallback
        # checks the schema's required object structure and closed enums; when
        # jsonschema is installed, full Draft 2020-12 validation is used.
        if data.get("schema_version") != "canonical-phase1-fixture-package-v1" or data.get("policy_version") != "freshness-v1":
            raise AssertionError("package/schema version mismatch")
        required = {
            "package_metadata": ["name", "purpose", "authority", "fixture_package_status", "rule_origins"],
            "evaluation": ["evaluation_time", "timezone", "clock_skew_future_tolerance_seconds"],
        }
        for obj, fields in required.items():
            if any(field not in data[obj] for field in fields): raise AssertionError(f"missing {obj} field")
        for case in data.get("fixtures", []):
            fields = ["id", "description", "source_observation", "resale_market_evidence", "identity_audit", "freshness_audit", "economics_inputs", "expected_calculations", "decision_audit"]
            if any(field not in case for field in fields): raise AssertionError(f"missing fixture field in {case.get('id')}")
            if case["decision_audit"]["expected_recommendation"] not in {"BUY_CANDIDATE", "WATCH", "RECHECK", "SKIP"}: raise AssertionError("invalid recommendation")
            if case["resale_market_evidence"]["marketplace"] != "eBay": raise AssertionError("invalid resale marketplace")
        return
    resolver = jsonschema.RefResolver(SCHEMA.as_uri(), json.loads(SCHEMA.read_text(encoding="utf-8")))
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")), resolver=resolver).validate(data)

def check_case(case):
    errors = []
    econ = case["economics_inputs"]
    calc = case["expected_calculations"]
    total = money(sum(Decimal(str(econ[field])) for field in ("acquisition_cost", "tax", "inbound_shipping", "packaging", "return_allowance")))
    net = money(Decimal(str(econ["expected_resale_price"])) - total - sum(Decimal(str(econ[field])) for field in ("outbound_shipping", "marketplace_fees", "payment_fees")))
    break_even = money(total + sum(Decimal(str(econ[field])) for field in ("outbound_shipping", "marketplace_fees", "payment_fees")))
    roi = money(net / total) if total else Decimal("0.00")
    margin = money(net / Decimal(str(econ["expected_resale_price"]))) if econ["expected_resale_price"] else Decimal("0.00")
    expected_values = {"total_cost": total, "expected_net_profit": net,
                       "break_even_resale_price": break_even, "roi": roi,
                       "margin": margin, "capital_at_risk": total}
    for field, actual in expected_values.items():
        if money(calc[field]) != actual:
            errors.append(f"{field} {actual} != {calc[field]}")
    expected = case["decision_audit"]["expected_recommendation"]
    reasons = case["decision_audit"]["expected_reason_codes"]
    gates = case["decision_audit"]["hard_gates"]
    gate_values = [gates[key] for key in gates if key != "all_required_gates_pass"]
    if not all(isinstance(value, bool) for value in gate_values): errors.append("hard gates must be booleans")
    if gates["economics_pass"] != (net >= Decimal(str(econ["min_net_profit"])) and roi >= Decimal(str(econ["min_roi"])) and margin >= Decimal(str(econ["min_margin"]))): errors.append("economics_pass mismatch")
    if gates["all_required_gates_pass"] != all(gate_values): errors.append("all_required_gates_pass is not the gate conjunction")
    if gates["all_required_gates_pass"] != (expected == "BUY_CANDIDATE"): errors.append("all_required_gates_pass mismatch")
    if gates["confidence_minimum_pass"] != (case["decision_audit"]["confidence"] >= 70): errors.append("confidence gate is not derived from recorded confidence")
    if case["id"] == "10_out_of_stock" and gates["stock_current"]: errors.append("out-of-stock incorrectly passes stock gate")
    if case["id"] == "15_inferred_only_evidence" and "SOLD_EVIDENCE_UNAVAILABLE" not in reasons: errors.append("inferred eBay evidence missing sold refusal")
    if case["id"] == "16_stale_sold_snapshot" and case["resale_market_evidence"]["sold_snapshot"]["status"] != "AGING": errors.append("24h+ sold snapshot must be AGING under policy")
    if expected == "BUY_CANDIDATE":
        if not all(gate_values) or not case["decision_audit"]["human_recheck"]["required"]: errors.append("BUY gates/recheck missing")
        if BUY_RECHECK not in case["decision_audit"]["human_recheck"]["items"]: errors.append("BUY recheck text missing")
        if case["decision_audit"]["first_failing_gate"] is not None or case["decision_audit"]["refusal"]: errors.append("BUY refusal/failing gate invalid")
    if case["id"] == "12_borderline_roi" and roi != money(econ["min_roi"]): errors.append("borderline ROI is not exactly min_roi")
    if case["id"] == "13_borderline_net_profit" and net != money(econ["min_net_profit"]): errors.append("borderline net profit is not exactly min_net_profit")
    for observation in case["source_observation"]["observations"] + case["resale_market_evidence"]["observations"]:
        if not observation.get("source_id") or not observation.get("source_kind"): errors.append("observation provenance missing")
    if case["id"] == "14_missing_critical_timestamp" and case["source_observation"]["price"]["observed_at"] is not None: errors.append("missing timestamp did not fail closed")
    if case["id"] == "17_missing_sold_evidence" and case["resale_market_evidence"]["sold_snapshot"]["availability"] != "UNAVAILABLE": errors.append("missing sold evidence did not fail closed")
    if not reasons: errors.append("empty reason codes")
    return errors

def main():
    data = json.loads(PACKAGE.read_text(encoding="utf-8"))
    validate_schema(data)
    fixtures = data["fixtures"]
    if len(fixtures) != 18 or len({c["id"] for c in fixtures}) != 18:
        raise AssertionError("package must contain 18 unique fixture IDs")
    failures = {}
    for case in fixtures:
        errors = check_case(case)
        if errors: failures[case["id"]] = errors
    if failures:
        raise AssertionError(json.dumps(failures, indent=2))
    counts = {}
    reason_counts = {}
    for case in fixtures:
        rec = case["decision_audit"]["expected_recommendation"]
        counts[rec] = counts.get(rec, 0) + 1
        for reason in case["decision_audit"]["expected_reason_codes"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    print(f"PASS schema: {len(fixtures)} fixtures validated")
    print("PASS deterministic checks: economics, gate conjunctions, BUY recheck, reason-code presence")
    print("recommendations:", json.dumps(dict(sorted(counts.items())), sort_keys=True))
    print("reason_codes:", json.dumps(dict(sorted(reason_counts.items())), sort_keys=True))
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
