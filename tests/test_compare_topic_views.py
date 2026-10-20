import json
import tempfile
import unittest
from pathlib import Path

from erate.engine import write_csv
from scripts.compare_topic_views import analyze, match_topics


class ThemeComparisonTest(unittest.TestCase):
    def test_optimal_topic_matching_is_not_identical_numeric_ids(self):
        base={'1':'T01','2':'T01','3':'T02','4':'T02'}
        aug={'1':'T02','2':'T02','3':'T01','4':'T01'}
        matched=match_topics(['T01','T02'],['T01','T02'],base,aug)
        self.assertEqual(set(matched),{('T01','T02',2),('T02','T01',2)})

    def test_comparison_validates_identity_and_newly_eligible_filings(self):
        with tempfile.TemporaryDirectory() as temp:
            snap=Path(temp)/'research_snapshot_synthetic'
            base=snap/'themes_baseline'
            aug=snap/'themes_augmented'
            base.mkdir(parents=True)
            aug.mkdir(parents=True)
            (snap/'snapshot_summary.json').write_text(json.dumps({'run_id':'synthetic'}))
            records={
                'baseline':[('101','T01',.9),('102','T01',.8),('103','T02',.9),('104','T02',.7)],
                'augmented':[('101','T02',.8),('102','T02',.9),('103','T01',.8),
                             ('104','T01',.7),('105','T01',.9)]}
            for view,folder in [('baseline',base),('augmented',aug)]:
                rows=[dict(submission_id=sid,topic_id=tid,
                           topic_strength=str(conf),
                           source_url=f'https://www.fcc.gov/ecfs/filing/{sid}')
                      for sid,tid,conf in records[view]]
                write_csv(folder/'exploratory_topic_map.csv',rows,list(rows[0]))
                topics=[dict(topic_id=tid,top_terms=f'network; broadband; {tid}') for tid in ['T01','T02']]
                write_csv(folder/'exploratory_topics.csv',topics,list(topics[0]))
                (folder/'exploratory_topic_method.json').write_text(
                    json.dumps({'text_view':view,'source_snapshot_id':'synthetic',
                                'eligible_filings':len(rows)}))
            report=analyze(snap,sample_per_topic=2)
            self.assertEqual(report['filings_in_both_views'],4)
            self.assertEqual(report['filings_newly_eligible_after_ocr'],1)
            self.assertEqual(report['common_filings_retaining_matched_topic'],4)
            self.assertEqual(report['matched_topic_assignment_stability_on_common'],1.0)
            self.assertTrue((snap/'theme_comparison/topic_alignment.csv').is_file())
            self.assertTrue((snap/'theme_comparison/topic_transitions.csv').is_file())
            self.assertTrue((snap/'theme_comparison/human_theme_review_sample.csv').is_file())
            report2=analyze(snap)
            self.assertEqual(report2['filings_newly_eligible_after_ocr'],1)
            # Breaking the saved model's eligibility inventory must not silently pass.
            (base/'exploratory_topic_method.json').write_text(
                json.dumps({'text_view':'augmented','source_snapshot_id':'synthetic',
                            'eligible_filings':4}))
            with self.assertRaisesRegex(ValueError,'does not match baseline'):
                analyze(snap)

    def test_reject_missing_augmentation_and_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError,'same common filings'):
            match_topics(['T01'],['T01'],{'1':'T01'},{'2':'T01'})


if __name__=='__main__':
    unittest.main()
