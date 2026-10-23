import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from hermes_resale_research import (
    FakeEbayEvidenceAdapter,
    LiveEbayBrowseAdapter,
    Recommendation,
    ResaleEvidence,
    SourceCandidate,
    UnavailableEbayAdapter,
    evaluate_opportunity_from_adapter,
    validate_resale_evidence,
)


NOW = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)


def source(**overrides):
    base = dict(
        source_marketplace="Walmart",
        source_url="https://example.test/source/widget-pro",
        product_name="Widget Pro",
        brand="Acme",
        model="W-1",
        upc="123456789012",
        condition="NEW",
        source_price=Decimal("40.00"),
        stock_status="IN_STOCK",
        source_observed_at=NOW - timedelta(minutes=10),
        provenance={"operator_id": "tester", "timestamp_quality": "PROVIDER_ASSERTED"},
        confidence=.98,
    )
    base.update(overrides)
    return SourceCandidate(**base)


def assumptions(**overrides):
    base = dict(
        acquisition_cost=25,
        tax=2,
        inbound_shipping=1,
        outbound_shipping=3,
        marketplace_fees=3,
        payment_fees=1,
        packaging=1,
        return_allowance=1,
        expected_resale_price=60,
    )
    base.update(overrides)
    return base


def sold_evidence(**overrides):
    base = dict(
        resale_marketplace="eBay",
        product_name="Widget Pro",
        brand="Acme",
        model="W-1",
        upc="123456789012",
        condition="NEW",
        recent_sold_median=Decimal("60.00"),
        sold_count=8,
        sold_window_days=90,
        evidence_observed_at=NOW - timedelta(minutes=10),
        evidence_type="OBSERVED",
        provenance={"source": "manual_sold_export", "timestamp_quality": "PROVIDER_ASSERTED"},
        fees_observed_at=NOW - timedelta(minutes=10),
        shipping_observed_at=NOW - timedelta(minutes=10),
        stock_status="IN_STOCK",
    )
    base.update(overrides)
    return ResaleEvidence(**base)


def active_evidence(**overrides):
    base = dict(
        resale_marketplace="eBay",
        product_name="Widget Pro",
        brand="Acme",
        model="W-1",
        upc="123456789012",
        condition="NEW",
        active_listing_count=11,
        seller_count=5,
        evidence_observed_at=NOW - timedelta(minutes=10),
        evidence_type="OBSERVED",
        provenance={"timestamp_quality": "PROVIDER_ASSERTED", "evidence_scope": "ACTIVE_ASKING"},
        asking_price=Decimal("84.99"),
        asking_currency="USD",
        estimated_sold_quantity=4,
    )
    base.update(overrides)
    return ResaleEvidence(**base)


class FakeEbayEvidenceAdapterTests(unittest.TestCase):
    def test_fake_adapter_is_deterministic_and_query_scoped(self):
        adapter = FakeEbayEvidenceAdapter(active=active_evidence(), sold=sold_evidence())

        first_active = adapter.fetch_active_listings("Widget Pro")
        second_active = adapter.fetch_active_listings("Widget Pro")
        first_sold = adapter.fetch_sold_evidence("Widget Pro")
        second_sold = adapter.fetch_sold_evidence("Widget Pro")

        self.assertEqual(first_active, second_active)
        self.assertEqual(first_sold, second_sold)
        self.assertEqual(first_active.provenance["adapter"], "fake")
        self.assertEqual(first_active.provenance["query"], "Widget Pro")
        self.assertEqual(first_active.provenance["evidence_scope"], "ACTIVE_ASKING")
        self.assertEqual(first_sold.provenance["adapter"], "fake")
        self.assertEqual(first_sold.provenance["query"], "Widget Pro")

    def test_fake_adapter_requires_manual_sold_price_provenance(self):
        adapter = FakeEbayEvidenceAdapter(manual_sold=sold_evidence(provenance={}))

        item = adapter.fetch_sold_evidence("Widget Pro")

        self.assertEqual(item.evidence_type, "UNAVAILABLE")
        self.assertIsNone(item.recent_sold_median)
        self.assertEqual(item.provenance["reason"], "MANUAL_SOLD_PROVENANCE_REQUIRED")

    def test_fake_adapter_reports_unavailable_when_no_sold_history_source_exists(self):
        adapter = FakeEbayEvidenceAdapter(active=active_evidence())

        item = adapter.fetch_sold_evidence("Widget Pro")

        self.assertEqual(item.evidence_type, "UNAVAILABLE")
        self.assertIsNone(item.recent_sold_median)
        self.assertEqual(item.provenance["reason"], "SOLD_HISTORY_NOT_AVAILABLE")


