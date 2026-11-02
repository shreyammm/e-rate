"""Regression tests for institutional, personal, and represented-capacity identities."""
import unittest

from scripts.submitter_identity_resolution import (
    resolve_submitter, canonical_org, normalize
)


class SubmitterCapacityTests(unittest.TestCase):
    def key(self, raw, filing, **entry):
        return resolve_submitter(raw, filing, entry)[0]

    def test_repeat_individual_same_capacity_collapses(self):
        entry={'organization':'Newport School District','role':'school_technology_staff'}
        self.assertEqual(self.key('Ms. Sarah Example','1',**entry),
                         self.key('MS SARAH EXAMPLE','2',**entry))

    def test_same_individual_different_organizations_are_separate(self):
        self.assertNotEqual(
            self.key('Alex Example','1',organization='Newport School District'),
            self.key('Alex Example','2',organization='Becket Athenaeum'))

    def test_different_people_at_same_institution_are_separate(self):
        self.assertNotEqual(
            self.key('Alex Example','1',organization='Newport School District'),
            self.key('Blake Example','2',organization='Newport School District'))

    def test_person_institution_compound_and_metadata_affiliation_agree(self):
        compound=self.key('Alex Example | Newport School District','1')
        from_signature=self.key('Alex Example','2',
                                organization='Newport School District')
        self.assertEqual(compound,from_signature)

    def test_one_institution_multiple_comments_is_one_voice(self):
        self.assertEqual(
            self.key('Environmental Health Sciences','1',role='advocacy_organization',
                     organization='Environmental Health Sciences'),
            self.key('environmental health sciences','2',role='advocacy_organization',
                     organization='Environmental Health Sciences'))
        self.assertEqual(
            self.key('Funds For Learning, LLC','1',organization='Funds For Learning, LLC'),
            self.key('Funds for Learning LLC','2',organization='Funds For Learning, LLC'))

    def test_occupational_titles_are_not_identified_as_people(self):
        from scripts.submitter_identity_resolution import person_name
        self.assertEqual(person_name('Outreach Director'),'')
        self.assertEqual(person_name('Technology Coordinator'),'')
        self.assertEqual(person_name('Executive Director'),'')
        self.assertEqual(
            self.key('Outreach Director | California Brain Tumor Association','1',
                     organization='California Brain Tumor Association'),
            self.key('California Brain Tumor Association','2',
                     organization='California Brain Tumor Association'))

    def test_industry_legal_aliases_merge_when_corrob(self):
        self.assertEqual(canonical_org('AdvanEdge Solutions'),
                         canonical_org('IntelaFunds'))

    def test_placeholder_ids_dont_merge(self):
        self.assertNotEqual(self.key('Unknown','1'),self.key('Unknown','2'))
        self.assertNotEqual(self.key('Anonymous','1'),self.key('Anonymous','2'))

    def test_fake_organization_excerpt_is_ignored(self):
        suspicious='Submitted to the Federal Communications Commission’s Proposed Rule to'
        self.assertEqual(canonical_org(suspicious),'')
        self.assertEqual(canonical_org('● My children’s elementary school pays $800 a year'),'')
        self.assertEqual(self.key('Alex Example','1',organization=suspicious),
                         self.key('Alex Example','2'))

    def test_joint_institutions_remain_one_submission_not_each_party(self):
        x=self.key('Unknown cofilers','1',multi_submitter_metadata=True,
                   joint_institution_candidates=['Environmental Health Sciences',
                                                 'California Brain Tumor Association'])
        y=self.key('Different label','2',multi_submitter_metadata=True,
                   joint_institution_candidates=['California Brain Tumor Association',
                                                 'Environmental Health Sciences'])
        self.assertEqual(x,y)
        self.assertNotEqual(x,self.key('Environmental Health Sciences','3',
                                      organization='Environmental Health Sciences'))

    def test_same_name_unsafe_unknown_org_is_not_confident(self):
        _key,basis,review=resolve_submitter('Alex Example','1')
        self.assertIn('not_established',basis)
        self.assertTrue('person:' in _key)
        self.assertFalse(basis=='institution_filer_metadata')

    def test_no_unverifiable_content_similarity_identity(self):
        self.assertNotEqual(self.key('Alex Example','1'),self.key('Blake Example','2'))


if __name__=='__main__':
    unittest.main()
