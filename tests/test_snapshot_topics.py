import json
import tempfile
import unittest
from pathlib import Path

from erate.engine import normalized_text, sha256, write_csv
from erate.topics import analyze


class SnapshotTopicSmokeTest(unittest.TestCase):
    def test_topics_run_on_immutable_snapshot_and_validate_hashes(self):
        with tempfile.TemporaryDirectory() as t:
            corpus=Path(t)/'corpus'
            analysis=corpus/'analysis_observatory'
            snap=analysis/'research_snapshot_synthetic'
            folder=snap/'ocr_augmented_text'
            folder.mkdir(parents=True)
            rows=[]
            groups=[
                ('rural schools libraries broadband connectivity access programs education funding',4),
                ('students privacy online safety internet protections technology children safeguards',4),
                ('administrative compliance reporting audits costs efficiency application paperwork',4)
            ]
            for j,(words,count) in enumerate(groups):
                for i in range(count):
                    sid=str(1000+j*10+i)
                    text=((words+' ') * 15).strip()+f' Filing evidence example {j} {i}.'
                    (folder/f'{sid}.txt').write_text(text+'\n')
                    rows.append(dict(submission_id=sid,augmented_chars=len(text),
                        augmented_sha256=sha256(normalized_text(text).encode()),
                        agency_record_candidate='0',
                        source_url=f'https://www.fcc.gov/ecfs/filing/{sid}'))
            write_csv(snap/'research_inventory.csv',rows,list(rows[0]))
            report=analyze(corpus,analysis,n_topics=3,max_chars=5000,
                           snapshot_id='synthetic',view='augmented')
            self.assertEqual(report['eligible_filings'],12)
            self.assertEqual(report['text_view'],'augmented')
            self.assertEqual(report['source_snapshot_id'],'synthetic')
            self.assertTrue((snap/'themes_augmented/exploratory_topics.csv').exists())
            self.assertFalse((snap/'themes_baseline/exploratory_topics.csv').exists())
            (folder/'1000.txt').write_text('tampered with!')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                analyze(corpus,analysis,n_topics=3,max_chars=5000,
                        snapshot_id='synthetic',view='augmented')


if __name__ == '__main__':
    unittest.main()
