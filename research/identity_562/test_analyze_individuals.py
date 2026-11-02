import unittest
from scripts.identity_context_resolver import context_capacity
from research.identity_562.analyze_individuals import declared_roles, normalize_template, shingles

class ExperimentalIdentityTests(unittest.TestCase):
    def check(self, text, role):
        self.assertIn(role, [x.role for x in declared_roles(text)])

    def test_declared_affiliations(self):
        samples = {
          "As a library patron I rely on public access.": "library_patron",
          "I use our public library for internet access.": "library_patron",
          "As a taxpayer, I support accountable use of funds.": "taxpayer",
          "I live in a rural community and have limited broadband.": "community_resident",
          "As a school board member, I understand our budget.": "school_administrator",
          "I am a retired teacher and care about learning.": "retired_educator",
          "I am a high-schooler and internet access is critical.": "student",
          "I work in our public school district.": "school_employee_general",
          "I own an E-Rate consulting firm helping applicants.": "erate_consultant",
          "My grandson uses the school library.": "parent_guardian",
          "Our children attend schools that use E-Rate.": "parent_guardian",
          "Our library provides broadband to residents.": "library_community_connection",
          "Our school's internet access is essential.": "school_community_connection",
          "As an E-Rate applicant I know the paperwork.": "erate_applicant_voice",
          "I volunteer at our public library.": "community_volunteer",
          "I am a researcher studying education policy.": "researcher",
          "I am a school IT director.": "school_technology_staff",
          "As a professional librarian I see the benefit.": "library_staff",
          "As a high school teacher, I want E-Rate preserved.": "school_educator",
          "I have just retired in June from teaching elementary school for 28 years.": "retired_educator",
          "As an IT Professional at a Catholic School in Marlborough, I see firsthand its importance.": "school_technology_staff",
          "Currently, I am a member of the BOE at my district.": "school_board_member",
          "I have been in education for over 20 years, starting in the classroom.": "education_professional",
          "I am a licensed psychologist in private practice.": "health_professional",
          "I have been a homeschool parent for 20 years.": "parent_guardian",
          "Screen time is affecting our children, in 2nd and 3rd grade, who are required to use tablets.": "parent_guardian",
          "My family has used our library services many times.": "library_patron",
          "We need wifi at the library to be able to do homework.": "library_patron",
          "The E-Rate program saves my library money and time allowing us to serve our residents.": "library_community_connection",
        }
        for text, role in samples.items():
            with self.subTest(text=text):
                self.check(text, role)

    def test_topic_mentions_not_author(self):
        cases=[
          "Teachers and school board members should review this rule.",
          "The FCC asks about parents, students and librarians.",
          "Some tax payers say we should eliminate E-Rate.",
          "The letter discusses school administrators and broadband."
        ]
        for x in cases:
            with self.subTest(x=x):
                self.assertFalse(declared_roles(x), x)

    def test_references_not_author(self):
        x=("This filing raises an issue.\nReferences\n"
           "I am an E-Rate consultant employed by a school.\n")
        self.assertEqual(declared_roles(x),[])

    def test_template_trivial_letters_not_clustered(self):
        self.assertFalse(shingles(normalize_template("Keep E-Rate, please.")))
        self.assertFalse(shingles(normalize_template("")))

    def test_existing_context_role_supported(self):
        self.assertEqual(context_capacity("As a parent I support school internet").role,"parent_guardian")

if __name__=="__main__":
    unittest.main()
