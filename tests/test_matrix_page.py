"""Source and UI safeguards for the stakeholder comparison research view."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs/matrix.html"
JS = ROOT / "docs/assets/matrix.js"
CSS = ROOT / "docs/assets/matrix.css"
CENSUS = ROOT / "docs/data/stakeholder_argument_census.json"

class MatrixResearchPageTests(unittest.TestCase):
    def test_source_and_component_wiring(self):
        html = PAGE.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
        self.assertTrue(CSS.exists())
        ids = re.findall(r'\bid="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)), "HTML element IDs must be unique")
        required = [
            "load-status", "matrix-head", "matrix-body", "matrix-export", "industry-audit-export", "industry-audit-status",
            "group-scope", "issue-filter", "measure", "topic-search",
            "detail-metrics", "detail-evidence", "detail-deep-link",
            "comparison-group", "evidence-query", "prefer-clear",
            "frame-focus", "frame-compare", "frame-list",
        ]
        for item in required:
            self.assertIn(item, ids)
            self.assertIn("'"+item+"'", js)
        self.assertIn("./data/stakeholder_argument_census.json", js)
        self.assertIn("./assets/matrix.js",html)
        self.assertIn("./matrix.html",(ROOT/"docs/index.html").read_text(encoding="utf-8"))
        self.assertIn("./matrix.html",(ROOT/"docs/stakeholders.html").read_text(encoding="utf-8"))

    def test_census_denominators_and_stakeholder_exclusivity(self):
        d = json.loads(CENSUS.read_text(encoding="utf-8"))
        self.assertEqual(d["schema"],"stakeholder-arguments-v1")
        self.assertEqual(d["coverage"]["filings"], 3231)
        self.assertEqual(len(d["filings"]), 3231)
        groups = {g["id"]:g for g in d["stakeholder_groups"]}
        self.assertEqual(sum(g["filings"] for g in groups.values()), 3231)
        self.assertEqual(len({r["id"] for r in d["filings"]}), 3231)
        for topic in d["topics"]:
            with self.subTest(topic=topic["id"]):
                self.assertEqual(
                    sum(x["filings"] for x in topic["by_stakeholder"].values()),
                    topic["filings"]
                )
                self.assertLessEqual(topic["distinct_source_texts"],topic["filings"])
                for group,c in topic["by_stakeholder"].items():
                    self.assertLessEqual(c["filings"],groups[group]["filings"])
                    self.assertLessEqual(c["distinct_source_texts"],c["filings"])
        self.assertEqual(
            sum(r["group"] == "joint_institutional_filings" for r in d["filings"]),
            groups["joint_institutional_filings"]["filings"]
        )

    def test_position_caution_and_evidence_first(self):
        html = PAGE.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
        self.assertIn("not verified agreement",html)
        self.assertIn("position", html.lower())
        self.assertIn("support or opposition",html)
        self.assertIn("https://www.fcc.gov/ecfs/filing/",js)
        self.assertIn("text_sha256",js)
        self.assertIn("needs_speaker_review",js)
        self.assertIn("c.filings/t.filings",js)
        self.assertIn("c.filings/g.filings",js)
        self.assertNotIn("r.position",js)
        self.assertIn("alleged_misuse",js)
        self.assertIn("consultant_fees",js)
        self.assertIn("screen_use_distinctions",js)
        self.assertIn("isEdtechCofiling",js)
        self.assertIn("review_argument_endorsed",js)
        self.assertIn("review_verified_position",js)

if __name__ == "__main__":
    unittest.main()
