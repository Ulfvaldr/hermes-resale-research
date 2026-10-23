#!/usr/bin/env python3
"""Build the canonical offline Phase 1 fixture package."""
from __future__ import annotations
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOW = "2026-10-22T12:00:00Z"
POLICY = "freshness-v1"
BUY_RECHECK = "final source price and stock recheck required before purchase"

def ts(minutes=0, hours=0, days=0):
    total = minutes + hours * 60 + days * 1440
    # All fixture times are deterministic and minute-granular.
    from datetime import datetime, timedelta, timezone
    return (datetime.fromisoformat(NOW.replace("Z", "+00:00")) - timedelta(minutes=total)).isoformat().replace("+00:00", "Z")

def obs(field, value, age_minutes=10, status="FRESH", source="authenticated_manual", quality="USER_ENTERED", availability="AVAILABLE"):
    missing = quality == "MISSING"
    result = {
        "field": field, "value": None if availability == "UNAVAILABLE" else value,
        "observed_at": None if missing else ts(minutes=age_minutes),
        "retrieved_at": None if missing else NOW,
        "source_kind": source, "source_id": f"fixture:{field}",
        "timestamp_quality": quality, "status": status, "availability": availability,
    }
    if isinstance(value, (int, float)): result["currency"] = "USD"
    if source in ("authenticated_manual", "manual_fallback"):
        result["operator_id"] = "fixture-operator"
        result["evidence_reference"] = f"fixture-evidence:{field}"
    result["notes"] = "synthetic deterministic fixture"
    return result

def clean(d):
    if isinstance(d, dict):
        return {k: clean(v) for k, v in d.items()}
    if isinstance(d, list):
        return [clean(v) for v in d]
    return d

def money(x):
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def ratio(x):
    return money(x)

