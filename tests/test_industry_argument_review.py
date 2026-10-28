"""Accuracy and reproducibility tests for the industry argument audit queue."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_industry_argument_review import (
    COMPARATORS, INDUSTRY, TOPICS, FIELDS, build, make_queue,
    safe_csv_value, verify_census,
)

ROOT = Path(__file__).resolve().parents[1]


class IndustryArgumentReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input_path = ROOT / "docs/data/stakeholder_argument_census.json"
        cls.data = json.loads(cls.input_path.read_text(encoding="utf-8"))

    def test_source_reconciliation_rejects_incorrect_frequencies(self):
        verify_census(self.data)
        damaged = dict(self.data)
        damaged["topics"] = [dict(x) for x in self.data["topics"]]
        damaged["topics"][0]["filings"] += 1
        with self.assertRaisesRegex(ValueError, "overall argument denominator"):
            verify_census(damaged)

    def test_complete_industry_joint_review_and_negative_controls(self):
        rows, summary = make_queue(self.data, per_comparator_stratum=2)
        self.assertEqual(summary["status"], "UNREVIEWED_SOURCE_CHECK_ASSIGNMENTS")
        self.assertEqual(summary["source_filings"], 3231)
        self.assertEqual(len(rows), summary["assignments"])
        self.assertEqual(len(rows), len({(r["filing_id"], r["topic_id"]) for r in rows}))
        all_industry = [f for f in self.data["filings"]
                        if f["group"] in INDUSTRY or f.get("joint_filing")]
        expected = {(f["id"], t) for f in all_industry for t in TOPICS}
        actual = {(r["filing_id"], r["topic_id"]) for r in rows
                  if r["review_assignment"] != "comparator_quality_control"}
        self.assertEqual(actual, expected)
        self.assertEqual(summary["known_industry_and_joint_filings_in_census"],
                         len(all_industry))
        self.assertEqual(summary["industry_filings"],
                         sum(f["group"] in INDUSTRY for f in all_industry))
        self.assertEqual(summary["joint_filings_screened"],
                         sum(bool(f.get("joint_filing")) for f in all_industry))
        controls = [r for r in rows if r["review_assignment"] == "comparator_quality_control"]
        self.assertTrue(controls)
        self.assertTrue(all(r["stakeholder_candidate"] in COMPARATORS for r in controls))
        self.assertTrue(any(r["model_candidate_status"] == "not_detected_by_model"
                            for r in controls))
        self.assertTrue(any(r["model_candidate_status"] == "argument_extracted"
                            for r in controls))
        self.assertTrue(all(not r["redacted_source_quote"]
                            for r in rows if r["model_candidate_status"] == "not_detected_by_model"))
        self.assertTrue(all(r["source_url"].endswith(r["filing_id"]) for r in rows))
        self.assertTrue(all(not r["reviewer_id"] and not r["filer_endorses_argument"]
                            for r in rows))

    def test_same_source_same_queue_and_export_has_no_auto_answer(self):
        first, a = make_queue(self.data, per_comparator_stratum=2)
        second, b = make_queue(self.data, per_comparator_stratum=2)
        self.assertEqual(first, second)
        self.assertEqual(a, b)
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "audit.csv"
            summary_path = Path(tmp) / "audit.json"
            result = build(self.input_path, csv_path, summary_path, 2)
            self.assertEqual(result["assignments"], len(first))
            with csv_path.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(tuple(reader.fieldnames), FIELDS)
                loaded = list(reader)
            self.assertEqual(len(loaded), len(first))
            self.assertTrue(all(row["reviewer_id"] == "" for row in loaded))
            self.assertEqual(json.loads(summary_path.read_text())["input_census_sha256"].__len__(), 64)

    def test_csv_cells_cannot_execute_spreadsheet_formulas(self):
        for prefix in ("=", "+", "-", "@"):
            self.assertEqual(safe_csv_value("  " + prefix + "HYPERLINK()"),
                             "'  " + prefix + "HYPERLINK()")
        self.assertEqual(safe_csv_value("ordinary quote"), "ordinary quote")


if __name__ == "__main__":
    unittest.main()
