import base64,csv,hashlib,json,unittest,zlib
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class FullTextRolePublicationTest(unittest.TestCase):
    def test_every_filing_role_has_a_verified_record_index_position(self):
        data=json.loads((ROOT/'docs/data/full_text_role_codes.json').read_text())
        corpus=json.loads((ROOT/'docs/data/corpus_index.json').read_text())
        rows=corpus['filings']
        self.assertEqual(len(rows),3231)
        actual=hashlib.sha256('\n'.join(x['id'] for x in rows).encode()).hexdigest()
        self.assertEqual(actual,data['id_order_sha256'])
        decoded={key:zlib.decompress(base64.b64decode(data[key+'_deflate_b64'])).decode()
                 for key in ('role_codes','confidence_codes')}
        self.assertEqual(len(decoded['role_codes']),3231)
        self.assertEqual(len(decoded['confidence_codes']),3231)
        self.assertTrue(set(decoded['role_codes']).issubset(data['role_keys']))
        self.assertTrue(set(decoded['confidence_codes']).issubset(data['confidence_keys']))
        roles=[data['role_keys'][code] for code in decoded['role_codes']]
        counts=Counter(roles)
        self.assertEqual(sum(counts.values()),3231)
        self.assertEqual(counts['school_district'],1292)
        self.assertEqual(counts['library'],280)
        self.assertEqual(counts['parent_guardian'],109)
        self.assertEqual(counts['advocacy_nonprofit'],400)
        self.assertEqual(counts['unresolved'],1055)
        self.assertEqual(counts['tribal_government'],1)
        # Reproduce full-text role × previously published issue mention cross-tab.
        check=Counter()
        for row,role in zip(rows,roles):
            for j,key in enumerate(corpus['issue_keys']):
                if row['issues']&(1<<j):check[key]+=1
        agg=json.loads((ROOT/'docs/data/research_dashboard.json').read_text())
        self.assertEqual(dict(check),{x['id']:x['n'] for x in agg['issues']})

    def test_site_loads_role_data_before_dashboard(self):
        html=(ROOT/'docs/index.html').read_text()
        self.assertLess(html.index('fulltext-roles.js'),html.index('site.js'))
        scripts=(ROOT/'docs/assets/site.js').read_text()
        self.assertIn('applyFullTextRoles',scripts)
        self.assertIn('falling back to filer-field',scripts)

if __name__=='__main__':
    unittest.main()
