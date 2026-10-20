import base64
import collections
import gzip
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FullTextCensusPublicationTests(unittest.TestCase):
    def test_every_filing_is_classified_without_sampling(self):
        census=json.loads((ROOT/'docs/data/exhaustive_census.json').read_text())
        index=json.loads((ROOT/'docs/data/corpus_index.json').read_text())
        roles=json.loads((ROOT/'docs/data/full_text_filer_roles.json').read_text())
        records=index['filings']
        self.assertEqual(len(records),3231)
        self.assertEqual(census['coverage']['filings'],3231)
        self.assertEqual(census['coverage']['filings_with_text'],3230)
        self.assertEqual(census['coverage']['characters_analyzed'],211756379)
        self.assertEqual(census['coverage']['filing_policy_checks'],93699)
        self.assertEqual(len(census['provisions']),29)
        self.assertEqual(sum(x['filings'] for x in census['roles']),3231)
        self.assertEqual(records[0]['id'],roles['expected_first_id'])
        self.assertEqual(records[-1]['id'],roles['expected_last_id'])
        codes=gzip.decompress(base64.b64decode(roles['sequence'])).decode('ascii')
        self.assertEqual(len(codes),3231)
        self.assertEqual(dict(collections.Counter(codes)),roles['expected_code_counts'])
        self.assertEqual(roles['expected_code_counts']['5'],143)
        self.assertEqual(roles['expected_code_counts']['0'],924)
        self.assertEqual(roles['expected_code_counts']['1'],857)
        by_id={r['id']:roles['legend'][code] for r,code in zip(records,codes)}
        # Previous metadata-only errors: institutional, policy NGO and elected office filings.
        self.assertEqual(by_id['26110080373'],'school_district_or_school')
        self.assertEqual(by_id['26110078107'],'school_district_or_school')
        self.assertEqual(by_id['26110081295'],'advocacy_nonprofit_or_trade_association')
        self.assertEqual(by_id['26110080878'],'advocacy_nonprofit_or_trade_association')
        self.assertEqual(by_id['26110081059'],'government_or_tribal_organization')
        self.assertEqual(by_id['26110081382'],'named_person_capacity_unstated')
        self.assertEqual(len({r['id'] for r in records}),len(records))
        self.assertEqual(set(codes),set(roles['legend']))
        role_counter=collections.Counter(roles['legend'][c] for c in codes)
        self.assertEqual({r['id']:r['filings'] for r in census['roles']},dict(role_counter))

    def test_full_population_argument_by_role_sums(self):
        c=json.loads((ROOT/'docs/data/exhaustive_census.json').read_text())
        matrix=json.loads((ROOT/'docs/data/argument_language_by_role.json').read_text())
        self.assertEqual(matrix['role_ids'],[x['id'] for x in c['roles']])
        self.assertEqual(len(matrix['counts_by_argument']),14)
        for family in c['argument_language_signals']:
            counts=matrix['counts_by_argument'][family['id']]
            self.assertEqual(len(counts),len(c['roles']))
            self.assertEqual(sum(counts),family['filings_with_language'])
            for n,role in zip(counts,c['roles']):
                self.assertLessEqual(n,role['filings'])
        html=(ROOT/'docs/index.html').read_text()
        self.assertIn('id="argument-role-table"',html)
        self.assertIn('id="argument-role-family"',html)

    def test_all_29_proposal_counts_and_caveats(self):
        census=json.loads((ROOT/'docs/data/exhaustive_census.json').read_text())
        for x in census['provisions']:
            self.assertGreaterEqual(x['mentions'],0)
            self.assertLessEqual(x['mentions'],3231)
            self.assertLessEqual(x['agency_type_candidates'],x['mentions'])
            self.assertLessEqual(x['other_docket_signature'],x['mentions'])
        self.assertEqual(next(x['mentions'] for x in census['provisions']
                              if x['id']=='erate_sunset'),2176)
        self.assertIn('not support, opposition',census['retrieval_method'])
        self.assertEqual(census['cross_docket_signal']['filings'],123)
        self.assertEqual(len(census['argument_language_signals']),14)
        self.assertEqual(next(x['filings_with_language'] for x in
                              census['argument_language_signals']
                              if x['id']=='educational_opportunity'),1616)
        self.assertTrue(all(0<=x['agency_type_candidates']<=x['filings_with_language']
                            for x in census['argument_language_signals']))
        html=(ROOT/'docs/index.html').read_text()
        self.assertIn('id="argument-census-bars"',html)
        self.assertIn('id="census-proposals"',html)
        self.assertFalse('manual_spot_check' in (ROOT/'docs/data/research_dashboard.json').read_text())

if __name__=='__main__':
    unittest.main()
