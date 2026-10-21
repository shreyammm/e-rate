import json
import tempfile
import unittest
from pathlib import Path
from scripts.publish_research_findings import build

class FindingsTest(unittest.TestCase):
    def test_no_sample_extrapolation_or_unvalidated_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);land=root/'land.json';explor=root/'model.json';out=root/'research.html'
            land.write_text(json.dumps({
             'coverage':{'corpus_records':3231,'source_text_records':3230,
               'completed_machine_filings':20,'machine_claim_rows':1,
               'full_source_quote_offset_verified':1},
             'clusters':[{'working_label':'network maintenance','distinct_filings':1,
                'argument_rows':1,'unique_source_texts':1,'role_filings':{'school_district_or_school':1},
                'examples':[{'argument':'E-Rate helps sustain school connectivity',
                   'quote':'Preserve support for school infrastructure',
                   'submission_id':'26110072018','source_url':'https://www.fcc.gov/ecfs/filing/26110072018'}]}],
             'role_filings_with_model_claims':{'school_district_or_school':1}}))
            explor.write_text(json.dumps({
             'completed_filings':20,'generated_utc':'2026-10-21T15:00:00Z',
             'machine_evidence_quality':{'semantic_scope_full_text_filings':19,
                                         'semantic_scope_prioritized_windows_filings':1},
             'provisions':[{'provision_id':'erate_sunset','label':'Sunset policy',
                            'filings_mentioning':1,'positions':{'oppose':1}}]}))
            result=build(land,explor,out)
            self.assertEqual(result['completed'],20)
            text=out.read_text()
            self.assertIn('20',text)
            self.assertIn('3,230',text)
            self.assertIn('selected',text)
            self.assertIn('network maintenance',text)
            self.assertIn('href="https://www.fcc.gov/ecfs/filing/26110072018"',text)
            self.assertNotIn('all 3,230 filings have been',text)
            self.assertIn('not a verified survey',text)
            bad=json.loads(explor.read_text());bad['completed_filings']=21
            explor.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError,'disagree'):
                build(land,explor,out)

if __name__=='__main__':
    unittest.main()
