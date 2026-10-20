import unittest
from scripts.reconcile_remaining_pdfs import select_remaining_pdf_gaps


class GapSelectionTest(unittest.TestCase):
    def test_only_reconcilable_pdf_gaps_are_selected(self):
        rows=[
            {'submission_id':'777','diagnosis':'combined_text_file_missing_or_ambiguous'},
            {'submission_id':'123','diagnosis':'existing_source_text_needs_reconciliation'},
            {'submission_id':'789','diagnosis':'existing_source_text_needs_reconciliation'},
            {'submission_id':'123','diagnosis':'existing_source_text_needs_reconciliation'},
            {'submission_id':'111','diagnosis':'no_direct_text_and_no_attachments'},
        ]
        self.assertEqual(select_remaining_pdf_gaps(rows),['123','789'])


if __name__ == '__main__':
    unittest.main()
