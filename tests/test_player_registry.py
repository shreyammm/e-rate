"""Regression tests for conservative source-grounded player identity classification."""
import unittest
from scripts.build_player_registry import (
    inferred_identity, organization_label, canon, ROLE_LABELS, review_priority
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

    def test_mentioning_consultant_rules_does_not_make_filer_a_consultant(self):
        for name in ('Daniel Rice','David Smith'):
            x=inferred_identity({'filer_raw':name},
                'consultant_or_e_rate_services_firm',
                'We should consider consultant oversight without reducing E-Rate.')
            self.assertEqual(x['role'],'unresolved')
            self.assertTrue(x['needs_review'])
    def test_self_identified_individual_consultant_is_preserved(self):
        x=inferred_identity({'filer_raw':'Alex Doe'},
            'consultant_or_e_rate_services_firm',
            'I am an E-Rate consultant working with several small districts.')
        self.assertEqual(x['role'],'erate_consultant')
        self.assertEqual(x['basis'],'author_self_description')
        self.assertEqual(x['organization'],'')
    def test_telecom_company_mentioning_consultants_remains_telecom(self):
        x=inferred_identity({'filer_raw':'Alaska Power & Telephone'},
            'consultant_or_e_rate_services_firm',
            'The FCC should adjust consultant reporting requirements.')
        self.assertEqual(x['role'],'telecom_isp')
        self.assertEqual(x['organization'],'Alaska Power & Telephone')
    def test_named_hwc_consulting_entity_still_detected(self):
        x=inferred_identity({'filer_raw':'HWC Consultants'},
            'consultant_or_e_rate_services_firm',
            'We oppose limits on percentage-based consultant compensation.')
        self.assertEqual(x['role'],'erate_consultant')
        self.assertEqual(x['organization'],'HWC Consultants')
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

    def test_review_queue_prioritizes_possible_representatives(self):
        x=inferred_identity({'filer_raw':'Jane Doe | E-Rate Funding Services LLC'},
            'named_person_capacity_unstated','On behalf of our school client, we recommend procurement reforms.')
        priority=review_priority(x,'On behalf of our school client, we recommend procurement reforms.')
        self.assertEqual(priority['level'],'high')
        self.assertIn('possible_representative_client_relationship',priority['reasons'])
    def test_known_agency_not_unnecessarily_reviewed(self):
        x=inferred_identity({'filer_raw':'National Telecommunications and Information Administration'},
            'unresolved','This summary records public listening session statements.')
        self.assertEqual(review_priority(x,'text')['level'],'not_required')

    def test_named_business_subtypes_are_candidate_not_verified(self):
        for name,role,industry in [
            ('Curriculum Associates, LLC','edtech_learning_vendor','edtech_learning'),
            ('Stride, Inc.','edtech_virtual_school_vendor','edtech_virtual_school'),
            ('OverDrive, Inc.','edtech_digital_content_vendor','edtech_digital_content'),
            ('Rego Payment Architectures, Inc.','edtech_age_privacy_vendor','child_privacy_technology'),
            ('Cisco Systems, Inc.','network_technology_vendor','network_equipment'),
            ('Extreme Networks, Inc.','network_technology_vendor','network_equipment'),
            ('Zayo Group, LLC','telecom_isp','telecom_service'),
            ('CSM Consulting, Inc.','erate_consultant','erate_consulting'),
            ('Grant Consulting Services LLC','erate_consultant','erate_consulting')]:
            with self.subTest(name=name):
                x=inferred_identity({'filer_raw':name},'other_business_or_vendor','We submit comments.')
                self.assertEqual((x['role'],x['industry_focus']),(role,industry))
                self.assertEqual(x['basis'],'curated_company_type_candidate')
                self.assertTrue(x['needs_review'])
    def test_co_signers_not_inferred_as_independent_filings(self):
        from scripts.build_player_registry import submitted_by_multiple_entities
        x=submitted_by_multiple_entities('A School District | Curriculum Associates, LLC | Library Association')
        self.assertTrue(x['multi_submitter_metadata'])
        self.assertEqual(x['submitter_field_components'],3)
        self.assertFalse(submitted_by_multiple_entities('Curriculum Associates, LLC')['multi_submitter_metadata'])
        self.assertFalse(submitted_by_multiple_entities('Steve Potash | OverDrive, Inc.')['multi_submitter_metadata'])
        x=submitted_by_multiple_entities(
            "Prince George's County Memorial Library System | "
            "Software & Information Industry Association | Curriculum Associates")
        self.assertTrue(x['multi_submitter_metadata'])
        self.assertIn('Software and Information Industry Association',x['joint_institution_candidates'])
        self.assertIn('Curriculum Associates, LLC',x['joint_institution_candidates'])
        self.assertEqual(x['submitter_field_components'],3)
        self.assertFalse(any('Steve Potash' in x for x in x['joint_institution_candidates']))


    def test_school_filers_not_mistyped_as_commercial_firms(self):
        for name,expected in [
            ('Rensselaer Central Schools Corporation','school_district'),
            ('Columbia Gorge Education Service District','school_district'),
            ('Regional School Unit 22','school_district'),
            ('School City of Whiting','school_district'),
            ('Warren County Schools District','school_district'),
            ('International School of Brooklyn','individual_school'),
            ('Rudolf Steiner School','individual_school'),
            ('Saint Mary Catholic School','individual_school')
        ]:
            with self.subTest(name=name):
                self.assertEqual(inferred_identity(
                    {'filer_raw':name},'school_district_or_school','Our school depends on broadband.'
                )['role'],expected)

    def test_professional_associations_and_state_agencies_are_not_schools(self):
        for name,role in [
            ('National School Boards Association','trade_association'),
            ('New York State School Boards Association','trade_association'),
            ('State E-Rate Coordinators\u0027 Alliance','trade_association'),
            ('National Alliance for Public Charter Schools','advocacy_organization'),
            ('New York State Education Department','government')
        ]:
            with self.subTest(name=name):
                got=inferred_identity({'filer_raw':name},'unresolved','We submit these comments.')
                self.assertEqual(got['role'],role)
                self.assertNotEqual(got['industry_focus'],'erate_consulting')

    def test_mixed_person_and_school_labels_abstain_for_privacy(self):
        for name in ('Aaron Weston; Oley Valley School District',
                     'Holmes County School Board/Melissa Baxley',
                     'Jane Doe / Eastern School District'):
            with self.subTest(name=name):
                self.assertEqual(organization_label(name),'')
                got=inferred_identity({'filer_raw':name},
                    'school_district_or_school','Broadband matters.')
                self.assertEqual(got['organization'],'')
                self.assertTrue(got['needs_review'])

if __name__=='__main__':unittest.main()
