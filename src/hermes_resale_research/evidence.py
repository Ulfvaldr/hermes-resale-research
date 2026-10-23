"""Fail-closed normalization and validation for manually supplied eBay evidence."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
from .models import ResaleEvidence

EVIDENCE_TYPES = {"OBSERVED", "INFERRED", "ESTIMATED", "UNAVAILABLE"}

def _time(value: Any) -> datetime | str | None:
    if value is None or isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return value

def _decimal(value: Any) -> Any:
    if value is None or isinstance(value, Decimal): return value
    try: return Decimal(str(value))
    except (InvalidOperation, ValueError): return value

def normalize_resale_evidence(raw: ResaleEvidence | Mapping[str, Any]) -> ResaleEvidence:
    """Normalize JSON/manual input without ever treating asking price as sold data."""
    if isinstance(raw, ResaleEvidence): return raw
    data = dict(raw)
    data["evidence_type"] = str(data.get("evidence_type") or "UNAVAILABLE").upper()
    if data["evidence_type"] not in EVIDENCE_TYPES:
        data["evidence_type"] = "UNAVAILABLE"
    # Asking prices are valid only when explicitly marked active-listing evidence;
    # an unscoped asking_price is rejected rather than silently entering economics.
    if data.get("asking_price") is not None:
        data["asking_price"] = _decimal(data["asking_price"])
        data.setdefault("provenance", {})
        scope = data["provenance"].get("evidence_scope")
        if scope in {"ACTIVE_ASKING", "COMBINED"}:
            if scope == "ACTIVE_ASKING" and data.get("recent_sold_median") is not None:
                data["recent_sold_median"] = None
        else:
            data["evidence_type"] = "UNAVAILABLE"
            data["asking_price"] = None
    for key in ("recent_sold_median",): data[key] = _decimal(data.get(key))
    for key in ("evidence_observed_at", "fees_observed_at", "shipping_observed_at"): data[key] = _time(data.get(key))
    allowed = {f.name for f in ResaleEvidence.__dataclass_fields__.values()}
    return ResaleEvidence(**{k: v for k, v in data.items() if k in allowed})

def validate_resale_evidence(evidence: ResaleEvidence | Mapping[str, Any]) -> tuple[ResaleEvidence, tuple[str, ...]]:
    """Return normalized evidence and stable validation codes; callers can fail closed."""
    item = normalize_resale_evidence(evidence)
    errors = []
    if item.resale_marketplace.lower() != "ebay": errors.append("UNSUPPORTED_RESALE_MARKETPLACE")
    if item.evidence_type not in EVIDENCE_TYPES: errors.append("INVALID_EVIDENCE_TYPE")
    active_only = item.provenance.get("evidence_scope") == "ACTIVE_ASKING"
    if item.evidence_type == "OBSERVED" and item.recent_sold_median is None and not active_only: errors.append("OBSERVED_SOLD_PRICE_MISSING")
    if item.recent_sold_median is not None and item.recent_sold_median < 0: errors.append("NEGATIVE_SOLD_PRICE")
    if item.sold_count is not None and item.sold_count < 0: errors.append("NEGATIVE_SOLD_COUNT")
    if item.evidence_type != "UNAVAILABLE" and item.evidence_observed_at is None: errors.append("EVIDENCE_TIMESTAMP_MISSING")
    if not item.provenance: errors.append("PROVENANCE_MISSING")
    return item, tuple(dict.fromkeys(errors))
