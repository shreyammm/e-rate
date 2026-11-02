"""Explicit occupational self-description regression tests.

A generic discussion of a stakeholder must not be treated as authorship.
"""
import unittest
from scripts.identity_context_resolver import context_capacity


class ExtendedIdentityCapacityTest(unittest.TestCase):
    def test_explicit_self_descriptions(self):
        examples = {
            "I'm a district chief information officer, and we need connectivity.": "school_technology_staff",
            "I work in our school technology department.": "school_technology_staff",
            "I serve on our school board and am writing about E-Rate.": "school_administrator",
            "I'm an assistant principal at a public school.": "school_administrator",
            "I'm a special education teacher.": "school_educator",
            "I work as a school counselor.": "school_educator",
            "I'm a library assistant and I use this program.": "library_staff",
            "I work as a library media specialist.": "library_staff",
            "I provide E-Rate consulting services to local districts.": "erate_consultant",
        }
        for comment, role in examples.items():
            with self.subTest(comment=comment):
                self.assertEqual(context_capacity(comment).role, role)

    def test_topic_reference_is_not_identity(self):
        comments = (
            "School counselors and librarians should be consulted.",
            "The proposal could affect E-Rate consultants.",
            "The district chief information officer said costs would rise.",
            "According to a special education teacher, the program is useful.",
        )
        for comment in comments:
            with self.subTest(comment=comment):
                self.assertEqual(context_capacity(comment).role, "")


if __name__ == "__main__":
    unittest.main()
