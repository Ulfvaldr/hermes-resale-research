"""Bounded, deterministic Phase 2 batch evaluation and presentation.

Discovery adapters only supply JSON-shaped candidates. All identity, freshness,
economics, scoring, and recommendation decisions remain in ``workflow``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Mapping

from .models import Recommendation
from .workflow import evaluate_opportunity

DEFAULT_LIMIT = 10
_RECOMMENDATION_ORDER = {
    Recommendation.BUY_CANDIDATE.value: 0,
    Recommendation.WATCH.value: 1,
    Recommendation.RECHECK.value: 2,
    Recommendation.SKIP.value: 3,
}


def discover_candidates(records: Iterable[Mapping[str, Any]], limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    """Return a bounded, stable candidate set from a discovery/enrichment feed.

    A record is intentionally not interpreted beyond its Phase 1 input fields;
    adapters may add ``candidate_id`` and ``discovery`` metadata. Duplicate IDs
    are kept once, with the first record winning deterministically.
    """
    if limit < 1:
        return []
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        item = dict(record)
        candidate_id = str(item.get("candidate_id") or f"candidate-{index + 1:04d}")
        if candidate_id in seen:
            continue
        if not isinstance(item.get("source_candidate"), Mapping):
            continue
        seen.add(candidate_id)
        item["candidate_id"] = candidate_id
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def enrich_candidates(
    records: Iterable[Mapping[str, Any]],
    enricher: Any | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Apply an optional adapter-owned enrichment step to bounded candidates."""
    candidates = discover_candidates(records, limit=limit)
    if enricher is None:
        return candidates
    enriched: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            update = enricher(dict(candidate))
            enriched.append({**candidate, **dict(update or {})})
        except Exception as exc:
            enriched.append({**candidate, "enrichment_error": str(exc)})
    return enriched


def _source_store(candidate: Mapping[str, Any]) -> str:
    discovery = candidate.get("discovery") or {}
    source = candidate.get("source_candidate") or {}
    return str(discovery.get("store") or source.get("source_marketplace") or "unknown")


def _quality(assessment: Any) -> str:
    if assessment.decision.recommendation == Recommendation.SKIP:
        return "REJECTED"
    if assessment.identity.confidence >= 0.95 and not assessment.decision.failed_gates:
        return "HIGH"
    if assessment.identity.confidence >= 0.8:
        return "MEDIUM"
    return "LOW"


def _explanation(assessment: Any) -> str:
    parts = list(assessment.score.explanation)
    if assessment.decision.reason_codes:
        parts.extend(assessment.decision.reason_codes)
    return "; ".join(dict.fromkeys(str(part) for part in parts)) or "No explanation available"


def _item(candidate: Mapping[str, Any], assessment: Any) -> dict[str, Any]:
    economics = assessment.economics
    decision = assessment.decision
    source = candidate.get("source_candidate") or {}
    discovery = candidate.get("discovery") or {}
    return {
        "candidate_id": str(candidate["candidate_id"]),
        "product_name": str(source.get("product_name") or "Unknown product"),
        "source_store": _source_store(candidate),
        "source_price": source.get("source_price"),
        "expected_resale_price": economics.expected_resale_price,
        "estimated_net_profit": economics.expected_net_profit,
        "roi": economics.roi,
        "break_even_price": economics.break_even_resale_price,
        "recommendation": decision.recommendation.value,
        "confidence": decision.confidence,
        "evidence_quality": _quality(assessment),
        "explanation": _explanation(assessment),
        "failed_gates": list(decision.failed_gates),
        "reason_codes": list(decision.reason_codes),
        "source_provenance": {**dict(source.get("provenance") or {}), **dict(discovery)},
        "resale_provenance": dict(assessment.resale_provenance),
        "human_approval_required": True,
        "eligible": decision.recommendation != Recommendation.SKIP,
    }


def _sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    def decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value)) if value is not None else Decimal("-Infinity")
        except Exception:
            return Decimal("-Infinity")

    return (
        _RECOMMENDATION_ORDER.get(str(item["recommendation"]), 99),
        -decimal(item.get("estimated_net_profit")),
        -decimal(item.get("roi")),
        -int(item.get("confidence") or 0),
        str(item["candidate_id"]),
    )


def evaluate_batch(
    records: Iterable[Mapping[str, Any]],
    assumptions: Mapping[str, Any] | None = None,
    *,
    now: datetime | None = None,
    limit: int = DEFAULT_LIMIT,
    include_rejected: bool = False,
) -> dict[str, Any]:
    """Evaluate a bounded batch and return JSON-ready ranked output.

    Each record may carry its own ``assumptions``; the function-level defaults
    fill only when a record does not. Rejected candidates stay in ``rejected``
    for auditability and never appear in ``items`` unless requested.
    """
    now = now or datetime.now(timezone.utc)
    candidates = enrich_candidates(records, limit=limit)
    evaluated: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            if candidate.get("enrichment_error"):
                raise ValueError(f"ENRICHMENT_FAILED: {candidate['enrichment_error']}")
            assessment = evaluate_opportunity(
                candidate["source_candidate"],
                candidate.get("resale_evidence") or {},
                candidate.get("assumptions") or assumptions or {},
                now=now,
            )
            evaluated.append(_item(candidate, assessment))
        except (TypeError, ValueError, KeyError) as exc:
            evaluated.append({
                "candidate_id": candidate["candidate_id"],
                "product_name": str((candidate.get("source_candidate") or {}).get("product_name") or "Unknown product"),
                "source_store": _source_store(candidate),
                "source_price": (candidate.get("source_candidate") or {}).get("source_price"),
                "expected_resale_price": None, "estimated_net_profit": None, "roi": None,
                "break_even_price": None, "recommendation": Recommendation.SKIP.value,
                "confidence": 0, "evidence_quality": "REJECTED",
                "explanation": f"INVALID_CANDIDATE: {exc}", "failed_gates": ["candidate_validation"],
                "reason_codes": ["INVALID_CANDIDATE"], "source_provenance": dict((candidate.get("discovery") or {})),
                "resale_provenance": {}, "human_approval_required": True, "eligible": False,
            })
    evaluated.sort(key=_sort_key)
    rejected = [item for item in evaluated if not item["eligible"]]
    items = evaluated if include_rejected else [item for item in evaluated if item["eligible"]]
    return {
        "title": "Today's Resale Opportunity Candidates",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "bounded_limit": limit,
        "evaluated_count": len(evaluated),
        "candidate_count": len(candidates),
        "items": items,
        "rejected": rejected,
        "research_only": True,
        "human_approval_required": True,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render the compact inspectable daily report without making decisions."""
    lines = [str(report.get("title", "Today's Resale Opportunity Candidates")), ""]
    items = report.get("items", [])
    if not items:
        lines.append("No evidence-backed candidates passed the presentation filter.")
    for index, item in enumerate(items, 1):
        lines.extend([
            f"{index}. {item['product_name']} — {item['recommendation']} ({item['evidence_quality']})",
            f"   Source: {item['source_store']} at {item['source_price']}; resale: {item['expected_resale_price']}; net: {item['estimated_net_profit']}; ROI: {item['roi']}; break-even: {item['break_even_price']}",
            f"   Confidence: {item['confidence']}; {item['explanation']}",
            f"   Evidence: {item['resale_provenance']}",
        ])
    lines.extend(["", f"Evaluated: {report.get('evaluated_count', 0)}; rejected: {len(report.get('rejected', []))}; research-only; human approval required."])
    return "\n".join(lines)
