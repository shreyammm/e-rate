import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from erate.engine import sha256, write_csv
from scripts.build_research_snapshot import build, clean_passage, count_duplicates

FILE_FIELDS=['submission_id','date_submission','submission_type','filers','text_data_chars',
             'document_count','documents_downloaded','documents_extracted','status','issues','source_url']
DOC_FIELDS=['submission_id','document_number','filename','url','local_file','sha256',
            'http_status','file_status','text_file','text_chars','extraction_status','error']


class ResearchSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)/'corpus'
        for part in ['direct_text','combined_text','original_documents',
                     'attachment_text','analysis_observatory/ocr_recovery/text',
                     'analysis_observatory/ocr_recovery/evidence']:
            (self.base/part).mkdir(parents=True,exist_ok=True)
        filings=[]
        for sid,direct,ndocs,status in [('111','We support E-Rate for rural schools',1,'complete'),
                                        ('112','',1,'complete'),
                                        ('113','',1,'unresolved'),
                                        ('114','Library broadband helps people',0,'complete')]:
            filings.append(dict(submission_id=sid,date_submission='2026-10-13T00:00:00Z',
                submission_type='COMMENT',filers='Filer '+sid,text_data_chars=str(len(direct)),
                document_count=str(ndocs),documents_downloaded=str(ndocs),documents_extracted=str(ndocs),
                status=status,issues='',source_url='https://www.fcc.gov/ecfs/filing/'+sid))
            if direct:
                (self.base/f'direct_text/{sid}.txt').write_text(direct+'\n')
                (self.base/f'combined_text/{sid}.txt').write_text(
                    f'===== FCC DIRECT TEXT {sid} =====\n'+direct)
        (self.base/'combined_text/112.txt').write_text(
            '===== FCC ATTACHMENT 112/1 =====\nno text found')
        docs=[];records=[]
        for sid in ['111','112']:
            original=b'%PDF generated fixture '+sid.encode()
            raw=Path(f'original_documents/{sid}_1.pdf')
            (self.base/raw).write_bytes(original)
            old=Path(f'attachment_text/{sid}_1.txt')
            (self.base/old).write_text('no text found')
            docs.append(dict(submission_id=sid,document_number='1',filename='letter.pdf',
                url=f'https://www.fcc.gov/ecfs/document/{sid}/1',local_file=str(raw),
                sha256=sha256(original),http_status='',file_status='downloaded',text_file=str(old),
                text_chars='13',extraction_status='embedded_text',error=''))
            text=f'===== OCR PAGE 1 =====\nOCR content of filing {sid}: schools need reliable access.\n'
            transcript=Path(f'text/{sid}_1.txt')
            evidence=Path(f'evidence/{sid}_1.json')
            root=self.base/'analysis_observatory/ocr_recovery'
            (root/transcript).write_text(text)
            (root/evidence).write_text(json.dumps(dict(
                original_sha256=sha256(original),ocr_text_sha256=sha256(text.encode()),
                ocr_method_version='1.0')))
            records.append(dict(submission_id=sid,document_number='1',
                status='completed',ocr_engine='apple_vision',ocr_method_version='1.0',
                original_sha256=sha256(original),text_path=str(transcript),
                evidence_path=str(evidence),pages='1',pages_ocr_successful='1'))
        blob=b'blob:https://example.invalid/token'
        (self.base/'original_documents/113_1.txt').write_bytes(blob)
        (self.base/'attachment_text/113_1.txt').write_bytes(blob)
        docs.append(dict(submission_id='113',document_number='1',filename='bad.txt',
            url='https://www.fcc.gov/ecfs/document/113/1',
            local_file='original_documents/113_1.txt',sha256=sha256(blob),http_status='',
            file_status='downloaded',text_file='attachment_text/113_1.txt',
            text_chars=str(len(blob)),extraction_status='link_only_no_substantive_text',error=''))
        write_csv(self.base/'filings_manifest.csv',filings,FILE_FIELDS)
        write_csv(self.base/'documents_manifest.csv',docs,DOC_FIELDS)
        write_csv(self.base/'analysis_observatory/ocr_recovery/run_manifest.csv',
                  records,list(records[0]))

    def test_snapshot_creates_both_views_with_provenance(self):
        before=(self.base/'documents_manifest.csv').read_bytes()
        result=build(self.base,'test_a')
        self.assertEqual(result['indexed_filings'],4)
        self.assertEqual(result['baseline_filings_with_text'],2)
        self.assertEqual(result['augmented_filings_with_text'],3)
        self.assertEqual(result['ocr_attachment_candidates_included'],2)
        self.assertEqual(result['filings_metadata_only_even_with_ocr'],1)
        self.assertEqual(result['human_verified_ocr_documents'],0)
        dest=self.base/'analysis_observatory/research_snapshot_test_a'
        self.assertFalse((dest/'baseline_text/112.txt').exists())
        self.assertTrue((dest/'ocr_augmented_text/112.txt').exists())
        self.assertNotIn('===== OCR PAGE', (dest/'ocr_augmented_text/112.txt').read_text())
        self.assertNotIn('no text found',(dest/'ocr_augmented_text/112.txt').read_text())
        self.assertFalse((dest/'ocr_augmented_text/113.txt').exists())
        with (dest/'source_segments.csv').open(newline='') as f:
            rows=list(csv.DictReader(f))
        ocr_rows=[r for r in rows if r['source_kind']=='ocr_candidate_apple_vision']
        self.assertEqual(len(ocr_rows),2)
        self.assertTrue(all(x['included_baseline']=='0' and
                            x['review_status']=='ocr_candidate_not_human_verified'
                            and x['included_augmented']=='1' for x in ocr_rows))
        self.assertEqual((self.base/'documents_manifest.csv').read_bytes(),before)
        with self.assertRaises(FileExistsError):
            build(self.base,'test_a')

    def test_bad_original_hash_aborts_and_preserves_sources(self):
        (self.base/'original_documents/111_1.pdf').write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
            build(self.base,'hash_failure')
        self.assertFalse((self.base/'analysis_observatory/research_snapshot_hash_failure').exists())

    def test_script_help_runs_from_outside_repository(self):
        # Regression: invoking scripts/foo.py makes scripts/ sys.path[0],
        # so it must explicitly add the repository root before local imports.
        script = Path(__file__).resolve().parents[1] / 'scripts/build_research_snapshot.py'
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        with tempfile.TemporaryDirectory() as other_directory:
            result = subprocess.run(
                [sys.executable, str(script), '--help'],
                cwd=other_directory, env=env, text=True, capture_output=True,
                timeout=20, check=False
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--run-id', result.stdout)

    def test_wrapper_cleaning_and_duplicate_hashing(self):
        self.assertEqual(clean_passage('===== OCR PAGE 2 =====\nDo not repeal the rule.'),
                         'Do not repeal the rule.')
        self.assertEqual(clean_passage('===== FCC ATTACHMENT 123/1 =====\nno text found'),'')
        self.assertEqual(clean_passage('blob:https://example.invalid/uuid'),'')
        results=count_duplicates([
            {'hash':'abc'},{'hash':'abc'},{'hash':'def'},{'hash':''}
        ],'hash')
        self.assertEqual(results['exact_duplicate_clusters'],1)
        self.assertEqual(results['filings_in_exact_duplicate_clusters'],2)


if __name__=='__main__':
    unittest.main()