def case(spec):
    ident = spec.get("identity", "exact")
    status = "VERIFIED" if ident == "exact" else "REJECT"
    hard_conflict = ident != "exact"
    source_age = spec.get("source_age", 10)
    # Policy status and BUY-gate currency are distinct: source observations
    # become AGING after 2h and STALE only after 7d; BUY still requires <=30m.
    source_status = "MISSING" if source_age is None else ("STALE" if source_age > 10080 else ("AGING" if source_age > 120 else "FRESH"))
    stock_status = spec.get("stock_status", "FRESH")
    stock_value = spec.get("stock", "IN_STOCK")
    sold_count = spec.get("sold_count", 12)
    sold_age = spec.get("sold_age", 60)
    sold_status = spec.get("sold_status") or ("STALE" if sold_age > 10080 else ("AGING" if sold_age > 1440 else "FRESH"))
    evidence_type = spec.get("evidence_type", "OBSERVED")
    source = obs("source_price", 40.00, source_age or 0, source_status, quality="MISSING" if source_age is None else "USER_ENTERED")
    stock = obs("stock_status", stock_value, spec.get("stock_age", 10), stock_status)
    identity_obs = obs("identity", "exact-match" if ident == "exact" else "conflict", 10, "FRESH" if ident == "exact" else "CONFLICTING")
    src_product = {"product_name":"Fixture Widget", "brand":"FixtureCo", "model":"FW-100", "asin":"B0FIXTURE01", "upc":"000000000001", "condition":"NEW", "variation_attributes":{"pack_quantity":1,"size":"standard","color":"black","generation_or_version":"v1","bundle_contents":["widget"]}}
    resale_product = dict(src_product)
    if ident != "exact":
        resale_product["upc"] = "000000000099" if spec.get("identity_conflict", True) else resale_product["upc"]
        if spec.get("variation_conflict"): resale_product["variation_attributes"] = {**src_product["variation_attributes"], "pack_quantity":2}
    comp = [{"reference":f"fixture-sale-{i}","sale_date":ts(days=i+1),"price":55.0+i,"condition":"NEW","identity_match":True,"is_asking_price":False,"pack_quantity":1} for i in range(max(0, min(sold_count, 5)))]
    source_obs = clean({"marketplace":"Walmart","url_or_reference":"fixture://walmart/FW-100","product":src_product,"price":source,"stock":stock,"observations":[source,stock,identity_obs]})
    sold = obs("sold_snapshot", 55.0 if evidence_type != "UNAVAILABLE" else None, spec.get("sold_age", 60), sold_status, availability="UNAVAILABLE" if evidence_type == "UNAVAILABLE" else "AVAILABLE")
    active = obs("active_listing_count", 8, 60)
    sellers = obs("seller_count", 4, 60)
    resale = clean({"marketplace":"eBay","evidence_type":evidence_type,"sold_snapshot":sold,"sold_comps":comp,"active_market":{"active_listing_count":active,"seller_count":sellers,"observations":[active,sellers]},"observations":[sold]})
    fields = [
        {"field":"source_price","status":source_status,"observed_at":source["observed_at"],"retrieved_at":source["retrieved_at"],"age_seconds":None if source_age is None else source_age*60,"threshold_profile":"source_price","buy_gate_pass":source_status in ("LIVE","FRESH") and (source_age or 9999)<=30,"reason_codes":[] if source_status in ("LIVE","FRESH") else ["SOURCE_PRICE_NOT_CURRENT"]},
        {"field":"stock_status","status":stock_status,"observed_at":stock["observed_at"],"retrieved_at":stock["retrieved_at"],"age_seconds":spec.get("stock_age",10)*60,"threshold_profile":"stock","buy_gate_pass":stock_status in ("LIVE","FRESH") and spec.get("stock_age",10)<=30,"reason_codes":[] if stock_status in ("LIVE","FRESH") else ["STOCK_NOT_CURRENT"]},
        {"field":"sold_evidence","status":sold_status,"observed_at":sold["observed_at"],"retrieved_at":sold["retrieved_at"],"age_seconds":sold_age*60,"threshold_profile":"sold_evidence","buy_gate_pass":sold_status in ("LIVE","FRESH") and sold_age<=1440 and sold_count>=3 and evidence_type=="OBSERVED","reason_codes":[] if sold_status in ("LIVE","FRESH") and evidence_type=="OBSERVED" and sold_count>=3 else (["SOLD_EVIDENCE_STALE"] if sold_status in ("AGING","STALE") else ["SOLD_EVIDENCE_UNAVAILABLE"])},
        {"field":"active_competition","status":"FRESH","observed_at":active["observed_at"],"retrieved_at":active["retrieved_at"],"age_seconds":3600,"threshold_profile":"active_competition","buy_gate_pass":True,"reason_codes":[]},
        {"field":"seller_count","status":"FRESH","observed_at":sellers["observed_at"],"retrieved_at":sellers["retrieved_at"],"age_seconds":3600,"threshold_profile":"seller_count","buy_gate_pass":True,"reason_codes":[]},
        {"field":"fees","status":"FRESH","observed_at":active["observed_at"],"retrieved_at":active["retrieved_at"],"age_seconds":3600,"threshold_profile":"fees","buy_gate_pass":True,"reason_codes":[]},
        {"field":"shipping_estimate","status":"FRESH","observed_at":active["observed_at"],"retrieved_at":active["retrieved_at"],"age_seconds":3600,"threshold_profile":"shipping_estimate","buy_gate_pass":True,"reason_codes":[]},
        {"field":"identity","status":"FRESH" if ident == "exact" else "CONFLICTING","observed_at":identity_obs["observed_at"],"retrieved_at":identity_obs["retrieved_at"],"age_seconds":600,"threshold_profile":"identity_evidence","buy_gate_pass":ident == "exact","reason_codes":[] if ident == "exact" else ["IDENTITY_NOT_PROVEN"]},
    ]
    reasons = list(spec["reasons"])
    rec = spec["recommendation"]
    acq = spec.get("acquisition_cost", 25.0)
    tax = spec.get("tax", 2.0)
    inbound = spec.get("inbound_shipping", 1.0)
    outbound = spec.get("outbound_shipping", 3.0)
    fees = spec.get("marketplace_fees", 3.0)
    payment = spec.get("payment_fees", 1.0)
    packaging = spec.get("packaging", 1.0)
    returns = spec.get("return_allowance", 1.0)
    resale_price = spec.get("resale_price", 60.0)
    total = money(Decimal(str(acq))+Decimal(str(tax))+Decimal(str(inbound))+Decimal(str(packaging))+Decimal(str(returns)))
    net = money(Decimal(str(resale_price))-Decimal(str(total))-Decimal(str(outbound))-Decimal(str(fees))-Decimal(str(payment)))
    roi = ratio(Decimal(str(net))/Decimal(str(total))) if total else 0.0
    margin = ratio(Decimal(str(net))/Decimal(str(resale_price))) if resale_price else 0.0
    confidence = spec.get("confidence", 85 if rec == "BUY_CANDIDATE" else 40)
    gates = {"access_allowed":True,"identity_proven":ident=="exact","required_freshness_pass":source_status in ("LIVE","FRESH") and stock_status in ("LIVE","FRESH") and stock_value == "IN_STOCK","source_price_current":source_status in ("LIVE","FRESH") and (source_age or 9999)<=30,"stock_current":stock_status in ("LIVE","FRESH") and stock_value == "IN_STOCK" and spec.get("stock_age",10)<=30,"cost_inputs_current":True,"resale_evidence_pass":sold_status in ("LIVE","FRESH") and sold_count>=3 and evidence_type=="OBSERVED","market_context_current":spec.get("market_context_current",True),"economics_pass":net>=20.0 and roi>=0.20 and margin>=0.10,"volatility_resolved":spec.get("volatility")!="HIGH","confidence_minimum_pass":confidence >= 70}
    gates["all_required_gates_pass"] = all(gates.values())
    severity = {"LIVE":0,"FRESH":1,"AGING":2,"STALE":3,"UNVERIFIED":4,"MISSING":5,"CONFLICTING":6,"BLOCKED":7}
    statuses = [f["status"] for f in fields] + (["CONFLICTING"] if hard_conflict else [])
    worst_status = max(statuses, key=lambda value: severity[value])
    freshness_reasons = sorted({code for f in fields for code in f["reason_codes"]} | (set(["IDENTITY_NOT_PROVEN"]) if hard_conflict else set()))
    return clean({"id":spec["id"],"description":spec["description"],"tags":spec.get("tags",[]),"source_observation":source_obs,"resale_market_evidence":resale,"identity_audit":{"status":status,"identity_confidence":0.99 if ident=="exact" else 0.2,"matched_fields":["upc","model","variation_attributes"] if ident=="exact" else ["model"],"conflicting_fields":[] if ident=="exact" else ["upc"] + (["pack_quantity"] if spec.get("variation_conflict") else []),"hard_conflict":hard_conflict,"reason_codes":[] if ident=="exact" else ["IDENTITY_NOT_PROVEN"],"evidence":["fixture:identity"]},"freshness_audit":{"evaluation_time":NOW,"fields":fields,"overall_status":worst_status,"worst_status":worst_status,"reason_codes":freshness_reasons},"economics_inputs":{"currency":"USD","acquisition_cost":acq,"tax":tax,"inbound_shipping":inbound,"outbound_shipping":outbound,"marketplace_fees":fees,"payment_fees":payment,"packaging":packaging,"return_allowance":returns,"expected_resale_price":resale_price,"min_net_profit":20.0,"min_roi":0.20,"min_margin":0.10,"rounding_scale":2},"expected_calculations":{"total_cost":total,"expected_net_profit":net,"break_even_resale_price":money(total+outbound+fees+payment),"roi":roi,"margin":margin,"capital_at_risk":total,"rounding_mode":"ROUND_HALF_UP_2DP","calculation_status":"COMPLETE"},"decision_audit":{"expected_recommendation":rec,"expected_reason_codes":reasons,"hard_gates":gates,"human_recheck":{"required":rec=="BUY_CANDIDATE","items":[BUY_RECHECK] if rec=="BUY_CANDIDATE" else []},"confidence":confidence,"refusal":rec=="SKIP","first_failing_gate":None if rec=="BUY_CANDIDATE" else reasons[0]}})