class LiveEbayBrowseAdapterTests(unittest.TestCase):
    def test_missing_ebay_credentials_return_unavailable_without_network_or_crash(self):
        def fail_if_called(*args, **kwargs):
            raise AssertionError("network opener should not be called without credentials")

        with patch.dict(os.environ, {"EBAY_CLIENT_ID": "", "EBAY_CLIENT_SECRET": ""}, clear=False):
            adapter = LiveEbayBrowseAdapter(client_id=None, client_secret=None, opener=fail_if_called)
            item = adapter.fetch_active_listings("Widget Pro")

        self.assertEqual(item.evidence_type, "UNAVAILABLE")
        self.assertIsNone(item.recent_sold_median)
        self.assertEqual(item.provenance["reason"], "EBAY_API_UNAVAILABLE")

    def test_live_adapter_fetch_sold_evidence_requires_manual_approved_source(self):
        no_source = LiveEbayBrowseAdapter(client_id="id", client_secret="secret", manual_sold_source=None)
        missing_provenance = LiveEbayBrowseAdapter(client_id="id", client_secret="secret", manual_sold_source=sold_evidence(provenance={}))
        approved = LiveEbayBrowseAdapter(client_id="id", client_secret="secret", manual_sold_source=sold_evidence(provenance={"provider": "approved-export"}))

        unavailable = no_source.fetch_sold_evidence("Widget Pro")
        provenance_rejected = missing_provenance.fetch_sold_evidence("Widget Pro")
        observed = approved.fetch_sold_evidence("Widget Pro")

        self.assertEqual(unavailable.evidence_type, "UNAVAILABLE")
        self.assertEqual(unavailable.provenance["reason"], "SOLD_HISTORY_NOT_AVAILABLE")
        self.assertEqual(provenance_rejected.evidence_type, "UNAVAILABLE")
        self.assertEqual(provenance_rejected.provenance["reason"], "MANUAL_SOLD_PROVENANCE_REQUIRED")
        self.assertEqual(observed.evidence_type, "OBSERVED")
        self.assertEqual(observed.recent_sold_median, Decimal("60.00"))
        self.assertEqual(observed.provenance["provider"], "approved-export")

    def test_estimated_sold_quantity_from_active_listings_is_only_demand_context(self):
        calls = []

        class Response:
            def __init__(self, payload):
                self.payload = payload
            def __enter__(self):
                return self
            def __exit__(self, *exc):
                return False
            def read(self):
                import json
                return json.dumps(self.payload).encode("utf-8")

        def opener(request, timeout):
            calls.append(request.full_url)
            if request.full_url.endswith("/identity/v1/oauth2/token"):
                return Response({"access_token": "token", "expires_in": 3600})
            return Response({
                "total": 2,
                "itemSummaries": [
                    {"price": {"value": "80.00", "currency": "USD"}, "seller": {"username": "seller-a"}, "estimatedSoldQuantity": 3},
                    {"price": {"value": "100.00", "currency": "USD"}, "seller": {"username": "seller-b"}, "estimatedSoldQuantity": 4},
                ],
            })

        adapter = LiveEbayBrowseAdapter(client_id="id", client_secret="secret", opener=opener)
        item = adapter.fetch_active_listings("Widget Pro")

        self.assertEqual(len(calls), 2)
        self.assertEqual(item.evidence_type, "OBSERVED")
        self.assertEqual(item.provenance["evidence_scope"], "ACTIVE_ASKING")
        self.assertEqual(item.active_listing_count, 2)
        self.assertEqual(item.seller_count, 2)
        self.assertEqual(item.estimated_sold_quantity, 7)
        self.assertEqual(item.asking_price, Decimal("90.00"))
        self.assertIsNone(item.recent_sold_median)
        self.assertIsNone(item.sold_count)


