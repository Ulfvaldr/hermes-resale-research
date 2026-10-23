from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping, Any
from .models import EconomicsResult
Q=Decimal("0.01")
def money(x): return Decimal(str(x)).quantize(Q, rounding=ROUND_HALF_UP)
def evaluate_economics(inputs: Mapping[str, Any], resale_price=None) -> EconomicsResult:
    names=("acquisition_cost","tax","inbound_shipping","outbound_shipping","marketplace_fees","payment_fees","packaging","return_allowance")
    vals={n: (None if inputs.get(n) is None else money(inputs[n])) for n in names}
    price=inputs.get("expected_resale_price", resale_price); price=None if price is None else money(price)
    missing=tuple(n for n,v in vals.items() if v is None) + (() if price is not None else ("expected_resale_price",))
    if missing:
        return EconomicsResult(
            **{n: vals[n] for n in names}, expected_resale_price=price,
            break_even_resale_price=None, expected_net_profit=None, roi=None,
            margin=None, capital_at_risk=None, calculation_status="INCOMPLETE",
            missing_fields=missing)
    capital=money(vals["acquisition_cost"]+vals["tax"]+vals["inbound_shipping"]+vals["packaging"]+vals["return_allowance"])
    breakeven=money(capital+vals["outbound_shipping"]+vals["marketplace_fees"]+vals["payment_fees"])
    net=money(price-breakeven); roi=money(net/capital) if capital else None; margin=money(net/price) if price else None
    return EconomicsResult(
        **{n: vals[n] for n in names}, expected_resale_price=price,
        break_even_resale_price=breakeven, expected_net_profit=net, roi=roi,
        margin=margin, capital_at_risk=capital, calculation_status="COMPLETE")
