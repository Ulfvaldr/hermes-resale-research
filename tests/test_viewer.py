import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hermes_resale_research.n8n_client import N8nResponse
from hermes_resale_research.viewer import load_report, render, run_research


class ViewerContractTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "title": "Today's Resale Opportunity Candidates",
            "generated_at": "2026-10-24T12:00:00Z",
            "items": [
                {"product_name": "First", "recommendation": "WATCH", "source_price": None,
                 "estimated_net_profit": "10.00", "source_provenance": {"url": "https://example.test/a"}},
                {"product_name": "Second", "recommendation": "RECHECK", "eligible": False},
            ],
            "rejected": [{"product_name": "Skipped", "recommendation": "SKIP", "reason_codes": ["OUT_OF_STOCK"]}],
            "research_only": True,
            "human_approval_required": True,
        }

    def test_render_preserves_order_and_missing_values(self):
        page = render(self.report)
        self.assertLess(page.index("First"), page.index("Second"))
        self.assertIn("Source price: <strong>Unavailable</strong>", page)
        self.assertIn("Skipped", page)
        self.assertIn("Evidence and provenance", page)
        self.assertIn("Run Today's Research", page)
        self.assertIn("/api/research", page)

    def test_render_formats_presentation_values_and_explains_reasons(self):
        self.report["items"][0].update({
            "source_price": "21",
            "expected_resale_price": "72.00",
            "estimated_net_profit": "40",
            "break_even_price": "30.5",
            "roi": "0.60",
            "reason_codes": ["ALL_REQUIRED_GATES_PASS"],
        })
        self.report["rejected"][0].update({"estimated_net_profit": "10", "roi": "1.40", "reason_codes": ["SOLD_COUNT_BELOW_MINIMUM"]})
        page = render(self.report)
        for value in ("$21.00", "$72.00", "$40.00", "$30.50", "60%", "140%"):
            self.assertIn(value, page)
        self.assertIn("All required checks passed", page)
        self.assertIn("There are not enough sold examples", page)
        self.assertIn("ALL_REQUIRED_GATES_PASS", page)
        self.assertIn('class="audit-record"', page)
        self.assertNotIn('<details class="audit-record" open', page)
    def test_load_rejects_unsafe_report(self):
        unsafe = dict(self.report, research_only=False)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(unsafe), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_report(path)

    def test_load_accepts_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(self.report), encoding="utf-8")
            self.assertEqual(load_report(path)["items"][0]["product_name"], "First")

    @patch("hermes_resale_research.viewer.demo_report")
    def test_run_research_demo_delegates_to_phase_two(self, demo):
        demo.return_value = self.report
        self.assertIs(run_research(demo=True), self.report)
        demo.assert_called_once_with()

    def test_run_research_non_demo_requires_explicit_payload(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "N8N_RESEARCH_PAYLOAD"):
                run_research(demo=False)

    @patch("hermes_resale_research.viewer.post_evaluation")
    def test_run_research_non_demo_validates_n8n_report(self, post):
        post.return_value = N8nResponse(True, 200, data=self.report)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payload.json"
            path.write_text('{"candidates": []}', encoding="utf-8")
            result = run_research(demo=False, payload_path=path)
        self.assertFalse(result["demo_mode"])
        post.assert_called_once_with({"candidates": []})


if __name__ == "__main__":
    unittest.main()
