"""Static integration and research-integrity tests for corpus-only workbenches."""
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/"docs"

class Elements(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set();self.js=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get("id"):self.ids.add(a["id"])
        if tag=="script" and a.get("src"):self.js.append(a["src"])

class ResearchToolsTests(unittest.TestCase):
    def test_all_analysis_pages_have_local_scripts_and_controls(self):
        expected={
          "patterns.html": {"lab-weight","lab-role","lab-issue","lab-timeline","lab-pairs","lab-download"},
          "compare.html": {"compare-weight","compare-metric","compare-body","compare-records","compare-export"},
          "phrase.html": {"ph-a","ph-b","ph-mode","ph-run","ph-results","ph-export","ph-scanned"},
          "similar.html": {"sim-id","sim-run","sim-export","sim-results","sim-status"},
          "research.html": {"studio-search","studio-query","studio-status","studio-filings"},
          "ask.html": {"ask-use-ai","ask-share-question","ev-role","ev-ocr","ev-order","ev-results","ev-export"}
        }
        for page,ids in expected.items():
            parser=Elements();parser.feed((DOCS/page).read_text(encoding="utf-8"))
            self.assertTrue(ids<=parser.ids,(page,ids-parser.ids))
            for js in parser.js:
                self.assertTrue((DOCS/js).is_file(),(page,js))
    def test_question_workbench_guards_source_counts_and_result_status(self):
        code=(DOCS/"assets"/"phrase_lab.js").read_text(encoding="utf-8")
        for token in ("meta.records", "manifest.with_text", "ids.size",
                      "size!==expected", "No partial findings were published",
                      "DecompressionStream", "encodeURIComponent", "textContent"):
            self.assertIn(token,code)
    def test_ask_has_explicit_evidence_only_and_full_hit_event(self):
        code=(DOCS/"assets"/"ask.js").read_text(encoding="utf-8")
        self.assertIn("'erate:scan-complete'",code)
        self.assertIn("'ask-use-ai'",code)
        self.assertIn("citation",code)
        sidecar=(DOCS/"assets"/"ask_evidence.js").read_text(encoding="utf-8")
        self.assertIn("full.candidates",sidecar)
        self.assertIn("fcc_ask_corpus_evidence.csv",sidecar)
        self.assertIn("corpus_index.json",sidecar)
    def test_similarity_uses_document_coverage_and_source_metadata(self):
        code=(DOCS/"assets"/"similar.js").read_text(encoding="utf-8")
        for part in ("manifest.records", "m.with_text",
                     "qa_index", "idf", "dots", "norms", "docs[i]",
                     "fcc_similar_filings.csv"):
            self.assertIn(part,code)

    def test_index_links_all_plain_corpus_workbenches(self):
        home=(DOCS/"index.html").read_text(encoding="utf-8")
        for page in ("patterns.html","compare.html","phrase.html","similar.html","research.html","ask.html"):
            self.assertIn(page,home)

if __name__=="__main__":unittest.main()
