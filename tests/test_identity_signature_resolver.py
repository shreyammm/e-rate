"""Regression tests for evidence-only signature, email-domain and terminal titles."""
import unittest
from scripts.identity_signature_resolver import signature_signal, domain_sector
from scripts.build_player_registry import inferred_identity


class SignatureIdentityTest(unittest.TestCase):
    def test_school_domain_in_real_closing(self):
        t = ("This comment discusses E-Rate oversight.\n"
             "Best regards,\nJane Doe\njane@maple.k12.or.us")
        s = signature_signal(t, "Jane Doe")
        self.assertEqual(s.role, "school_connected_unknown")
        self.assertEqual(s.basis, "signature_institutional_email_domain")
        x = inferred_identity({"filer_raw":"Jane Doe"},
            "named_person_capacity_unstated", t)
        self.assertEqual(x["role"], "school_connected_unknown")
        self.assertTrue(x["attribution_review"])
        self.assertFalse(x["needs_review"])
        self.assertEqual(x["organization"], "")

    def test_library_domain_at_close(self):
        t = "I am concerned about continued access.\nWarm regards,\nJane Doe\njane@fox.library.org"
        x = inferred_identity({"filer_raw":"Jane Doe"},
            "named_person_capacity_unstated", t)
        self.assertEqual(x["role"], "library_affiliated")
        self.assertEqual(x["organization"], "")

    def test_title_no_closing_but_named_signer(self):
        t = ("Please protect E-Rate connectivity.\n\n"
             "Jane Doe\nDistrict E-Rate Coordinator\njane@maple.k12.or.us")
        x = inferred_identity({"filer_raw":"Jane Doe"},
            "named_person_capacity_unstated", t)
        self.assertEqual(x["role"], "school_technology_staff")
        self.assertEqual(x["basis"], "terminal_signature_job_title")

    def test_title_in_colon_fields(self):
        t = "We rely on these connections.\nRegards,\nJane Doe\nTitle: Library Technician"
        self.assertEqual(signature_signal(t, "Jane Doe").role, "library_staff")

    def test_false_positive_topic_or_quote(self):
        t = ("Director of Technology discusses E-Rate.\n"
             "The hearing referenced a sample email at example.k12.ca.us.\n"
             "The author thinks this is important.")
        s = signature_signal(t, "Jane Doe")
        self.assertFalse(s.role)
        self.assertEqual(inferred_identity({"filer_raw":"Jane Doe"},
             "named_person_capacity_unstated", t)["role"],
             "named_person_capacity_unstated")

    def test_false_positive_reference_and_unmatched_name(self):
        t = ("This matters.\nReferences\nJane Doe\n"
             "District E-Rate Coordinator\njane@maple.k12.or.us")
        self.assertEqual(signature_signal(t, "Jane Doe").role, "")

    def test_no_generic_email_domain_speaker_inference(self):
        for email in ("jane@gmail.com", "jane@alumni.edu",
                      "jane@consultants.com", "jane@example.org"):
            with self.subTest(email=email):
                t = "Sincerely,\nJane Doe\n" + email
                self.assertEqual(signature_signal(t, "Jane Doe").role, "")

    def test_parent_priority_over_school_domain(self):
        t = ("As a parent, my child needs reliable access.\n"
             "Sincerely,\nJane Doe\njane@maple.k12.or.us")
        x = inferred_identity({"filer_raw":"Jane Doe"},
            "named_person_capacity_unstated", t)
        self.assertEqual(x["role"], "parent_guardian")

    def test_organization_filer_not_retyped_from_personal_signature(self):
        t = ("Please modernize the program.\nSincerely,\n"
             "Jane Doe\njane@maple.k12.or.us")
        x = inferred_identity({"filer_raw":"Cisco Systems, Inc."},
            "other_business_or_vendor", t)
        self.assertEqual(x["role"], "network_technology_vendor")

    def test_conflicting_domains_abstain(self):
        s = signature_signal("Regards,\nJane Doe\njane@my.library.org\njane@town.schools.org",
                             "Jane Doe")
        self.assertEqual(s.role, "")

    def test_another_persons_signoff_must_not_be_attributed_to_filer(self):
        t = ("The original filer submits through their counsel.\n"
             "Sincerely,\nAlex Roe\nalex@town.k12.ca.us")
        self.assertEqual(signature_signal(t, "Jane Doe").role, "")

    def test_generic_edu_or_gov_does_not_assume_role(self):
        self.assertEqual(domain_sector("university.edu"), "")
        self.assertEqual(domain_sector("gov.gov"), "")
        self.assertEqual(domain_sector("some.k12.tx.us"), "school_connected_unknown")


if __name__ == "__main__":
    unittest.main()
