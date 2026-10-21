"""Regression checks for the standalone non-LLM Patterns Lab."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


class PatternsPageTests(unittest.TestCase):
    def test_index_and_asset_wired(self):
        home = (SITE / "index.html").read_text(encoding="utf-8")
        page = (SITE / "patterns.html").read_text(encoding="utf-8")
        script = (SITE / "assets" / "patterns.js").read_text(encoding="utf-8")
        self.assertIn('href="./patterns.html"', home)
        self.assertIn('src="./assets/patterns.js"', page)
        self.assertIn('./data/corpus_index.json', script)
        self.assertIn('escape(r.organization', script)
        self.assertIn('noopener noreferrer', script)

    def test_every_required_control_exists(self):
        page = (SITE / "patterns.html").read_text(encoding="utf-8")
        for element in ("lab-role", "lab-issue", "lab-type", "lab-weight",
                        "lab-ocr", "lab-timeline", "lab-roles", "lab-pairs",
                        "lab-sensitivity", "lab-table", "lab-download"):
            self.assertRegex(page, r'id="' + element + r'"')

    def test_published_index_is_valid_for_bitmask_analysis(self):
        data = json.loads((SITE / "data" / "corpus_index.json").read_text(encoding="utf-8"))
        self.assertGreater(len(data["filings"]), 0)
        self.assertGreater(len(data["issue_keys"]), 1)
        self.assertLessEqual(len(data["issue_keys"]), 30)
        ids = [str(r["id"]) for r in data["filings"]]
        self.assertEqual(len(ids), len(set(ids)))
        for row in data["filings"]:
            self.assertGreaterEqual(int(row["issues"]), 0)
            self.assertLess(int(row["issues"]), 1 << len(data["issue_keys"]))
            self.assertGreaterEqual(int(row.get("duplicate_count", 0)), 0)
            # A zero denotes unavailable exact-text family data (for example, no text).
            # UI weighting explicitly treats this as a singleton instead of division by zero.


if __name__ == "__main__":
    unittest.main()
