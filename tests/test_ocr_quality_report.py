import tempfile
import unittest
from pathlib import Path

from scripts.ocr_quality_report import inspect, select_sample


class OcrQualityReportTest(unittest.TestCase):
    def test_provenance_missing_is_not_marked_verified(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t)
            out = base / 'analysis_observatory/ocr_recovery'
            out.mkdir(parents=True)
            rec = {
                'submission_id': '123', 'document_number': '1',
                'original_path': 'original_documents/123_1.pdf',
                'status': 'completed', 'ocr_engine': 'apple_vision',
                'pages': '1', 'pages_ocr_successful': '1',
                'pages_with_text': '1', 'ocr_chars': '100',
                'text_path': 'text/123_1.txt',
                'evidence_path': 'evidence/123_1.json',
            }
            qc = inspect(rec, base, out, .8)
            self.assertEqual(qc['original_sha256_valid'], 0)
            self.assertEqual(qc['evidence_hash_valid'], 0)
            self.assertIn('original_pdf_missing', qc['quality_flags'])
            self.assertEqual(qc['review_priority'], 'high')

    def test_sample_no_duplicate_keys(self):
        rows = [
            {'submission_id': str(i), 'document_number': '1',
             'review_priority': 'high' if i % 2 else 'routine',
             'quality_flags': 'low_median_ocr_confidence' if i % 2 else '',
             'median_line_confidence': .9 if i % 2 == 0 else .7,
             'source_url': '', 'original_path': '', 'ocr_text_path': '',
             'pages': '1', 'ocr_chars': '100'}
            for i in range(30)
        ]
        sample = select_sample(rows, 12)
        self.assertEqual(len(sample), 12)
        self.assertEqual(len({(r['submission_id'], r['document_number']) for r in sample}), 12)
        self.assertEqual(select_sample(rows, 12), sample)


if __name__ == '__main__':
    unittest.main()
