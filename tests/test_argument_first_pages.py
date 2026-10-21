"""Regression checks for the argument-first redesign and distinct evidence standards."""
import json
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/"docs"

class Parse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.scripts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get("id"):self.ids.add(a["id"])
        if tag=="script" and a.get("src"):self.scripts.append(a["src"])

class ArgumentFirstTests(unittest.TestCase):
    def test_primary_atlas_and_secondary_crosswalk_are_operable_pages(self):
        for page,required in [
          ("atlas.html",{"at-clusters-list","at-selected-evidence","at-roles","at-reason-bars","at-tensions","at-map","at-status"}),
          ("regulatory.html",{"reg-list","reg-q","reg-status","reg-category","reg-checks"}),
        ]:
            parser=Parse()
            parser.feed((DOCS/page).read_text(encoding="utf-8"))
            self.assertTrue(required<=parser.ids,(page,required-parser.ids))
            for asset in parser.scripts:
                self.assertTrue((DOCS/asset).exists(),asset)
        for path in ("index.html","research.html"):
            src=(DOCS/path).read_text(encoding="utf-8")
            self.assertIn('./atlas.html',src)
            self.assertIn('./regulatory.html',src)
        home=(DOCS/"index.html").read_text(encoding="utf-8")
        self.assertIn('FCC regulatory crosswalk (secondary)',home)
        self.assertIn('id="census-proposals"',home) # No loss of original dashboard data.

    def test_four_evidence_types_have_a_schema(self):
        d=json.loads((ROOT/"analysis_methods/argument_first_ontology_v2.json").read_text())
        self.assertEqual(len(d["tiers"]),4)
        self.assertEqual([x["id"] for x in d["tiers"]],
          ["discovered_language_cluster","reason_language_family","interpreted_claim","regulatory_crosswalk"])
        self.assertFalse(d["tiers"][2]["ready"])
        self.assertIn("source_quote",d["dimensions"]["claim_unit"])
        self.assertIn("regulatory_crosswalk",d["tiers"][3]["id"])

    def test_unsupervised_discovery_and_census_are_independent(self):
        discovery=json.loads((DOCS/"data"/"argument_landscape.json").read_text())
        census=json.loads((DOCS/"data"/"exhaustive_census.json").read_text())
        role=json.loads((DOCS/"data"/"argument_language_by_role.json").read_text())
        self.assertEqual(discovery["source_filings_scanned"],3231)
        self.assertEqual(discovery["readable_filings"],3230)
        self.assertEqual(len(discovery["language_themes"]),16)
        self.assertEqual(len(census["argument_language_signals"]),14)
        self.assertEqual(len(role["role_ids"]),len(census["roles"]))
        self.assertEqual(role["role_ids"],[x["id"] for x in census["roles"]])
        self.assertEqual(sum(x["filings"] for x in census["roles"]),3231)
        for family in census["argument_language_signals"]:
            counts=role["counts_by_argument"][family["id"]]
            self.assertEqual(sum(counts),family["filings_with_language"])
            self.assertTrue(all(0<=n<=population["filings"] for n,population in zip(counts,census["roles"])))

    def test_atlas_does_not_use_llm_syntheses_as_corpus_facts(self):
        js=(DOCS/"assets"/"argument_atlas.js").read_text()
        for needed in ("landscape.language_themes","topic_terms","e.quote","repeatRisk",
                       "concentrationRisk","reason","counts_by_argument","renderMap"):
            self.assertIn(needed,js)
        self.assertNotIn("llm_synthesis",js)
        self.assertNotIn("llm_argument_map",js)
        html=(DOCS/"atlas.html").read_text()
        self.assertIn("not a validated position",html)
        self.assertIn("analyst-defined search vocabularies",html)

    def test_regulatory_crosswalk_does_not_claim_positions(self):
        js=(DOCS/"assets"/"regulatory_crosswalk.js").read_text()
        for token in ("notice_status","filing_policy_checks","c.mentions","keyword/phrase",
                      "regulatory question","related reason-language"):
            self.assertIn(token,js)
        self.assertIn("not positions",js)
        self.assertEqual(len(json.loads((DOCS/"data"/"provisions.json").read_text())["provisions"]),29)

if __name__=="__main__":unittest.main()
