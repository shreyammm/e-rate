import unittest
from scripts.ocr_review_packet import keys_for_review, safe_fcc_link


class ReviewPacketTest(unittest.TestCase):
    def test_sample_includes_priority_first_without_duplicate(self):
        sample = [{'submission_id': '1', 'document_number': '1'},
                  {'submission_id': '2', 'document_number': '1'}]
        qc = [{'submission_id': '2', 'document_number': '1', 'review_priority': 'high'},
              {'submission_id': '3', 'document_number': '2', 'review_priority': 'high'}]
        self.assertEqual(keys_for_review(sample, qc, 4, False),
                         [('2','1'), ('3','2'), ('1','1')])
        self.assertEqual(keys_for_review(sample, qc, 4, True),
                         [('2','1'), ('3','2')])

    def test_rejects_untrusted_urls(self):
        self.assertEqual(safe_fcc_link('https://www.fcc.gov/ecfs/document/123/1'),
                         'https://www.fcc.gov/ecfs/document/123/1')
        self.assertEqual(safe_fcc_link('javascript:alert(1)'), '')
        self.assertEqual(safe_fcc_link('https://www.fcc.gov.evil.org/ecfs/document/123/1'), '')


if __name__ == '__main__':
    unittest.main()
