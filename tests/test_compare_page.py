"""Comparative workbench publication checks."""
import json
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"docs"

class ComparisonPublicationTests(unittest.TestCase):
    def test_links_scripts_and_comparison_controls(self):
        page=(P/"compare.html").read_text()
        script=(P/"assets"/"compare.js").read_text()
        home=(P/"index.html").read_text()
        self.assertIn('href="./research.html"',home)
        self.assertIn('href="./compare.html"',(P/"research.html").read_text())
        self.assertIn('src="./assets/compare.js"',page)
        for id in ("compare-metric","compare-weight","compare-type","compare-ocr","compare-head","compare-body","compare-records","compare-export"):
            self.assertIn('id="'+id+'"',page)
        self.assertIn('corpus_index.json',script)
        self.assertIn('otherNum',script)
        self.assertIn('noopener noreferrer',script)

    def test_counts_are_reconciled_to_published_rows(self):
        data=json.loads((P/"data"/"corpus_index.json").read_text())
        rows=data["filings"]
        self.assertEqual(len(rows),3231)
        for r in rows:
            self.assertIn("role",r)
            self.assertIn("issues",r)
            self.assertIn("id",r)

if __name__=="__main__":unittest.main()
