"""Local, read-only presentation layer for Phase 2 batch reports."""
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DEMO_INPUT = ROOT / "examples" / "phase2-demo-candidates.json"


def load_report(path: Path) -> dict:
    """Load and validate only the viewer safety/envelope contract."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read report: {exc}") from exc
    if not isinstance(report, dict):
        raise ValueError("Report must be a JSON object")
    for field in ("items", "rejected"):
        if not isinstance(report.get(field), list):
            raise ValueError(f"Report field {field!r} must be an array")
    if report.get("research_only") is not True or report.get("human_approval_required") is not True:
        raise ValueError("Report safety contract requires research_only=true and human_approval_required=true")
    return report


def demo_report() -> dict:
    """Run the existing Phase 2 CLI against its credential-free fixture."""
    command = [sys.executable, "-m", "hermes_resale_research", str(DEMO_INPUT), "--batch", "--limit", "10"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ValueError(f"Demo report generation failed: {result.stderr.strip()}")
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Demo command returned malformed JSON") from exc
    report["demo_mode"] = True
    return report


def _value(item: dict, key: str) -> str:
    value = item.get(key)
    if value is None or value == "":
        return "Unavailable"
    return html.escape(str(value))


def _list(value: object) -> str:
    if not value:
        return "None"
    if isinstance(value, list):
        return html.escape(", ".join(str(v) for v in value))
    return html.escape(str(value))


def _details(item: dict) -> str:
    provenance = {key: item.get(key) for key in ("source_provenance", "resale_provenance") if key in item}
    audit = {key: item.get(key) for key in ("candidate_id", "failed_gates", "reason_codes", "eligible", "human_approval_required") if key in item}
    payload = html.escape(json.dumps({"provenance": provenance, "audit": audit}, indent=2, ensure_ascii=False))
    return f"<details><summary>Evidence and provenance</summary><pre>{payload}</pre></details>"


def _card(item: dict, rank: int) -> str:
    rec = _value(item, "recommendation")
    return f"""<article class="card">
      <div class="rank">#{rank}</div><div class="card-main">
      <div class="heading"><h2>{_value(item, 'product_name')}</h2><span class="badge">{rec}</span></div>
      <p class="source">{_value(item, 'source_store')} · Source price: <strong>{_value(item, 'source_price')}</strong></p>
      <div class="metrics"><div><small>Estimated net profit</small><strong>{_value(item, 'estimated_net_profit')}</strong></div>
      <div><small>ROI</small><strong>{_value(item, 'roi')}</strong></div><div><small>Confidence</small><strong>{_value(item, 'confidence')}</strong></div>
      <div><small>Evidence quality</small><strong>{_value(item, 'evidence_quality')}</strong></div></div>
      <dl><dt>Expected resale price</dt><dd>{_value(item, 'expected_resale_price')}</dd><dt>Break-even price</dt><dd>{_value(item, 'break_even_price')}</dd>
      <dt>Explanation</dt><dd>{_value(item, 'explanation')}</dd></dl>{_details(item)}</div></article>"""


def render(report: dict) -> str:
    cards = "".join(_card(item, rank) for rank, item in enumerate(report["items"], 1))
    rejected = "".join(_card(item, rank) for rank, item in enumerate(report["rejected"], 1)) or "<p>No rejected or skipped candidates.</p>"
    mode = "CREDENTIAL-FREE SYNTHETIC DEMO" if report.get("demo_mode") else "LOCAL REPORT"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(str(report.get('title', "Today's Resale Opportunity Candidates")))}</title><style>
:root{{font-family:system-ui,sans-serif;color:#172033;background:#f4f6fa}}body{{margin:0}}header{{background:#172033;color:white;padding:2rem max(1rem,calc((100% - 1100px)/2))}}main{{max-width:1100px;margin:2rem auto;padding:0 1rem}}h1{{margin:.2rem 0}}.notice{{background:#fff4d6;color:#684b00;padding:1rem;border-left:4px solid #e0a400;margin:1rem 0}}.meta{{opacity:.8}}.card{{display:flex;gap:1rem;background:white;border-radius:10px;margin:1rem 0;padding:1rem;box-shadow:0 2px 8px #17203318}}.rank{{font-size:1.5rem;font-weight:700;color:#556}}.card-main{{flex:1}}.heading{{display:flex;justify-content:space-between;gap:1rem;align-items:center}}h2{{margin:0}}.badge{{background:#e5efff;padding:.35rem .6rem;border-radius:999px;font-weight:700;font-size:.8rem}}.source{{color:#556}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem}}.metrics div{{background:#eef3fb;padding:.8rem;border-radius:7px}}small{{display:block;color:#556}}.metrics strong{{font-size:1.25rem;display:block;margin-top:.25rem}}dl{{display:grid;grid-template-columns:180px 1fr;gap:.35rem 1rem}}dt{{font-weight:700}}dd{{margin:0}}details{{margin-top:1rem}}pre{{white-space:pre-wrap;background:#f4f6fa;padding:1rem;overflow:auto}}section{{margin-top:2rem}}@media(max-width:650px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.heading{{display:block}}dl{{grid-template-columns:1fr}}}}
</style></head><body><header><div class="meta">{mode}</div><h1>{html.escape(str(report.get('title', "Today's Resale Opportunity Candidates")))}</h1><div class="meta">Generated {html.escape(str(report.get('generated_at', 'Unavailable')))} · {len(report['items'])} ranked · {len(report['rejected'])} rejected</div></header><main>
<div class="notice"><strong>Research-only, read-only view.</strong> Human approval is required. Values and recommendations are rendered from Phase 2 output; nothing is recalculated or acted upon.</div>
<section><h2>Top opportunities</h2>{cards or '<p>No evidence-backed candidates passed the presentation filter.</p>'}</section><section><h2>Rejected / skipped audit records</h2>{rejected}</section></main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the read-only Phase 2 candidates viewer")
    parser.add_argument("--report", type=Path, help="local Phase 2 JSON report")
    parser.add_argument("--demo", action="store_true", help="run the credential-free synthetic demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if bool(args.report) == args.demo:
        parser.error("choose exactly one of --report or --demo")
    try:
        report = demo_report() if args.demo else load_report(args.report)
    except ValueError as exc:
        parser.error(str(exc))
    page = render(report).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if urlparse(self.path).path != "/":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Viewer listening at http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
