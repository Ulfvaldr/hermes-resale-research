from decimal import Decimal
from .models import ScoreResult, IdentityResult, FreshnessResult, EconomicsResult
from .freshness import SEVERITY
def score_opportunity(identity: IdentityResult, freshness: FreshnessResult, economics: EconomicsResult, market=None) -> ScoreResult:
    comps={"identity":Decimal(str(identity.confidence*40)),"freshness":Decimal(str(max(0,40-SEVERITY.get(freshness.overall_status,8)*8))),"economics":Decimal("0")}
    if economics.calculation_status=="COMPLETE": comps["economics"] = Decimal("20") if (economics.expected_net_profit or 0)>=0 else Decimal("0")
    risks=[]
    if identity.status.value in ("LOW","REJECT"): risks.append("IDENTITY_NOT_PROVEN")
    if market is not None and getattr(market,"volatility",None)=="HIGH": risks.append("VOLATILITY_HIGH")
    return ScoreResult(sum(comps.values()).quantize(Decimal("0.01")), comps, tuple(risks), tuple(risks))