class EbayEvidenceWorkflowTests(unittest.TestCase):
    def test_active_listing_normalization_never_substitutes_asking_price_for_sold_price(self):
        adapter = FakeEbayEvidenceAdapter(active=active_evidence(asking_price=Decimal("199.99")), sold=None)

        assessment = evaluate_opportunity_from_adapter(source(), assumptions(), adapter=adapter, query="Widget Pro", now=NOW)

        self.assertEqual(assessment.market.evidence_type, "UNAVAILABLE")
        self.assertIsNone(assessment.market.recent_sold_median)
        self.assertIsNone(assessment.market.sold_count)
        self.assertEqual(assessment.market.asking_price, Decimal("199.99"))
        self.assertEqual(assessment.market.estimated_sold_quantity, 4)
        self.assertNotEqual(assessment.decision.recommendation, Recommendation.BUY_CANDIDATE)
        self.assertIn("SOLD_EVIDENCE_UNAVAILABLE", assessment.decision.reason_codes)
        self.assertNotIn("SOLD_EVIDENCE_NOT_CURRENT", assessment.decision.reason_codes)

    def test_active_asking_price_requires_explicit_active_or_combined_scope(self):
        item, errors = validate_resale_evidence({
            "resale_marketplace": "eBay",
            "evidence_type": "OBSERVED",
            "asking_price": "80.00",
            "evidence_observed_at": NOW.isoformat(),
            "provenance": {"source": "active-listing-export"},
        })

        self.assertEqual(errors, ())
        self.assertEqual(item.evidence_type, "UNAVAILABLE")
        self.assertIsNone(item.asking_price)
        self.assertIsNone(item.recent_sold_median)

    def test_manual_sold_price_evidence_accepts_explicit_provenance(self):
        adapter = FakeEbayEvidenceAdapter(manual_sold=sold_evidence(provenance={"source_url": "https://example.test/sold-export"}))

        item = adapter.fetch_sold_evidence("Widget Pro")

        self.assertEqual(item.evidence_type, "OBSERVED")
        self.assertEqual(item.recent_sold_median, Decimal("60.00"))
        self.assertEqual(item.provenance["source_url"], "https://example.test/sold-export")

    def test_one_opportunity_end_to_end_workflow_uses_fake_adapter(self):
        adapter = FakeEbayEvidenceAdapter(active=active_evidence(), sold=sold_evidence())

        assessment = evaluate_opportunity_from_adapter(source(), assumptions(), adapter=adapter, query="Widget Pro", now=NOW)

        self.assertEqual(assessment.market.evidence_type, "OBSERVED")
        self.assertEqual(assessment.market.recent_sold_median, Decimal("60.00"))
        self.assertEqual(assessment.market.sold_count, 8)
        self.assertEqual(assessment.market.asking_price, Decimal("84.99"))
        self.assertEqual(assessment.market.estimated_sold_quantity, 4)
        self.assertEqual(assessment.resale_provenance["adapter"], "ebay")
        self.assertEqual(assessment.resale_provenance["query"], "Widget Pro")
        self.assertEqual(assessment.resale_provenance["active"]["adapter"], "fake")
        self.assertEqual(assessment.resale_provenance["sold"]["adapter"], "fake")
        self.assertEqual(assessment.decision.recommendation, Recommendation.BUY_CANDIDATE)


if __name__ == "__main__":
    unittest.main()
