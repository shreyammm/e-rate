import json,tempfile,unittest
from pathlib import Path
from scripts.label_argument_map import label_map

class LandscapeLabelTests(unittest.TestCase):
    def test_no_training_stable_cache_and_reproducible_filing_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'landscape.json';cache=Path(d)/'labels'
            group={'id':'language_theme_1','topic_terms':['screen time','funding'],
                   'evidence':[{'id':'26110079250','filer':'Parent A','quote':'Schools should restrict screen time as a condition of receiving public E-Rate funding for internet access.'}]}
            p.write_text(json.dumps({'language_themes':[group]}))
            calls=[]
            def model(group,model):
                calls.append(1)
                return {'status':'machine_generated_unreviewed','label':'Fund internet access with safety conditions',
                'argument_summary':'Parents request limits on screen time as a condition of receiving E-Rate discounts.',
                'other_perspectives':'','source_indices':[1],'source_filing_ids':['26110079250']}
            a=label_map(p,cache,generate=model)
            self.assertEqual(a['automatically_labeled_themes'],1)
            self.assertEqual(len(calls),1)
            b=label_map(p,cache,generate=lambda *args:self.fail('should use cached model output'))
            self.assertEqual(b['cache_hits'],1)
            self.assertEqual(json.loads(p.read_text())['language_themes'][0]['llm_synthesis']['source_filing_ids'],['26110079250'])