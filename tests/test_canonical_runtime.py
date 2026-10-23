import json
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "canonical_phase1" / "fixtures.json"
NOW = "2026-10-22T12:00:00Z"


def _payload(case):
    src = case["source_observation"]
    product = src["product"]
    price, stock = src["price"], src["stock"]
    market = case["resale_market_evidence"]
    sold = market["sold_snapshot"]
    active = market["active_market"]["active_listing_count"]
    sellers = market["active_market"]["seller_count"]
    audit = case["identity_audit"]
    resale_product = dict(product)
    if audit.get("hard_conflict") and "upc" in audit.get("conflicting_fields", []):
        resale_product["upc"] = "000000000099"
    if audit.get("hard_conflict") and "pack_quantity" in audit.get("conflicting_fields", []):
        resale_product["variation_attributes"] = dict(product["variation_attributes"])
        resale_product["variation_attributes"]["pack_quantity"] = 2
    source = {
        "source_marketplace": src["marketplace"], "source_url": src["url_or_reference"],
        "product_name": product["product_name"], "brand": product["brand"], "model": product["model"],
        "asin": product["asin"], "upc": product["upc"], "condition": product["condition"],
        "variation_attributes": product["variation_attributes"], "source_price": price["value"],
        "stock_status": stock["value"], "source_observed_at": price.get("observed_at") or stock.get("observed_at"),
        "provenance": {
            "fixture_id": case["id"], "price_observed_at": price.get("observed_at"),
            "stock_observed_at": stock.get("observed_at"),
            "timestamp_quality": price.get("timestamp_quality") or stock.get("timestamp_quality"),
            "price_timestamp_quality": price.get("timestamp_quality"),
            "stock_timestamp_quality": stock.get("timestamp_quality"),
            "market_context_current": case["decision_audit"]["hard_gates"].get("market_context_current", True),
        },
    }
    resale = {
        "resale_marketplace": market["marketplace"], "product_name": resale_product["product_name"],
        "brand": resale_product["brand"], "model": resale_product["model"], "asin": resale_product["asin"],
        "upc": resale_product["upc"], "condition": resale_product["condition"],
        "variation_attributes": resale_product["variation_attributes"], "recent_sold_median": sold["value"],
        "sold_count": len(market.get("sold_comps", [])), "sold_window_days": 90,
        "active_listing_count": active["value"], "seller_count": sellers["value"],
        "evidence_observed_at": sold.get("observed_at") or active.get("observed_at"),
        "evidence_type": market["evidence_type"], "fees_observed_at": active.get("observed_at"),
        "shipping_observed_at": active.get("observed_at"), "stock_status": stock["value"],
        "volatility": "HIGH" if case["id"] == "11_high_volatility" else None,
        "provenance": {"timestamp_quality": sold.get("timestamp_quality"), "evidence_scope": "SOLD_SNAPSHOT", "active_observed_at": active.get("observed_at"), "seller_observed_at": sellers.get("observed_at"), "sold_observed_at": sold.get("observed_at")},
    }
    econ = case["economics_inputs"]
    assumptions = {key: econ[key] for key in ("acquisition_cost", "tax", "inbound_shipping", "outbound_shipping", "marketplace_fees", "payment_fees", "packaging", "return_allowance", "expected_resale_price")}
    return {"now": NOW, "source_candidate": source, "resale_evidence": resale, "assumptions": assumptions}


class CanonicalRuntimeTests(unittest.TestCase):
    def test_all_canonical_fixtures_replay_through_cli(self):
        package = json.loads(FIXTURES.read_text(encoding="utf-8"))
        for case in package["fixtures"]:
            with self.subTest(fixture=case["id"]):
                input_path = ROOT / "tests" / ".canonical-runtime-input.json"
                input_path.write_text(json.dumps(_payload(case)), encoding="utf-8")
                try:
                    proc = subprocess.run([sys.executable, "-m", "hermes_resale_research", str(input_path)], text=True, capture_output=True, cwd=ROOT, env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")})
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    actual = json.loads(proc.stdout)["decision"]
                    expected = case["decision_audit"]
                    self.assertEqual(actual["recommendation"], expected["expected_recommendation"])
                    self.assertEqual(actual["reason_codes"], expected["expected_reason_codes"])
                finally:
                    input_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
