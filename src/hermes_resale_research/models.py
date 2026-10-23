from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping

class IdentityStatus(str, Enum): VERIFIED="VERIFIED"; HIGH="HIGH"; MEDIUM="MEDIUM"; LOW="LOW"; REJECT="REJECT"
class FreshnessState(str, Enum): LIVE="LIVE"; FRESH="FRESH"; AGING="AGING"; STALE="STALE"; UNKNOWN="UNKNOWN"; MISSING="MISSING"; CONFLICTING="CONFLICTING"; UNVERIFIED="UNVERIFIED"; BLOCKED="BLOCKED"
class Recommendation(str, Enum): BUY_CANDIDATE="BUY_CANDIDATE"; WATCH="WATCH"; RECHECK="RECHECK"; SKIP="SKIP"

@dataclass(frozen=True)
class SourceCandidate:
    source_marketplace: str; source_url: str; product_name: str
    brand: str | None = None; model: str | None = None; asin: str | None = None
    upc: str | None = None; ean: str | None = None; gtin: str | None = None
    manufacturer_part_number: str | None = None
    variation_attributes: Mapping[str, Any] = field(default_factory=dict)
    condition: str | None = None; source_price: Decimal | float | int | None = None
    stock_status: str | None = None; source_observed_at: datetime | str | None = None
    source_notes: str | None = None; provenance: Mapping[str, Any] = field(default_factory=dict)
    confidence: float | None = None

@dataclass(frozen=True)
class ResaleEvidence:
    resale_marketplace: str = "eBay"; product_name: str | None = None
    brand: str | None = None; model: str | None = None; asin: str | None = None
    upc: str | None = None; ean: str | None = None; gtin: str | None = None
    manufacturer_part_number: str | None = None
    variation_attributes: Mapping[str, Any] = field(default_factory=dict)
    condition: str | None = None; recent_sold_median: Decimal | float | int | None = None
    sold_count: int | None = None; sold_window_days: int | None = None
    active_listing_count: int | None = None; seller_count: int | None = None
    evidence_observed_at: datetime | str | None = None
    evidence_type: str = "UNAVAILABLE"; provenance: Mapping[str, Any] = field(default_factory=dict)
    confidence: float | None = None; volatility: str | None = None; stock_status: str | None = None
    fees_observed_at: datetime | str | None = None; shipping_observed_at: datetime | str | None = None
    # Active-listing fields are intentionally separate from sold economics.
    asking_price: Decimal | float | int | None = None; asking_currency: str | None = None
    estimated_sold_quantity: int | None = None

@dataclass(frozen=True)
class IdentityResult:
    status: IdentityStatus; matched_fields: tuple[str, ...] = (); conflicting_fields: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = (); confidence: float = 0.0

@dataclass(frozen=True)
class FieldFreshness:
    field: str; state: FreshnessState; observed_at: datetime | None = None; age_seconds: int | None = None
    reason_codes: tuple[str, ...] = (); buy_gate_pass: bool = False

@dataclass(frozen=True)
class FreshnessResult:
    fields: Mapping[str, FieldFreshness]; overall_status: FreshnessState
    reason_codes: tuple[str, ...] = (); provenance: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class EconomicsResult:
    acquisition_cost: Decimal | None; tax: Decimal | None; inbound_shipping: Decimal | None
    outbound_shipping: Decimal | None; marketplace_fees: Decimal | None; payment_fees: Decimal | None
    packaging: Decimal | None; return_allowance: Decimal | None; expected_resale_price: Decimal | None
    break_even_resale_price: Decimal | None; expected_net_profit: Decimal | None; roi: Decimal | None
    margin: Decimal | None; capital_at_risk: Decimal | None; calculation_status: str
    missing_fields: tuple[str, ...] = ()

@dataclass(frozen=True)
class ScoreResult:
    score: Decimal; components: Mapping[str, Decimal]; risk_flags: tuple[str, ...] = (); explanation: tuple[str, ...] = ()

@dataclass(frozen=True)
class Decision:
    recommendation: Recommendation; score: Decimal; reason_codes: tuple[str, ...]
    failed_gates: tuple[str, ...] = (); confidence: int = 0
    human_recheck_required: tuple[str, ...] = ()

@dataclass(frozen=True)
class OpportunityAssessment:
    identity: IdentityResult; freshness: FreshnessResult; economics: EconomicsResult
    score: ScoreResult; decision: Decision; market: ResaleEvidence
    evaluated_at: datetime; source_provenance: Mapping[str, Any] = field(default_factory=dict)
    resale_provenance: Mapping[str, Any] = field(default_factory=dict)
