import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from erate.engine import write_csv
from scripts.package_policy_excerpt_sample import redact_contact, select_sample, package


class PolicySamplePackageTests(unittest.TestCase):
    def test_contact_masking(self):
        text='Contact jane@example.org or (212) 555-0119 regarding the E-Rate proposal.'
        result=redact_contact(text)
        self.assertNotIn('jane@example.org',result)
        self.assertNotIn('(212) 555-0119',result)
        self.assertIn('[EMAIL REDACTED]',result)
        self.assertIn('[PHONE REDACTED]',result)

    def test_sample_is_stratified_across_issues_without_duplicate_pair(self):
        pairs=[]
        for issue in ['parent_opt_out','consultant_registration']:
            for sid in range(6):
                pairs.append(dict(submission_id=str(sid),provision_id=issue,hit_count='2',
                                  source_url='https://www.fcc.gov/ecfs/filing/'+str(sid),
                                  matched_terms='test',ocr_candidate='0',excerpt='some test',
                                  source_text_sha256='abc'))
        sample=select_sample(pairs,3)
        self.assertEqual(len(sample),6)
        self.assertEqual(len({(r['submission_id'],r['provision_id']) for r in sample}),6)

    def test_privacy_reviewable_archive_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'corpus'
            p=base/'analysis_observatory/research_snapshot_ocr_candidate_v1/policy_analysis_augmented'
            p.mkdir(parents=True)
            rows=[dict(submission_id='111',provision_id='parent_opt_out',
                       excerpt='Parents want an opt-out. Contact alice@example.org.',
                       source_url='https://www.fcc.gov/ecfs/filing/111',
                       matched_terms='opt-out',ocr_candidate='0',
                       source_text_sha256='SHA',hit_count='1')]
            write_csv(p/'candidate_passages.csv',rows,list(rows[0]))
            archive,report=package(base,'ocr_candidate_v1',1,400,Path(tmp)/'upload.zip')
            self.assertEqual(report['sample_provision_pairs'],1)
            with zipfile.ZipFile(archive) as z:
                excerpt=json.loads(z.read('sample_excerpt_pairs.jsonl').decode().strip())
                self.assertNotIn('alice@example.org',excerpt['excerpt'])
                self.assertIn('source_url',excerpt)
                self.assertNotIn('filer_raw',excerpt)
            with self.assertRaises(FileExistsError):
                package(base,'ocr_candidate_v1',1,400,Path(tmp)/'upload.zip')


if __name__=='__main__':
    unittest.main()
