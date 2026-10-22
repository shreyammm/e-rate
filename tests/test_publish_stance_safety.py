"""Prevent unreliable sunset direction counts from being published as validated results."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.publish_research_findings import build


class SunsetStanceSafetyTest(unittest.TestCase):
    def test_sunset_polarity_hidden_and_other_rows_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            landscape = root / "landscape.json"
            machine = root / "machine.json"
            site = root / "findings.html"
            landscape.write_text(json.dumps({
                "coverage": {
                    "corpus_records": 3231,
                    "source_text_records": 3230,
                    "completed_machine_filings": 2778,
                    "machine_claim_rows": 12031,
                    "full_source_quote_offset_verified": 12031
                },
                "clusters": [],
                "role_filings_with_model_claims": {}
            }))
            machine.write_text(json.dumps({
                "generated_utc": "2026-10-22T06:06:28Z",
                "completed_filings": 2778,
                "machine_evidence_quality": {
                    "semantic_scope_full_text_filings": 2778
                },
                "provisions": [
                    {"provision_id": "erate_sunset", "label": "Limit or sunset E-Rate",
                     "positions": {"support": 999, "oppose": 8},
                     "filings_mentioning": 1200},
                    {"provision_id": "screen_time_condition",
                     "label": "Condition E-Rate on screen-time limits",
                     "positions": {"support": 7, "oppose": 2},
                     "filings_mentioning": 9}
                ]
            }))
            build(landscape, machine, site)
            html = site.read_text()
            self.assertIn("Withheld: stance direction under audit", html)
            self.assertIn("Stance-polarity audit required", html)
            self.assertNotIn('<td class="num">999</td>', html)
            self.assertIn(
                '<tr><td>Condition E-Rate on screen-time limits</td>'
                '<td class="num">7</td><td class="num">2</td>',
                html
            )


if __name__ == "__main__":
    unittest.main()
