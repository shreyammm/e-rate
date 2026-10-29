import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.assets=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if d.get('id'): self.ids.add(d['id'])
        if tag=='script' and d.get('src'):self.assets.append(d['src'])
        if tag=='link' and d.get('href'):self.assets.append(d['href'])


class StaticPublicationTests(unittest.TestCase):
    def test_provisions_match_research_codebook(self):
        book=json.loads((ROOT/'analysis_methods/provision_codebook_v1.json').read_text())
        public=json.loads((ROOT/'docs/data/provisions.json').read_text())
        self.assertEqual(len(book['provisions']),29)
        self.assertEqual(len(public['provisions']),29)
        self.assertEqual({p['id'] for p in book['provisions']},
                         {p['id'] for p in public['provisions']})
        for original,web in zip(book['provisions'],public['provisions']):
            for k in ('id','label','category','policy_option',
                      'notice_status','notice_paragraph_range'):
                self.assertEqual(original[k],web[k])

    def test_placeholder_publishes_no_fabricated_positions(self):
        payload=json.loads((ROOT/'docs/data/public_results.json').read_text())
        self.assertEqual(payload['reviewed_filing_provision_pairs'],0)
        self.assertEqual(payload['provisions'],[])
        self.assertEqual(payload['publication_status'],'awaiting_validated_position_data')

    def test_static_site_links_and_accessibility_targets(self):
        raw=(ROOT/'docs/index.html').read_text()
        p=LinkParser()
        p.feed(raw)
        # Current front page is a navigational landing page; the old dashboard
        # charts are separate workbenches. Verify navigation and caveats instead.
        self.assertIn('aria-label="Primary navigation"',raw)
        for target in ("matrix.html","stakeholders.html","corpus.html","research.html"):
            self.assertIn('href="./'+target+'"',raw)
        for asset in p.assets:
            self.assertTrue((ROOT/'docs'/asset).is_file(),asset)
        self.assertIn('not affiliated with the fcc',raw.lower())
        self.assertIn('machine-extracted argument candidates',raw)
        self.assertIn('not verified supporters',raw)


if __name__=='__main__':
    unittest.main()
