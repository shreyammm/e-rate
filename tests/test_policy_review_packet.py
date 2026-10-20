import tempfile
import unittest
from pathlib import Path
from erate.engine import write_csv,normalized_text,sha256
from scripts.build_policy_review_packet import make_review_sample,build


class HumanReviewPacketTest(unittest.TestCase):
    def test_keeps_keyword_negative_controls_explicit(self):
        proposals=[{'id':'parent_opt_out'},{'id':'consultant_registration'}]
        filings=[{'submission_id':str(i),'source_url':'https://www.fcc.gov/ecfs/filing/'+str(i),
                  'augmented_chars':'500','agency_record_candidate':'0','has_unreviewed_ocr':'0'}
                 for i in range(1,11)]
        queue=[{'submission_id':'1','provision_id':'parent_opt_out',
                'source_url':filings[0]['source_url'],'matched_terms':'opt out','ocr_candidate':'0'}]
        rows=make_review_sample(queue,filings,proposals,2,4,20261020)
        self.assertEqual(len(rows),5)
        self.assertEqual(sum(r['selection_stratum']=='keyword_negative_control' for r in rows),4)
        self.assertEqual(len(set((r['submission_id'],r['provision_id']) for r in rows)),5)

    def test_offline_source_text_is_html_escaped(self):
        with tempfile.TemporaryDirectory() as temp:
            corpus=Path(temp)
            snap=corpus/'analysis_observatory/research_snapshot_ocr_candidate_v1'
            (snap/'ocr_augmented_text').mkdir(parents=True)
            text='The parent opt-out needs <script>alert(1)</script> because screens affect learning.'
            (snap/'ocr_augmented_text/111.txt').write_text(text)
            inventory=[dict(submission_id='111',source_url='https://www.fcc.gov/ecfs/filing/111',
                            agency_record_candidate='0',augmented_chars=str(len(text)),
                            augmented_sha256=sha256(normalized_text(text).encode()),
                            has_unreviewed_ocr='0')]
            write_csv(snap/'research_inventory.csv',inventory,list(inventory[0]))
            path=snap/'policy_analysis_augmented/review_queue_GENERATED.csv'
            path.parent.mkdir(parents=True)
            queue=[dict(submission_id='111',provision_id='parent_opt_out',
                        source_url='https://www.fcc.gov/ecfs/filing/111',
                        matched_terms='opt-out',ocr_candidate='0')]
            write_csv(path,queue,list(queue[0]))
            result,n=build(corpus,per_provision=1,negative_controls=0,chars_per_document=1000)
            html=result.read_text()
            self.assertEqual(n,1)
            self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;',html)
            self.assertNotIn('<script>alert(1)</script>',html)
            self.assertIn('requested_action',html)
            self.assertIn('Export reviewed rows to CSV',html)


if __name__=='__main__':
    unittest.main()
