import json
import tempfile
import unittest
from pathlib import Path

from erate.engine import normalized_text, sha256, write_csv, read_csv
from scripts.prepare_policy_analysis import candidate_windows, analyze as retrieve
from scripts.validate_position_annotations import analyze as validate
from scripts.export_public_site_data import build as export


class ProvisionAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)/'corpus'
        self.snap=self.base/'analysis_observatory/research_snapshot_ocr_candidate_v1'
        texts=self.snap/'ocr_augmented_text'
        texts.mkdir(parents=True)
        self.text={
            '111':'We support a parental opt-out from screen-based instruction at school. '
                  'Parents should be able to refuse screen instruction to protect children.',
            '222':'We oppose a parental opt-out from screen-based instruction. '
                  'A broad opt-out would increase school administration costs.',
            '333':'We propose that E-Rate maintain support for rural public libraries '
                  'and community broadband access for students.'
        }
        inv=[]
        for sid,text in self.text.items():
            (texts/f'{sid}.txt').write_text(text+'\n')
            inv.append({
                'submission_id':sid,'source_url':f'https://www.fcc.gov/ecfs/filing/{sid}',
                'augmented_sha256':sha256(normalized_text(text).encode()),
                'has_unreviewed_ocr':'0'
            })
        write_csv(self.snap/'research_inventory.csv',inv,list(inv[0]))

    def test_keyword_candidates_are_not_support_oppose_labels(self):
        windows=candidate_windows(self.text['111'],['opt-out','screen-based instruction'])
        self.assertTrue(windows)
        for w in windows:
            self.assertEqual(self.text['111'][w['excerpt_start']:w['excerpt_end']],w['excerpt'])
        report=retrieve(self.base)
        self.assertEqual(report['stance_counts_inferred'],0)
        self.assertGreater(report['distinct_filing_provision_candidate_pairs'],0)
        q,_=read_csv(self.snap/'policy_analysis_augmented/review_queue_GENERATED.csv')
        matches=[r for r in q if r['provision_id']=='parent_opt_out']
        self.assertEqual({r['submission_id'] for r in matches},{'111','222'})
        self.assertTrue(all(not r['position'] for r in matches))

    def test_verbatim_human_reviews_export_only_as_reviewed(self):
        quote1='We support a parental opt-out from screen-based instruction at school.'
        quote2='We oppose a parental opt-out from screen-based instruction.'
        records=[
            dict(submission_id='111',provision_id='parent_opt_out',position='support',
                 review_status='manual_reviewed',coder_id='researcher_1',
                 requested_action='Require a parent opt-out.',
                 rationale='Families need an alternative to screens.',
                 reason_families='parental_autonomy',stakeholder_role='parent_guardian',
                 evidence_quote=quote1,notes='Checked against original.'),
            dict(submission_id='222',provision_id='parent_opt_out',position='oppose',
                 review_status='manual_reviewed',coder_id='researcher_1',
                 requested_action='Do not require parent opt-outs.',
                 rationale='Administrative costs could rise.',
                 reason_families='administrative_burden',stakeholder_role='school_district',
                 evidence_quote=quote2,notes='Checked against original.')
        ]
        path=self.base/'human_reviews.csv'
        write_csv(path,records,list(records[0]))
        report=validate(self.base,path)
        self.assertEqual(report['valid_human_reviews'],2)
        self.assertEqual(report['position_counts_in_reviewed_rows']['support'],1)
        self.assertEqual(report['position_counts_in_reviewed_rows']['oppose'],1)
        output,payload=export(self.base)
        self.assertTrue(output.is_file())
        self.assertIn('site_preview',str(output))
        self.assertEqual(payload['reviewed_filing_provision_pairs'],2)
        target=next(x for x in payload['provisions'] if x['id']=='parent_opt_out')
        self.assertEqual(target['counts']['support'],1)
        self.assertEqual(target['counts']['oppose'],1)

    def test_reject_hallucinated_or_unreviewed_stance(self):
        records=[
            dict(submission_id='111',provision_id='parent_opt_out',position='support',
                 review_status='manual_reviewed',coder_id='researcher_1',
                 requested_action='Require opt-out.',rationale='Parent rights.',
                 evidence_quote='The FCC has already adopted this final rule.'),
            dict(submission_id='222',provision_id='parent_opt_out',position='oppose',
                 review_status='pending',coder_id='model_only',
                 requested_action='Reject opt-out.',rationale='Cost',
                 evidence_quote='We oppose a parental opt-out from screen-based instruction.')
        ]
        path=self.base/'bad_reviews.csv'
        write_csv(path,records,list(records[0]))
        report=validate(self.base,path)
        self.assertEqual(report['valid_human_reviews'],0)
        self.assertEqual(report['invalid_or_unreviewed_rows'],2)
        self.assertGreater(report['rejection_reasons']['evidence_not_unique_or_absent_in_source'],0)
        self.assertGreater(report['rejection_reasons']['not_human_reviewed'],0)


if __name__=='__main__':
    unittest.main()
