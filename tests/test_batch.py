import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_resale_research import evaluate_batch, render_markdown


class BatchTests(unittest.TestCase):
    demo = json.loads((ROOT / "examples" / "phase2-demo-candidates.json").read_text(encoding="utf-8"))
    now = datetime.fromisoformat(demo["demo_now"].replace("Z", "+00:00"))

    def test_bounded_deterministic_batch_and_rejected_audit(self):
        report = evaluate_batch(self.demo["candidates"], now=self.now, limit=5)
        self.assertEqual(report["candidate_count"], 5)
        self.assertEqual(report["evaluated_count"], 5)
        self.assertEqual([item["candidate_id"] for item in report["items"]], ["demo-01-valid-buy", "demo-02-stale-source-price", "demo-03-stale-stock"])
        self.assertEqual([item["candidate_id"] for item in report["rejected"]], ["demo-05-identity-mismatch", "demo-04-missing-sold-evidence"])
        self.assertTrue(all(item["human_approval_required"] for item in report["items"] + report["rejected"]))

    def test_missing_required_input_is_rejected_not_raised(self):
        report = evaluate_batch([{"candidate_id": "bad", "source_candidate": {"product_name": "bad"}}], now=self.now)
        self.assertEqual(report["items"], [])
        self.assertEqual(report["rejected"][0]["recommendation"], "SKIP")
        self.assertIn("INVALID_CANDIDATE", report["rejected"][0]["reason_codes"])

    def test_markdown_contains_required_output_fields(self):
        report = evaluate_batch(self.demo["candidates"][:1], now=self.now)
        output = render_markdown(report)
        for text in ("Today's Resale Opportunity Candidates", "Source:", "resale:", "net:", "ROI:", "break-even:", "Confidence:", "Evidence:"):
            self.assertIn(text, output)


if __name__ == "__main__":
    unittest.main()