S = [
("01_strong_valid_opportunity","valid BUY with current observations","BUY_CANDIDATE",["ALL_REQUIRED_GATES_PASS"],{}),
("02_source_price_at_31m","source price just beyond BUY boundary","RECHECK",["SOURCE_PRICE_NOT_CURRENT"],{"source_age":31}),
("03_source_price_at_30m_boundary","source price exactly at BUY boundary","BUY_CANDIDATE",["ALL_REQUIRED_GATES_PASS"],{"source_age":30}),
("04_stock_stale","stock stale","RECHECK",["STOCK_NOT_CURRENT"],{"stock_age":61,"stock_status":"AGING"}),
("05_identity_identifier_conflict","exact identifier conflict","SKIP",["IDENTITY_NOT_PROVEN"],{"identity":"conflict"}),
("06_identity_variation_pack_conflict","variation and pack conflict","SKIP",["IDENTITY_NOT_PROVEN"],{"identity":"conflict","variation_conflict":True}),
("07_fees_destroy_margin","fees make economics fail","SKIP",["ECONOMICS_FAIL"],{"marketplace_fees":30.75}),
("08_shipping_destroy_margin","shipping makes economics fail","SKIP",["ECONOMICS_FAIL"],{"outbound_shipping":29.0}),
("09_sold_count_below_minimum","fresh sold evidence but fewer than three comps","WATCH",["SOLD_COUNT_BELOW_MINIMUM"],{"sold_count":2}),
("10_out_of_stock","source explicitly out of stock","SKIP",["OUT_OF_STOCK"],{"stock":"OUT_OF_STOCK"}),
("11_high_volatility","unresolved high volatility","WATCH",["VOLATILITY_HIGH"],{"volatility":"HIGH"}),
("12_borderline_roi","ROI exactly at threshold","BUY_CANDIDATE",["ALL_REQUIRED_GATES_PASS"],{"acquisition_cost":95.0,"tax":2.0,"inbound_shipping":1.0,"packaging":1.0,"return_allowance":1.0,"resale_price":127.0}),
("13_borderline_net_profit","net profit exactly at threshold","BUY_CANDIDATE",["ALL_REQUIRED_GATES_PASS"],{"resale_price":57.0}),
("14_missing_critical_timestamp","missing source price timestamp","RECHECK",["SOURCE_PRICE_NOT_CURRENT"],{"source_age":None}),
("15_inferred_only_evidence","inferred demand cannot satisfy eBay sold gate","SKIP",["SOLD_EVIDENCE_UNAVAILABLE"],{"evidence_type":"INFERRED"}),
("16_stale_sold_snapshot","aging sold snapshot beyond BUY window","RECHECK",["SOLD_EVIDENCE_STALE"],{"sold_age":1441}),
("17_missing_sold_evidence","unavailable sold evidence","SKIP",["SOLD_EVIDENCE_UNAVAILABLE"],{"evidence_type":"UNAVAILABLE","sold_count":0}),
("18_market_context_missing","missing market context requires recheck","RECHECK",["MARKET_CONTEXT_NOT_CURRENT"],{"market_context_current":False}),
]

def main():
    fixtures=[]
    for ident, desc, rec, reasons, extra in S:
        fixtures.append(case({"id":ident,"description":desc,"recommendation":rec,"reasons":reasons,**extra}))
    package={"schema_version":"canonical-phase1-fixture-package-v1","policy_version":POLICY,"package_metadata":{"name":"canonical-phase1-fixtures","purpose":"offline deterministic contract execution","authority":"docs/freshness-policy.md","fixture_package_status":"NEW CANONICAL PACKAGE; not a reconstruction of legacy packages","rule_origins":["PRESERVED: docs/freshness-policy.md","PRESERVED: docs/phase1-contract.md","NEWLY DEFINED: explicit fixture packaging and deterministic probe cross-field assertions"],"notes":"Synthetic values only; legacy task packages are historical evidence, not an authority."},"evaluation":{"evaluation_time":NOW,"timezone":"UTC","clock_skew_future_tolerance_seconds":300},"fixtures":fixtures}
    (ROOT/"fixtures.json").write_text(json.dumps(package,indent=2)+"\n",encoding="utf-8")
    print(f"wrote {len(fixtures)} fixtures to {ROOT/'fixtures.json'}")
if __name__ == "__main__": main()
