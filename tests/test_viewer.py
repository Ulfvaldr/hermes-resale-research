import json
import tempfile
import unittest
from pathlib import Path

from hermes_resale_research.viewer import load_report, render


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


if __name__ == "__main__":
    unittest.main()
