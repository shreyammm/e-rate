import json
import unittest
from pathlib import Path
from scripts.export_static_corpus_index import affiliation_hint,safe_org_display,ISSUES

ROOT=Path(__file__).resolve().parents[1]


class PublicFilingIndexTests(unittest.TestCase):
    def test_explorer_issue_keys_and_aggregate_counts(self):
        aggregate=json.loads((ROOT/'docs/data/research_dashboard.json').read_text())
        self.assertEqual(aggregate['indexed_filings'],3231)
        self.assertEqual(aggregate['text_filings'],3230)
        self.assertEqual(aggregate['ocr_candidate_attachments'],206)
        self.assertEqual(list(ISSUES),[x['id'] for x in aggregate['issues']])
        self.assertEqual(sum(x['filings'] for x in aggregate['roles']),3231)
        self.assertTrue(all('n' in r for r in aggregate['issues']))
        self.assertEqual(sum(int(r['filings']) for r in aggregate['roles']),3231)
        self.assertEqual(sum(aggregate['directional_signals'][0]['role_counts'].values()),
                         aggregate['directional_signals'][0]['filings'])
        for issue in aggregate['issues']:
            self.assertEqual(sum(aggregate['issue_role_matrix'][issue['id']].values()),
                             issue['n'])
        self.assertEqual(len({r['id'] for r in aggregate['examples']}),
                         len(aggregate['examples']))
        self.assertGreater(len(aggregate['examples']),10)
        self.assertTrue(all(r['filing'].isdigit() for r in aggregate['examples']))
        self.assertFalse(any('filer_raw' in r for r in aggregate['examples']))

    def test_critical_role_proxy_examples(self):
        self.assertEqual(affiliation_hint('Theodora Scarato | Director of Wireless and EMF Program at Environmental Health Sciences'),'nonprofit')
        self.assertEqual(affiliation_hint('Gatesville Independent School District'),'school')
        self.assertEqual(affiliation_hint('Sanibel Public Library District'),'library')
        self.assertEqual(affiliation_hint('Office of Media Relations'),'government')
        self.assertEqual(affiliation_hint('Funds For Learning, LLC'),'consultant')
        self.assertEqual(affiliation_hint('Jane Doe'),'unresolved')

    def test_do_not_bulk_publish_person_names(self):
        self.assertEqual(safe_org_display('Avery Johnson','unresolved'),'')
        self.assertEqual(safe_org_display('Avery Johnson | Riverview School District','school'),'')
        self.assertEqual(safe_org_display('example@example.com','nonprofit'),'')
        self.assertEqual(safe_org_display('Canyon School District','school'),'Canyon School District')


if __name__=='__main__':
    unittest.main()
