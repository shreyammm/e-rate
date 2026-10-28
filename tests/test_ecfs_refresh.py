"""Regression safeguards for adding new FCC metadata without corrupting the frozen corpus."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from scripts.audit_ecfs_refresh import (
    compare, filing_id, normalized_export, parse_input, build,
)

class EcfsRefreshTest(unittest.TestCase):
    @staticmethod
    def snapshot():
        filings=[{"id":str(26110070000+i),"date":"2026-10-13","type":"COMMENT"} for i in range(3231)]
        return {"snapshot":"ocr_candidate_v1","filings":filings}

    def test_new_vs_existing_and_no_false_missing_on_partial_export(self):
        source=self.snapshot()
        known=source["filings"][0]["id"]
        incoming=[{"submission_id":known,"date":"2026-10-13","type":"COMMENT"},
                  {"filing_id":"26110099999","date":"2026-11-06","type":"REPLY"}]
        x=compare(source,incoming,False)
        self.assertEqual(x["new_filing_candidates"],1)
        self.assertEqual(x["new_filings"][0]["id"],"26110099999")
        self.assertIsNone(x["original_ids_absent_from_export"])
        self.assertTrue(x["source_not_imported"])
        self.assertEqual(x["status"],"UNVERIFIED_METADATA_DIFF_ONLY")
        y=compare(source,incoming,True)
        self.assertEqual(y["original_ids_absent_from_export"],3230)

    def test_existing_modified_record_is_review_candidate(self):
        source=self.snapshot()
        known=source["filings"][0]["id"]
        report=compare(source,[{"id":known,"date":"2026-10-13",
                               "last_modified":"2026-11-01T09:00:00Z",
                               "type":"COMMENT"}])
        self.assertEqual(report["metadata_changes_to_recheck"],1)
        self.assertIn("post_snapshot_modified",
                      report["changed_existing_metadata"][0]["changes"])

    def test_conflicting_duplicate_and_unsafe_source_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate export row"):
            normalized_export([{"id":"26110099999"},{"filing_id":"26110099999"}])
        with self.assertRaisesRegex(ValueError,"conflicting ECFS filing IDs"):
            normalized_export([{"id":"26110099999","submission_id":"26110099998"}])
        with self.assertRaisesRegex(ValueError,"official HTTPS FCC"):
            normalized_export([{"id":"26110099999","source_url":"https://other.com/filing/26110099999"}])
        with self.assertRaisesRegex(ValueError,"conflicts"):
            normalized_export([{"id":"26110099999","source_url":"https://www.fcc.gov/ecfs/filing/26110099998"}])

    def test_missing_id_invalid_date_and_bad_objects_rejected(self):
        with self.assertRaisesRegex(ValueError,"Missing or conflicting"):
            filing_id({})
        with self.assertRaisesRegex(ValueError,"Unparseable submission date"):
            normalized_export([{"id":"26110099999","date":"2026-99-99"}])
        with self.assertRaisesRegex(ValueError,"Each export row"):
            normalized_export(["not an ECFS record"])

    def test_csv_and_json_inputs_and_local_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            input_path=p/"incoming.csv"
            with input_path.open("w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["filing_id","date","type"])
                w.writeheader();w.writerow({"filing_id":"26110099999","date":"2026-11-01","type":"REPLY"})
            self.assertEqual(len(parse_input(input_path)),1)
            snapshot=p/"snapshot.json"
            snapshot.write_text(json.dumps(self.snapshot()))
            result=build(input_path,snapshot,p/"output")
            self.assertEqual(result["new_filing_candidates"],1)
            self.assertEqual(json.loads((p/"output/ecfs_metadata_delta.json").read_text())["source_not_imported"],True)
            json_path=p/"incoming.json"
            json_path.write_text(json.dumps({"filings":[{"id":"26110099999"}]}))
            self.assertEqual(len(parse_input(json_path)),1)


if __name__=="__main__":
    unittest.main()
