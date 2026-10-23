import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import unittest
from hermes_resale_research import *

NOW=datetime(2026,10,22,12,tzinfo=timezone.utc)
class CoreTests(unittest.TestCase):
    def source(self, **kw):
        base=dict(source_marketplace="Walmart",source_url="https://example.test/x",product_name="Widget Pro",brand="Acme",model="W-1",upc="123",condition="NEW",source_price=40,stock_status="IN_STOCK",source_observed_at=NOW-timedelta(minutes=10),provenance={"operator_id":"u1","timestamp_quality":"PROVIDER_ASSERTED"},confidence=.9)
        base.update(kw); return SourceCandidate(**base)
    def resale(self, **kw):
        base=dict(resale_marketplace="eBay",product_name="Widget Pro",brand="Acme",model="W-1",upc="123",condition="NEW",recent_sold_median=60,sold_count=5,sold_window_days=90,active_listing_count=10,seller_count=4,evidence_observed_at=NOW-timedelta(minutes=10),evidence_type="OBSERVED",provenance={"timestamp_quality":"PROVIDER_ASSERTED"},stock_status="IN_STOCK",fees_observed_at=NOW-timedelta(minutes=10),shipping_observed_at=NOW-timedelta(minutes=10))
        base.update(kw); return ResaleEvidence(**base)
    def test_hard_identifier_and_variation_conflicts_reject(self):
        self.assertEqual(compare_identity(self.source(),self.resale(upc="999")).status, IdentityStatus.REJECT)
        self.assertEqual(compare_identity(self.source(variation_attributes={"pack_quantity":1}),self.resale(variation_attributes={"pack_quantity":2})).status, IdentityStatus.REJECT)
    def test_arbitrary_variation_conflict_rejects(self):
        result = compare_identity(
            self.source(variation_attributes={"flavor": "vanilla"}),
            self.resale(variation_attributes={"flavor": "chocolate"}),
        )
        self.assertEqual(result.status, IdentityStatus.REJECT)
        self.assertIn("flavor", result.conflicting_fields)

    def test_title_only_never_high(self):
        result=compare_identity(self.source(upc=None,model=None,brand=None),self.resale(upc=None,model=None,brand=None))
        self.assertNotIn(result.status,(IdentityStatus.VERIFIED,IdentityStatus.HIGH))
    def test_freshness_boundary_and_future(self):
        a=classify_freshness({"source_price":{"value":1,"observed_at":NOW-timedelta(minutes=30)}},NOW)
        self.assertTrue(a.fields["source_price"].buy_gate_pass)
        b=classify_freshness({"source_price":{"value":1,"observed_at":NOW+timedelta(minutes=6)}},NOW)
        self.assertEqual(b.fields["source_price"].state,FreshnessState.UNVERIFIED)
    def test_economics_rounding_and_missing(self):
        e=evaluate_economics(dict(acquisition_cost=25,tax=2,inbound_shipping=1,outbound_shipping=3,marketplace_fees=3,payment_fees=1,packaging=1,return_allowance=1,expected_resale_price=60))
        self.assertEqual(e.expected_net_profit,Decimal("23.00")); self.assertEqual(e.break_even_resale_price,Decimal("37.00"))
        self.assertEqual(evaluate_economics({"acquisition_cost":1}).calculation_status,"INCOMPLETE")
    def test_recommendation_requires_recheck_text(self):
        a=evaluate_opportunity(self.source(),self.resale(),dict(acquisition_cost=25,tax=2,inbound_shipping=1,outbound_shipping=3,marketplace_fees=3,payment_fees=1,packaging=1,return_allowance=1,expected_resale_price=60),NOW)
        self.assertEqual(a.decision.recommendation,Recommendation.BUY_CANDIDATE)
        self.assertTrue(a.decision.human_recheck_required)

    def assumptions(self):
        return dict(acquisition_cost=25,tax=2,inbound_shipping=1,outbound_shipping=3,marketplace_fees=3,payment_fees=1,packaging=1,return_allowance=1,expected_resale_price=60)

    def test_aging_source_price_can_never_buy(self):
        a=evaluate_opportunity(self.source(source_observed_at=NOW-timedelta(minutes=31)), self.resale(), self.assumptions(), NOW)
        self.assertEqual(a.freshness.fields["source_price"].state, FreshnessState.AGING)
        self.assertFalse(a.freshness.fields["source_price"].buy_gate_pass)
        self.assertEqual(a.decision.recommendation, Recommendation.RECHECK)
        self.assertIn("SOURCE_PRICE_NOT_CURRENT", a.decision.reason_codes)

    def test_aging_sold_fees_and_shipping_can_never_buy(self):
        old = NOW-timedelta(hours=25)
        a=evaluate_opportunity(self.source(), self.resale(evidence_observed_at=old, fees_observed_at=old, shipping_observed_at=old), self.assumptions(), NOW)
        for field in ("sold_evidence", "fees", "shipping_estimate"):
            self.assertEqual(a.freshness.fields[field].state, FreshnessState.AGING)
            self.assertFalse(a.freshness.fields[field].buy_gate_pass)
        self.assertNotEqual(a.decision.recommendation, Recommendation.BUY_CANDIDATE)
        self.assertIn("SOLD_EVIDENCE_STALE", a.decision.reason_codes)
        self.assertNotIn("SOLD_EVIDENCE_NOT_CURRENT", a.decision.reason_codes)
        self.assertEqual(a.freshness.fields["sold_evidence"].reason_codes, ("SOLD_EVIDENCE_STALE",))
        self.assertIn("COST_INPUT_NOT_CURRENT", a.decision.reason_codes)
        self.assertEqual(a.freshness.fields["fees"].reason_codes, ("COST_INPUT_NOT_CURRENT",))
        self.assertEqual(a.freshness.fields["shipping_estimate"].reason_codes, ("COST_INPUT_NOT_CURRENT",))
        self.assertNotIn("FEES_NOT_CURRENT", a.decision.reason_codes)
        self.assertNotIn("SHIPPING_ESTIMATE_NOT_CURRENT", a.decision.reason_codes)

    def test_stale_active_competition_and_seller_count_use_market_context_code(self):
        old = NOW-timedelta(hours=25)
        a=evaluate_opportunity(self.source(), self.resale(evidence_observed_at=old), self.assumptions(), NOW)
        for field in ("active_competition", "seller_count"):
            self.assertEqual(a.freshness.fields[field].state, FreshnessState.AGING)
            self.assertEqual(a.freshness.fields[field].reason_codes, ("MARKET_CONTEXT_NOT_CURRENT",))
        self.assertIn("MARKET_CONTEXT_NOT_CURRENT", a.decision.reason_codes)
        self.assertNotIn("ACTIVE_COMPETITION_NOT_CURRENT", a.decision.reason_codes)
        self.assertNotIn("SELLER_COUNT_NOT_CURRENT", a.decision.reason_codes)

    def test_buy_gate_false_blocks_even_live_field(self):
        identity = compare_identity(self.source(), self.resale())
        freshness = classify_freshness({
            "source_price": {"value": 40, "observed_at": NOW, "provider_live": True},
            "stock_status": {"value": "IN_STOCK", "observed_at": NOW, "provider_live": True},
            "sold_evidence": {"value": 60, "observed_at": NOW},
            "fees": {"value": 3, "observed_at": NOW},
            "shipping_estimate": {"value": 3, "observed_at": NOW},
            "identity": {"value": identity.confidence, "observed_at": NOW},
        }, NOW)
        from dataclasses import replace
        freshness = replace(freshness, fields={**freshness.fields, "fees": replace(freshness.fields["fees"], buy_gate_pass=False)})
        economics = evaluate_economics(self.assumptions())
        decision = recommend(identity, freshness, economics, score_opportunity(identity, freshness, economics, self.resale()), self.resale())
        self.assertNotEqual(decision.recommendation, Recommendation.BUY_CANDIDATE)
        self.assertIn("fees", decision.failed_gates)

    def test_missing_market_context_cannot_buy(self):
        a=evaluate_opportunity(self.source(), self.resale(active_listing_count=None, seller_count=None), self.assumptions(), NOW)
        self.assertNotEqual(a.decision.recommendation, Recommendation.BUY_CANDIDATE)
        self.assertIn("active_competition", a.decision.failed_gates)
        self.assertIn("seller_count", a.decision.failed_gates)
        self.assertEqual(a.freshness.fields["active_competition"].reason_codes, ("MARKET_CONTEXT_NOT_CURRENT",))
        self.assertEqual(a.freshness.fields["seller_count"].reason_codes, ("MARKET_CONTEXT_NOT_CURRENT",))
        self.assertEqual(a.decision.reason_codes, ("MARKET_CONTEXT_NOT_CURRENT",))
        self.assertNotIn("ACTIVE_COMPETITION_NOT_CURRENT", a.decision.reason_codes)
        self.assertNotIn("SELLER_COUNT_NOT_CURRENT", a.decision.reason_codes)

    def test_out_of_stock_skips(self):
        a=evaluate_opportunity(self.source(stock_status="OUT_OF_STOCK"),self.resale(stock_status="OUT_OF_STOCK"),dict(acquisition_cost=25,tax=2,inbound_shipping=1,outbound_shipping=3,marketplace_fees=3,payment_fees=1,packaging=1,return_allowance=1,expected_resale_price=60),NOW)
        self.assertEqual(a.decision.recommendation,Recommendation.SKIP)


    def test_active_asking_price_is_unavailable(self):
        item, errors = validate_resale_evidence({"resale_marketplace":"eBay", "asking_price": 80, "provenance":{"source":"manual"}})
        self.assertEqual(item.evidence_type, "UNAVAILABLE")
        self.assertEqual(errors, ())
        self.assertIsNone(item.recent_sold_median)

    def test_invalid_observed_evidence_fails_closed(self):
        raw=dict(self.resale().__dict__)
        raw["recent_sold_median"] = -1
        a=evaluate_opportunity(self.source(), raw, dict(acquisition_cost=25,tax=2,inbound_shipping=1,outbound_shipping=3,marketplace_fees=3,payment_fees=1,packaging=1,return_allowance=1,expected_resale_price=60), NOW)
        self.assertIn("NEGATIVE_SOLD_PRICE", a.decision.reason_codes)
        self.assertNotEqual(a.decision.recommendation, Recommendation.BUY_CANDIDATE)

    def test_mapping_input_and_timestamp_normalization(self):
        a=evaluate_opportunity(self.source().__dict__, self.resale().__dict__, dict(acquisition_cost=25,tax=2,inbound_shipping=1,outbound_shipping=3,marketplace_fees=3,payment_fees=1,packaging=1,return_allowance=1,expected_resale_price=60), NOW)
        self.assertEqual(a.decision.recommendation, Recommendation.BUY_CANDIDATE)

if __name__ == "__main__": unittest.main()
