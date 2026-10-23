from __future__ import annotations
from .models import *
from decimal import Decimal

# These fields are the minimum evidence needed for a purchase recommendation.
# Keep this check here (rather than relying on the route-specific branches below)
# so every caller gets the same fail-closed BUY gate.
_CRITICAL_FRESHNESS_FIELDS = {
    "source_price": ("source_price",),
    "stock": ("stock_status", "stock"),
    "sold_evidence": ("sold_evidence",),
    "fees": ("fees",),
    "shipping": ("shipping_estimate", "shipping"),
    "identity": ("identity", "identity_evidence"),
    "active_competition": ("active_competition",),
    "seller_count": ("seller_count",),
}


def _critical_freshness_failures(freshness):
    failures = []
    for gate, names in _CRITICAL_FRESHNESS_FIELDS.items():
        field = next((freshness.fields.get(name) for name in names if name in freshness.fields), None)
        # A missing critical field is a failed gate too.  This is deliberately
        # stricter than checking only the aggregate freshness status.
        if field is None or not field.buy_gate_pass or field.state not in (FreshnessState.LIVE, FreshnessState.FRESH):
            failures.append(gate)
    return failures


def recommend(identity, freshness, economics, score, market=None, source_stock_status=None):
    failed=[]; reasons=[]
    if identity.status in (IdentityStatus.REJECT, IdentityStatus.LOW, IdentityStatus.MEDIUM) and identity.confidence < .95:
        failed.append("identity"); reasons.append("IDENTITY_NOT_PROVEN")

    critical_failures = _critical_freshness_failures(freshness)
    non_current_fields = [
        field for field in freshness.fields.values()
        if not field.buy_gate_pass or field.state not in (FreshnessState.LIVE, FreshnessState.FRESH)
    ]
    if critical_failures or non_current_fields:
        failed.extend(critical_failures)
        failed.extend(field.field for field in non_current_fields)
        failed.append("freshness")
        for gate in critical_failures:
            field = next((freshness.fields.get(name) for name in _CRITICAL_FRESHNESS_FIELDS[gate] if name in freshness.fields), None)
            code = {
                "source_price": "SOURCE_PRICE_NOT_CURRENT",
                "stock": "STOCK_NOT_CURRENT",
                "sold_evidence": "SOLD_EVIDENCE_STALE" if field and field.state in (FreshnessState.AGING, FreshnessState.STALE) else "SOLD_EVIDENCE_UNAVAILABLE",
                "fees": "COST_INPUT_NOT_CURRENT",
                "shipping": "COST_INPUT_NOT_CURRENT",
                "identity": "IDENTITY_NOT_CURRENT",
                "active_competition": "MARKET_CONTEXT_NOT_CURRENT",
                "seller_count": "MARKET_CONTEXT_NOT_CURRENT",
            }[gate]
            reasons.append(code)
    if market and (market.evidence_type != "OBSERVED" or (market.sold_count or 0) < 3):
        failed.append("sold_evidence"); reasons.append("SOLD_EVIDENCE_UNAVAILABLE" if market.evidence_type != "OBSERVED" else "SOLD_COUNT_BELOW_MINIMUM")
    if (source_stock_status or (getattr(market, "stock_status", None) if market else None)) == "OUT_OF_STOCK": failed.append("stock"); reasons.append("OUT_OF_STOCK")
    if economics.calculation_status != "COMPLETE" or economics.expected_net_profit is None: failed.append("economics"); reasons.append("ECONOMICS_INCOMPLETE")
    elif economics.expected_net_profit < Decimal("20") or economics.roi < Decimal("0.20") or economics.margin < Decimal("0.10"): failed.append("economics"); reasons.append("ECONOMICS_FAIL")
    if market and market.volatility=="HIGH": reasons.append("VOLATILITY_HIGH")
    if "identity" in failed: rec=Recommendation.SKIP
    elif (source_stock_status or (getattr(market, "stock_status", None) if market else None)) == "OUT_OF_STOCK": rec=Recommendation.SKIP
    elif "economics" in failed: rec=Recommendation.SKIP
    elif "sold_evidence" in failed and market and market.evidence_type != "OBSERVED": rec=Recommendation.SKIP
    elif "freshness" in failed: rec=Recommendation.RECHECK
    elif "sold_evidence" in failed: rec=Recommendation.SKIP if not market or market.evidence_type != "OBSERVED" or not (market.sold_count or 0) else Recommendation.WATCH
    elif market and market.volatility=="HIGH": rec=Recommendation.WATCH
    else: rec=Recommendation.BUY_CANDIDATE
    conf=max(0,min(100,int(score.score)))
    if rec == Recommendation.BUY_CANDIDATE and conf < 70:
        rec = Recommendation.WATCH
        failed.append("confidence")
        reasons.append("CONFIDENCE_BELOW_MINIMUM")
    return Decision(rec, score.score, tuple(dict.fromkeys(reasons or ["ALL_REQUIRED_GATES_PASS"])), tuple(dict.fromkeys(failed)), conf, ("final source price and stock recheck required before purchase",) if rec==Recommendation.BUY_CANDIDATE else ())
