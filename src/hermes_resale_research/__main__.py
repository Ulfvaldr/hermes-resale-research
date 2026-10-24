"""Thin offline invocation: python -m hermes_resale_research input.json"""
from __future__ import annotations
import argparse, json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from .workflow import evaluate_opportunity
from .n8n_client import post_evaluation

def _json(value):
    if isinstance(value, Enum): return value.value
    if isinstance(value, Decimal): return str(value)
    if isinstance(value, datetime): return value.isoformat().replace("+00:00", "Z")
    if is_dataclass(value): return {k: _json(v) for k, v in asdict(value).items()}
    if isinstance(value, dict): return {k: _json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [_json(v) for v in value]
    return value

def main():
    parser = argparse.ArgumentParser(description="Evaluate a manual source candidate against eBay resale evidence")
    parser.add_argument("input", type=Path, help="JSON with source_candidate, resale_evidence, assumptions, optional now")
    parser.add_argument("--n8n", action="store_true", help="POST the input JSON contract to the configured local n8n webhook")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if args.n8n:
        print(json.dumps(post_evaluation(payload).as_dict(), separators=(",", ":"), sort_keys=True))
        return
    now = datetime.fromisoformat(payload["now"].replace("Z", "+00:00")) if payload.get("now") else None
    assessment = evaluate_opportunity(payload["source_candidate"], payload["resale_evidence"], payload.get("assumptions", {}), now)
    print(json.dumps(_json(assessment), indent=2, sort_keys=True))

if __name__ == "__main__": main()
