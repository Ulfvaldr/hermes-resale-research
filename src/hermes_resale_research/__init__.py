"""Deterministic, offline resale-research core."""
from .models import SourceCandidate, ResaleEvidence, IdentityResult, FreshnessResult, EconomicsResult, ScoreResult, Decision, OpportunityAssessment, IdentityStatus, FreshnessState, Recommendation
from .identity import compare_identity
from .freshness import classify_freshness
from .economics import evaluate_economics
from .scoring import score_opportunity
from .recommendations import recommend
from .workflow import evaluate_opportunity, evaluate_opportunity_from_adapter
from .evidence import normalize_resale_evidence, validate_resale_evidence
from .adapter import EbayEvidenceAdapter, UnavailableEbayAdapter, FakeEbayEvidenceAdapter, LiveEbayBrowseAdapter
from .n8n_client import N8nResponse, post_evaluation
from .batch import discover_candidates, enrich_candidates, evaluate_batch, render_markdown

__all__ = ["SourceCandidate", "ResaleEvidence", "IdentityResult", "FreshnessResult", "EconomicsResult", "ScoreResult", "Decision", "OpportunityAssessment", "IdentityStatus", "FreshnessState", "Recommendation", "compare_identity", "classify_freshness", "evaluate_economics", "score_opportunity", "recommend", "evaluate_opportunity", "evaluate_opportunity_from_adapter", "normalize_resale_evidence", "validate_resale_evidence", "EbayEvidenceAdapter", "UnavailableEbayAdapter", "FakeEbayEvidenceAdapter", "LiveEbayBrowseAdapter", "N8nResponse", "post_evaluation", "discover_candidates", "enrich_candidates", "evaluate_batch", "render_markdown"]
