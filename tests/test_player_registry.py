"""Regression tests for conservative source-grounded player identity classification."""
import unittest
from scripts.build_player_registry import (
    inferred_identity, organization_label, canon, ROLE_LABELS
)
class PlayerIdentityTest(unittest.TestCase):
    def test_institutional_school_field(self):
        x=inferred_identity({'filer_raw':'Springfield Unified School District'},
            'school_district_or_school','The E-Rate Program should continue.')
        self.assertEqual(x['role'],'school_district')
        self.assertEqual(x['basis'],'filer_field_organization')
        self.assertFalse(x['needs_review'])
    def test_named_person_not_auto_employer(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
           'A journal wrote: "As a consultant I favor this." In my letter I have a different view.')
        self.assertEqual(x['organization'],'')
        self.assertEqual(x['role'],'named_person_capacity_unstated')
        self.assertTrue(x['needs_review'])
    def test_explicit_teacher_role_in_author_intro(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
           'I am a teacher in a public school. Internet service matters.')
        self.assertEqual(x['role'],'school_educator')
        self.assertEqual(x['basis'],'author_self_description')
    def test_reference_list_not_author_identity(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
           'Dear Commission, our concerns are varied. '+'x '*1300+
           'References: As an E-Rate consultant, we support this.')
        self.assertNotEqual(x['role'],'erate_consultant')
    def test_proxy_role_not_client_stance(self):
        x=inferred_identity({'filer_raw':'Example E-Rate Services LLC'},
           'consultant_or_e_rate_services_firm',
           'On behalf of our school clients we submit this filing.')
        self.assertEqual(x['role'],'erate_consultant')
        self.assertTrue(x['speaker_is_proxy_possible'])
        self.assertTrue(x['needs_review'])
    def test_sanitize_mixed_identifiers(self):
        self.assertEqual(organization_label('Joe Smith, ABC School District'),'')
        self.assertEqual(organization_label('Jane Doe jane@example.com'),'')
    def test_distinct_org_names_do_not_merge(self):
        self.assertNotEqual(canon('Central High School'),canon('Central School District'))
        self.assertIn('unresolved',ROLE_LABELS)

    def test_ntia_is_government_with_named_source(self):
        x=inferred_identity({'filer_raw':'National Telecommunications and Information Administration'},
            'unresolved','NTIA reports what participants said at a listening session.')
        self.assertEqual(x['organization'],'National Telecommunications and Information Administration')
        self.assertEqual(x['role'],'government')
    def test_comma_legal_suffix_not_person(self):
        x=inferred_identity({'filer_raw':'Funds For Learning, LLC'},
            'consultant_or_e_rate_services_firm','We submit these comments.')
        self.assertEqual(x['organization'],'Funds For Learning, LLC')
        self.assertEqual(x['role'],'erate_consultant')
    def test_trade_association_is_not_vendor(self):
        x=inferred_identity({'filer_raw':'Software and Information Industry Association'},
            'advocacy_nonprofit_or_trade_association','We advocate for education software.')
        self.assertEqual(x['role'],'trade_association')
        self.assertEqual(x['industry_focus'],'edtech_industry')
    def test_separated_person_metadata_is_only_candidate(self):
        x=inferred_identity({'filer_raw':'Chris Warden | K12TechPro'},
            'named_person_capacity_unstated','Our organization provides technology assistance.')
        self.assertEqual(x['organization'],'')
        self.assertTrue(x['needs_review'])
    def test_affiliation_candidate_not_legal_speaker(self):
        x=inferred_identity({'filer_raw':'Jane Doe | E-Rate Funding Services LLC'},
            'named_person_capacity_unstated','My statement addresses school procurement.')
        self.assertEqual(x['organization'],'E-Rate Funding Services LLC')
        self.assertEqual(x['basis'],'multi_party_metadata_affiliation_candidate')
        self.assertTrue(x['needs_review'])

if __name__=='__main__':unittest.main()
