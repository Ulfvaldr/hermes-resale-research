from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Mapping
from .models import FieldFreshness, FreshnessResult, FreshnessState

POLICY_VERSION = "freshness-v1"
PROFILES = {"source_price": (600,1800,7200,604800,1800), "stock_status": (600,1800,3600,86400,1800), "sold_evidence": (None,86400,259200,604800,86400), "active_competition": (None,86400,259200,604800,86400), "seller_count": (None,86400,259200,604800,86400), "fees": (None,86400,259200,604800,86400), "shipping_estimate": (None,86400,259200,604800,86400), "identity": (None,2592000,2592000,2592000,2592000)}
SEVERITY = {FreshnessState.LIVE:0, FreshnessState.FRESH:1, FreshnessState.AGING:2, FreshnessState.STALE:3, FreshnessState.UNVERIFIED:4, FreshnessState.MISSING:5, FreshnessState.CONFLICTING:6, FreshnessState.BLOCKED:7, FreshnessState.UNKNOWN:8}
def _non_current_reason(field: str, state: FreshnessState) -> str:
    if field in ("active_competition", "seller_count"):
        return "MARKET_CONTEXT_NOT_CURRENT"
    if field == "sold_evidence":
        return "SOLD_EVIDENCE_STALE" if state in (FreshnessState.AGING, FreshnessState.STALE) else "SOLD_EVIDENCE_UNAVAILABLE"
    if field in ("fees", "shipping_estimate"):
        return "COST_INPUT_NOT_CURRENT"
    return f"{field.upper()}_NOT_CURRENT"
def parse_time(v):
    if v is None: return None
    if isinstance(v, datetime): return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
def classify_field(field: str, observed_at: Any, now: datetime, *, timestamp_quality="PROVIDER_ASSERTED", provider_live=False, blocked=False, value_present=True, conflict=False) -> FieldFreshness:
    if blocked: return FieldFreshness(field, FreshnessState.BLOCKED, reason_codes=("ACCESS_BLOCKED",))
    if conflict: return FieldFreshness(field, FreshnessState.CONFLICTING, reason_codes=("OBSERVATION_CONFLICT",))
    t = parse_time(observed_at)
    if not value_present or t is None:
        reason = _non_current_reason(field, FreshnessState.MISSING) if field in ("sold_evidence", "active_competition", "seller_count") else "MISSING_CRITICAL_OBSERVATION"
        return FieldFreshness(field, FreshnessState.MISSING, t, reason_codes=(reason,))
    age = int((now - t).total_seconds())
    if age < -300: return FieldFreshness(field, FreshnessState.UNVERIFIED, t, age, ("CLOCK_SKEW_FUTURE",))
    if timestamp_quality in ("INFERRED", "MISSING", "USER_ENTERED_UNSUPPORTED"):
        reason = {"source_price": "SOURCE_PRICE_NOT_CURRENT", "stock_status": "STOCK_NOT_CURRENT"}.get(field, "TIMESTAMP_UNVERIFIED")
        return FieldFreshness(field, FreshnessState.UNVERIFIED, t, age, (reason,))
    live, fresh, aging, stale, buy = PROFILES.get(field, (None,86400,259200,604800,86400))
    if age > stale: state = FreshnessState.STALE
    elif aging is not None and age > aging: state = FreshnessState.AGING
    elif fresh is not None and age > fresh: state = FreshnessState.AGING
    elif provider_live and live is not None and age <= live: state = FreshnessState.LIVE
    else: state = FreshnessState.FRESH
    return FieldFreshness(field, state, t, age, (() if state in (FreshnessState.LIVE, FreshnessState.FRESH) else (_non_current_reason(field, state),)), age <= buy and state in (FreshnessState.LIVE, FreshnessState.FRESH))
def classify_freshness(evidence: Mapping[str, Any], now: datetime) -> FreshnessResult:
    fields = {}
    for name, raw in evidence.items():
        if isinstance(raw, Mapping):
            fields[name] = classify_field(name, raw.get("observed_at"), now, timestamp_quality=raw.get("timestamp_quality", "PROVIDER_ASSERTED"), provider_live=raw.get("provider_live", False), blocked=raw.get("blocked", False), value_present=raw.get("value") is not None, conflict=raw.get("conflict", False))
        else: fields[name] = classify_field(name, None, now, value_present=False)
    worst = max((x.state for x in fields.values()), key=lambda s: SEVERITY[s], default=FreshnessState.UNKNOWN)
    return FreshnessResult(fields, worst, tuple(sorted({r for x in fields.values() for r in x.reason_codes})), {"policy_version": POLICY_VERSION, "timezone":"UTC"})
