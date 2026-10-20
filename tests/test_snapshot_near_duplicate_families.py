import csv
import json
import tempfile
import unittest
from pathlib import Path

from erate.engine import normalized_text, sha256, write_csv
from scripts.snapshot_near_duplicate_families import analyze, families_from_pairs


class CandidateFamilyTests(unittest.TestCase):
    def test_chain_components_not_complete_similarity_cliques(self):
        info={sid:dict(
            filer_raw=('ONE' if sid!='3' else 'Two'),
            source_url='https://www.fcc.gov/ecfs/filing/'+sid,
            date_submission='2026-10-13',has_unreviewed_ocr='0'
        ) for sid in ['1','2','3','4','5']}
        edges=[
            dict(submission_id_a='1',submission_id_b='2',shingle_jaccard=.93),
            dict(submission_id_a='2',submission_id_b='3',shingle_jaccard=.89),
            dict(submission_id_a='4',submission_id_b='5',shingle_jaccard=.91)
        ]
        f,m=families_from_pairs(edges,info,'augmented')
        self.assertEqual([r['filing_count'] for r in f],[3,2])
        self.assertEqual([r['edge_count'] for r in f],[2,1])
        self.assertEqual(f[0]['distinct_exact_filer_fields'],2)
        self.assertEqual(len(m),5)
        self.assertEqual(len({r['submission_id'] for r in m}),5)
        # A chain component is not a proof all text pairs have Jaccard > threshold.

    def test_strict_snapshot_hash_validation_and_clean_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/'corpus'
            snap=base/'analysis_observatory/research_snapshot_example'
            (snap/'ocr_augmented_text').mkdir(parents=True)
            rows=[]
            for i in range(7):
                sid=str(100+i)
                content=(
                    'E-Rate broadband funding helps students access classes and '
                    'lets libraries support rural communities with vital internet connectivity. '
                    * 3
                )
                if i==6:
                    content=('Consultant procurement competitive bidding oversight changes '
                             'should be considered carefully for school district applications. ')*3
                (snap/f'ocr_augmented_text/{sid}.txt').write_text(content)
                rows.append(dict(
                    submission_id=sid,source_url='https://www.fcc.gov/ecfs/filing/'+sid,
                    date_submission='2026-10-13',filer_raw='A Filer '+sid,
                    agency_record_candidate='0',augmented_chars=len(content),
                    augmented_sha256=sha256(normalized_text(content).encode()),
                    has_unreviewed_ocr='1' if i%2==0 else '0'
                ))
            write_csv(snap/'research_inventory.csv',rows,list(rows[0]))
            result=analyze(base,'example','augmented',.87)
            self.assertEqual(result['filings_considered'],7)
            self.assertTrue(result['candidate_near_duplicate_families']>=1)
            self.assertTrue(result['filings_in_candidate_families']>=6)
            self.assertTrue((snap/'templates_augmented/near_duplicate_families.csv').is_file())
            self.assertTrue((snap/'templates_augmented/near_duplicate_candidates.csv').is_file())
            (snap/'ocr_augmented_text/100.txt').write_text('modified!')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                analyze(base,'example','augmented',.87)


if __name__=='__main__':
    unittest.main()
