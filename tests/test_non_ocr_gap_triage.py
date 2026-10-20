import tempfile
import unittest
from pathlib import Path
from scripts.non_ocr_gap_triage import triage_one


class NonOcrGapTriageTest(unittest.TestCase):
    def test_link_only_original_is_retained_and_flagged(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t)
            (base/'original_documents').mkdir()
            (base/'original_documents/123_1.txt').write_text('blob:https://example.invalid/id')
            row={'submission_id':'123','source_url':'https://www.fcc.gov/ecfs/filing/123',
                 'submission_type':'COMMENT','status':'unresolved',
                 'combined_text_file_count':'1'}
            docs={'123':[{'filename':'x.txt','local_file':'original_documents/123_1.txt',
                          'text_file':'','url':''}]}
            result=triage_one(row,docs,base)
            self.assertEqual(result['diagnosis'],'original_attachment_only_temporary_blob_link')
            self.assertEqual(result['document_count'],1)
            self.assertEqual(result['originals_missing'],0)

    def test_missing_combined_text_is_explicit(self):
        with tempfile.TemporaryDirectory() as t:
            row={'submission_id':'777','source_url':'','submission_type':'COMMENT',
                 'status':'complete','combined_text_file_count':'0'}
            result=triage_one(row,{},Path(t))
            self.assertEqual(result['diagnosis'],'combined_text_file_missing_or_ambiguous')


if __name__ == '__main__':
    unittest.main()
