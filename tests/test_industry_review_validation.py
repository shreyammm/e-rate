"""Independent-source-coding validation, including missed machine arguments."""
import unittest
from scripts.build_industry_argument_review import FIELDS
from scripts.validate_industry_argument_reviews import analyze, validate_review_row


def source(fid="123", detected=False):
    r = {k: "" for k in FIELDS}
    r.update({
        "filing_id": fid, "topic_id": "screen_policy",
        "review_assignment": "industry_complete_census",
        "stakeholder_candidate": "edtech_vendors",
        "model_candidate_status": "argument_extracted" if detected else "not_detected_by_model",
        "source_url": "https://www.fcc.gov/ecfs/filing/" + fid,
    })
    return r


def coded(original, reviewer, present="yes"):
    r = dict(original)
    r.update({
        "reviewer_id": reviewer,
        "actual_speaker": "filer",
        "argument_present_in_complete_source": present,
        "filer_endorses_argument": "yes" if present == "yes" else "not_applicable",
        "requested_fcc_action": "discussion_no_position" if present == "yes" else "not_addressed",
        "source_recheck_notes": "I inspected the full FCC submission.",
    })
    return r


class ReviewValidationTest(unittest.TestCase):
    def test_two_independent_agreements_find_a_possible_machine_miss(self):
        q = source(detected=False)
        result, diffs = analyze([q], [coded(q, "reviewer-a")], [coded(q, "reviewer-b")])
        self.assertFalse(diffs)
        self.assertEqual(result["counts"]["concordant_double_coded"], 1)
        self.assertEqual(result["counts"]["reviewed_machine_misses"], 1)
        self.assertTrue(result["all_assignments_double_coded_without_disagreement"])
        self.assertIn("NOT_APPROVED_FOR_PUBLIC_STANCE_COUNTS", result["status"])

    def test_disagreement_is_never_silently_adjudicated(self):
        q = source(detected=True)
        r = coded(q, "reviewer-b")
        r["filer_endorses_argument"] = "no"
        result, diffs = analyze([q], [coded(q, "reviewer-a")], [r])
        self.assertEqual(len(diffs), 1)
        self.assertEqual(result["counts"]["judgment_disagreements"], 1)
        self.assertFalse(result["all_assignments_double_coded_without_disagreement"])

    def test_falsified_source_metadata_is_rejected(self):
        q = source()
        r = coded(q, "reviewer-a")
        r["source_url"] = "https://not-the-actual-filing.example"
        with self.assertRaisesRegex(ValueError, "edited source"):
            validate_review_row(q, r, "reviewer-a")

    def test_incomplete_or_incoherent_human_reviews_are_rejected(self):
        q = source()
        r = coded(q, "reviewer-a", present="no")
        r["filer_endorses_argument"] = "yes"
        with self.assertRaisesRegex(ValueError, "confirmed absent"):
            validate_review_row(q, r, "reviewer-a")
        r2 = coded(q, "reviewer-a")
        r2["source_recheck_notes"] = ""
        with self.assertRaisesRegex(ValueError, "full-source check"):
            validate_review_row(q, r2, "reviewer-a")

    def test_independent_coder_ids_required(self):
        q = source()
        with self.assertRaisesRegex(ValueError, "different reviewer IDs"):
            analyze([q], [coded(q, "same")], [coded(q, "same")])

    def test_both_reviews_must_preserve_all_assignments(self):
        x, y = source("1"), source("2")
        with self.assertRaisesRegex(ValueError, "ALL queue assignments"):
            analyze([x, y], [coded(x, "a")], [coded(x, "b")])


if __name__ == "__main__":
    unittest.main()
