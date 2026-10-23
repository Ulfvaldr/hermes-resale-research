from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import replace
from .models import OpportunityAssessment, SourceCandidate, ResaleEvidence
from .identity import compare_identity
from .freshness import classify_freshness, parse_time
from .economics import evaluate_economics
from .scoring import score_opportunity
from .recommendations import recommend
from .evidence import normalize_resale_evidence, validate_resale_evidence
from .adapter import EbayEvidenceAdapter, UnavailableEbayAdapter

def _source(raw):
    if isinstance(raw, SourceCandidate): return raw
    data = dict(raw)
    if data.get("source_price") is not None: data["source_price"] = Decimal(str(data["source_price"]))
    if data.get("source_observed_at") is not None: data["source_observed_at"] = parse_time(data["source_observed_at"])
    return SourceCandidate(**{k:v for k,v in data.items() if k in SourceCandidate.__dataclass_fields__})

def evaluate_opportunity(source_candidate, resale_evidence, assumptions, now=None):
    """Run the complete offline Phase 1 flow on models or JSON-shaped mappings."""
    now = now or datetime.now(timezone.utc)
    source_candidate = _source(source_candidate)
    resale_evidence, evidence_errors = validate_resale_evidence(resale_evidence)
    # Malformed evidence must never enter economics as if it were valid sold history.
    if evidence_errors:
        resale_evidence = replace(resale_evidence, evidence_type="UNAVAILABLE", recent_sold_median=None,
                                  provenance={**dict(resale_evidence.provenance), "validation_errors": evidence_errors})
    identity = compare_identity(source_candidate, resale_evidence)
    provenance = dict(source_candidate.provenance)
    price_observed_at = provenance.get("price_observed_at", source_candidate.source_observed_at)
    stock_observed_at = provenance.get("stock_observed_at", source_candidate.source_observed_at)
    market_context_current = provenance.get("market_context_current", True)
    active_observed_at = resale_evidence.provenance.get("active_observed_at", resale_evidence.evidence_observed_at)
    seller_observed_at = resale_evidence.provenance.get("seller_observed_at", resale_evidence.evidence_observed_at)
    obs = {"source_price":{"value":source_candidate.source_price,"observed_at":price_observed_at,"timestamp_quality":provenance.get("price_timestamp_quality", provenance.get("timestamp_quality","PROVIDER_ASSERTED"))},"stock_status":{"value":source_candidate.stock_status,"observed_at":stock_observed_at,"timestamp_quality":provenance.get("stock_timestamp_quality", provenance.get("timestamp_quality","PROVIDER_ASSERTED"))},"sold_evidence":{"value":resale_evidence.recent_sold_median,"observed_at":resale_evidence.evidence_observed_at,"timestamp_quality":resale_evidence.provenance.get("timestamp_quality","PROVIDER_ASSERTED")},"active_competition":{"value":resale_evidence.active_listing_count if market_context_current else None,"observed_at":active_observed_at if market_context_current else None,"timestamp_quality":resale_evidence.provenance.get("timestamp_quality","PROVIDER_ASSERTED")},"seller_count":{"value":resale_evidence.seller_count if market_context_current else None,"observed_at":seller_observed_at if market_context_current else None,"timestamp_quality":resale_evidence.provenance.get("timestamp_quality","PROVIDER_ASSERTED")},"fees":{"value":assumptions.get("marketplace_fees"),"observed_at":resale_evidence.fees_observed_at},"shipping_estimate":{"value":assumptions.get("outbound_shipping"),"observed_at":resale_evidence.shipping_observed_at},"identity":{"value":identity.confidence,"observed_at":source_candidate.source_observed_at}}
    freshness = classify_freshness(obs, now)
    economics = evaluate_economics(assumptions)
    score = score_opportunity(identity, freshness, economics, resale_evidence)
    decision = recommend(identity, freshness, economics, score, resale_evidence, source_stock_status=source_candidate.stock_status)
    if evidence_errors:
        decision = replace(decision, reason_codes=tuple(dict.fromkeys((*evidence_errors, *decision.reason_codes))), recommendation=decision.recommendation)
    return OpportunityAssessment(identity, freshness, economics, score, decision, resale_evidence, now, provenance, resale_evidence.provenance)


def _adapter_query(source: SourceCandidate) -> str:
    """Build a non-secret Browse query from the source identity."""
    for value in (source.upc, source.ean, source.gtin, source.model, source.product_name):
        if value:
            return str(value)
    return ""


def evaluate_opportunity_from_adapter(source_candidate, assumptions, adapter: EbayEvidenceAdapter | None = None,
                                      query: str | None = None, now=None):
    """Fetch one eBay evidence bundle, then delegate to the deterministic core.

    Active and sold results are deliberately merged only by their distinct roles:
    active counts/asking fields are retained as market context, while sold price,
    count, and evidence type come only from the sold result. Adapter failures are
    converted to UNAVAILABLE rather than escaping into a purchase decision.
    """
    source = _source(source_candidate)
    adapter = adapter or UnavailableEbayAdapter()
    query = str(query if query is not None else _adapter_query(source))
    try:
        active = normalize_resale_evidence(adapter.fetch_active_listings(query))
    except Exception:
        active = ResaleEvidence(evidence_type="UNAVAILABLE", provenance={"reason": "ACTIVE_EVIDENCE_UNAVAILABLE", "query": query})
    try:
        sold = normalize_resale_evidence(adapter.fetch_sold_evidence(query))
    except Exception:
        sold = ResaleEvidence(evidence_type="UNAVAILABLE", provenance={"reason": "SOLD_EVIDENCE_UNAVAILABLE", "query": query})

    # Start with sold evidence so active asking data can never populate sold fields.
    merged = dict(sold.__dict__)
    for key in ("active_listing_count", "seller_count", "asking_price", "asking_currency", "estimated_sold_quantity"):
        value = getattr(active, key)
        if value is not None:
            merged[key] = value
    if sold.evidence_type == "UNAVAILABLE" and active.evidence_observed_at is not None:
        # This timestamp is valid for active market context, but the missing sold
        # value remains missing and therefore fails the sold-evidence gate.
        merged["evidence_observed_at"] = active.evidence_observed_at
    merged["provenance"] = {
        "adapter": "ebay",
        "query": query,
        "active": dict(active.provenance),
        "sold": dict(sold.provenance),
    }
    if active.asking_price is not None:
        merged["provenance"]["evidence_scope"] = "COMBINED" if sold.recent_sold_median is not None else "ACTIVE_ASKING"
    return evaluate_opportunity(source, merged, assumptions, now)
