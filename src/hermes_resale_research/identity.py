from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import Any, Mapping
from .models import IdentityResult, IdentityStatus, SourceCandidate, ResaleEvidence

HARD = {"asin", "upc", "ean", "gtin", "model", "manufacturer_part_number", "pack_quantity", "size", "color", "generation_or_version", "bundle_contents"}
def _norm(v: Any) -> Any:
    if isinstance(v, str): return re.sub(r"\\s+", " ", v.strip().casefold())
    if isinstance(v, (list, tuple, set)): return tuple(sorted(_norm(x) for x in v))
    return v
def _get(x: Any, key: str) -> Any:
    if key in ("pack_quantity", "size", "color", "generation_or_version", "bundle_contents"):
        return _norm((getattr(x, "variation_attributes", {}) or {}).get(key))
    return _norm(getattr(x, key, None))

def compare_identity(source: SourceCandidate, resale: ResaleEvidence | Mapping[str, Any]) -> IdentityResult:
    # Compare every supplied variation attribute, not only the canonical named
    # attributes. A marketplace-specific attribute (for example, flavor) is
    # still identity-bearing and must fail closed on disagreement.
    source_variations = dict(getattr(source, "variation_attributes", {}) or {})
    resale_variations = dict(
        (resale.get("variation_attributes", {}) or {})
        if isinstance(resale, Mapping)
        else (getattr(resale, "variation_attributes", {}) or {})
    )
    fields = ("asin", "upc", "ean", "gtin", "model", "manufacturer_part_number", "brand", "condition")
    variation_fields = tuple(sorted(set(source_variations) | set(resale_variations)))
    def val(name):
        if name in variation_fields:
            return _norm(resale_variations.get(name))
        return _norm(resale.get(name)) if isinstance(resale, Mapping) else _get(resale, name)
    matched, conflicts = [], []
    for f in fields:
        a, b = _get(source, f), val(f)
        if a is not None and b is not None:
            (matched if a == b else conflicts).append(f)
    for f in variation_fields:
        a, b = _norm(source_variations.get(f)), _norm(resale_variations.get(f))
        if a is not None and b is not None:
            (matched if a == b else conflicts).append(f)
    if conflicts:
        return IdentityResult(IdentityStatus.REJECT, tuple(matched), tuple(conflicts), ("IDENTITY_HARD_CONFLICT", "IDENTITY_NOT_PROVEN"), 0.0)
    title_a, title_b = _norm(source.product_name), val("product_name")
    title_score = SequenceMatcher(None, title_a or "", title_b or "").ratio() if title_b else 0.0
    if not matched:
        return IdentityResult(IdentityStatus.MEDIUM if title_score >= .85 else IdentityStatus.LOW, (), (), ("TITLE_ONLY_MATCH",) if title_score else ("IDENTITY_EVIDENCE_MISSING",), min(title_score, .79))
    exact_id = any(f in matched for f in ("asin", "upc", "ean", "gtin", "manufacturer_part_number"))
    if exact_id and ("model" in matched or not getattr(source, "model", None)): return IdentityResult(IdentityStatus.VERIFIED, tuple(matched), (), ("EXACT_IDENTIFIER_MATCH",), .99)
    if "model" in matched and "brand" in matched: return IdentityResult(IdentityStatus.HIGH, tuple(matched), (), ("MODEL_BRAND_MATCH",), .95)
    return IdentityResult(IdentityStatus.MEDIUM, tuple(matched), (), ("PARTIAL_IDENTITY_MATCH",), .80)
