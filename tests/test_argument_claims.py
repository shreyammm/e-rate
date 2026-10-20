import tempfile
import unittest
from pathlib import Path

from erate.engine import normalized_text,sha256,write_csv
from scripts.validate_argument_claims import validate


class ArgumentValidationTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.snap=self.base/'analysis_observatory/research_snapshot_ocr_candidate_v1'
        (self.snap/'ocr_augmented_text').mkdir(parents=True)
        self.body=('The FCC should preserve the current discount matrix. '
                   'Our rural district cannot afford the proposed increase in fees. '
                   'We also think families should have offline alternatives.')
        (self.snap/'ocr_augmented_text/123.txt').write_text(self.body)
        rows=[dict(submission_id='123',source_url='https://www.fcc.gov/ecfs/filing/123',
             augmented_sha256=sha256(normalized_text(self.body).encode()),has_unreviewed_ocr='0')]
        write_csv(self.snap/'research_inventory.csv',rows,list(rows[0]))

    def example(self,argid,kind,quote):
        return dict(argument_id=argid,submission_id='123',provision_id='discount_matrix',
                    claim_kind=kind,argument_summary='Rural affordability consequence',
                    asserted_mechanism='Lower support would raise direct district costs.',
                    requested_action='Keep the existing discounts.',
                    evidence_quote=quote,evidence_type='personal_experience',
                    evidence_independently_verified='no',
                    review_status='manual_reviewed',coder_id='researcher_1')

    def test_multiple_evidence_arguments_same_filing_and_provision(self):
        a=self.example('argument_1','cost_or_savings',
                       'Our rural district cannot afford the proposed increase in fees.')
        b=self.example('argument_2','normative_value',
                       'The FCC should preserve the current discount matrix.')
        path=self.base/'arguments.csv'
        write_csv(path,[a,b],list(a))
        report=validate(self.base,path)
        self.assertEqual(report['accepted_argument_rows'],2)
        self.assertEqual(report['source_filings_in_approved_arguments'],1)
        self.assertEqual(report['distinct_filing_provision_pairs'],1)
        self.assertEqual(report['independently_verified_cited_evidence_count'],0)
        self.assertTrue((self.snap/'policy_analysis_augmented/validated_argument_claims.csv').exists())

    def test_reject_hallucinated_quote_and_unverified_verification_claim(self):
        a=self.example('arg_a','cost_or_savings','An invented quote that cannot be found.')
        b=self.example('arg_b','cost_or_savings',
                       'Our rural district cannot afford the proposed increase in fees.')
        b['evidence_independently_verified']='yes'
        path=self.base/'bad.csv';write_csv(path,[a,b],list(a))
        report=validate(self.base,path)
        self.assertEqual(report['accepted_argument_rows'],0)
        self.assertEqual(report['rejected_argument_rows'],2)
        self.assertEqual(report['distinct_filing_provision_pairs'],0)


if __name__=='__main__':
    unittest.main()
