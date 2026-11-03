import unittest
from research.identity_562.deep_investigation import inspect_entire_source

class DeepSourceIdentityTests(unittest.TestCase):
    def roles(self,text):
        return {x["role"] for x in inspect_entire_source(text)}

    def test_missed_deep_role(self):
        self.assertIn("school_technology_staff",self.roles(
            "Introduction about E-Rate. "*300+
            "I maintain our district network and support its upgrades."))
        self.assertIn("school_educator",self.roles(
            "My students use educational internet and I need access."))
        self.assertIn("parent_guardian",self.roles(
            "My children attend public school and use online class materials."))
        self.assertIn("library_staff",self.roles(
            "I work at our local public library and help patrons access Wi-Fi."))
    def test_policy_topic_not_role(self):
        self.assertEqual(self.roles(
            "School teachers, school district tech staff, librarians and parents "
            "all benefit from the E-Rate program. The FCC should preserve it."),set())
    def test_reference_quotes_excluded(self):
        self.assertEqual(self.roles(
            "Introduction.\nReferences\nI am a teacher at a high school."),set())
    def test_evidence_offsets(self):
        text="This proposal harms libraries.\nI rely on our local library.\n"
        marks=inspect_entire_source(text)
        self.assertTrue(marks)
        self.assertTrue(all(x['char_offset']>=0 for x in marks))

if __name__=="__main__":
    unittest.main()
