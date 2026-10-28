"""Check the main research page wiring and its source-first publication contract."""
import re
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StakeholderPageTest(unittest.TestCase):
    def test_all_widget_ids_exist_once(self):
        html=(ROOT/'docs/stakeholders.html').read_text(encoding='utf-8')
        js=(ROOT/'docs/assets/stakeholders.js').read_text(encoding='utf-8')
        elements=re.findall(r'\bid="([^"]+)"',html)
        self.assertEqual(len(elements),len(set(elements)))
        ids=set(re.findall(r"\$\('([a-z][a-z0-9-]+)'\)",js))
        missing=ids-set(elements)
        self.assertEqual(missing,set(),f'JS expects missing HTML IDs: {missing}')
    def test_linked_data_and_entry_points(self):
        html=(ROOT/'docs/stakeholders.html').read_text()
        js=(ROOT/'docs/assets/stakeholders.js').read_text()
        for value in ['docs/stakeholders.html','docs/assets/stakeholders.js','docs/assets/stakeholders.css']:
            self.assertTrue((ROOT/value).exists())
        self.assertIn('./data/stakeholder_argument_census.json',js)
        self.assertIn('stakeholder-arguments-v1',js)
        self.assertIn('source',html.lower())
        self.assertIn('./stakeholders.html',(ROOT/'docs/index.html').read_text())
        self.assertIn('./stakeholders.html',(ROOT/'docs/research.html').read_text())
    def test_frequency_and_validation_exports_have_explicit_denominators(self):
        html=(ROOT/'docs/stakeholders.html').read_text()
        js=(ROOT/'docs/assets/stakeholders.js').read_text()
        for control in ('download-matrix','download-audit','download'):
            self.assertIn(f'id="{control}"',html)
            self.assertIn(f"$('{control}')",js)
        for field in ('pct_of_all_group_filings','pct_of_coded_group_filings',
                      'pct_of_all_filings_with_this_argument','distinct_original_source_texts',
                      'named_institutions_with_this_argument','selection_reason'):
            self.assertIn(field,js)
        self.assertIn('negative_control',js)
        self.assertIn('reviewer_notes',js)
    def test_source_citation_and_provisional_position_notice(self):
        text=(ROOT/'docs/stakeholders.html').read_text()
        self.assertIn('not verified opinions',text)
        js=(ROOT/'docs/assets/stakeholders.js').read_text()
        self.assertIn('https://www.fcc.gov/ecfs/filing/',js)
        self.assertIn('filing',js)
if __name__=='__main__':unittest.main()
