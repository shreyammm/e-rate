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
        self.assertEqual(x['identity_status'],'capacity_not_stated')
        self.assertFalse(x['needs_review'])
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
        self.assertTrue(x['attribution_review'])
        self.assertFalse(x['needs_review'])
    def test_sanitize_mixed_identifiers(self):
        self.assertEqual(organization_label('Joe Smith, ABC School District'),'')
        self.assertEqual(organization_label('Jane Doe jane@example.com'),'')
    def test_policy_slogan_or_document_title_is_not_an_organization(self):
        self.assertEqual(organization_label(
            "Ensuring Children’s Safe Use of Screens and E-Rate-Funded Services."),"")
        self.assertEqual(organization_label(
            "Strengthening Broadband Access for Schools and Libraries"),"")
        # Real institutional suffixes and names remain available.
        self.assertEqual(organization_label("Example Technology Services LLC"),
                         "Example Technology Services LLC")
        self.assertEqual(organization_label("Funds For Learning, LLC"),
                         "Funds For Learning, LLC")

    def test_distinct_org_names_do_not_merge(self):
        self.assertNotEqual(canon('Central High School'),canon('Central School District'))
        self.assertIn('unresolved',ROLE_LABELS)

    def test_mentioning_consultant_rules_does_not_make_filer_a_consultant(self):
        for name in ('Daniel Rice','David Smith'):
            x=inferred_identity({'filer_raw':name},
                'consultant_or_e_rate_services_firm',
                'We should consider consultant oversight without reducing E-Rate.')
            self.assertEqual(x['role'],'named_person_capacity_unstated')
            self.assertFalse(x['needs_review'])
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
        self.assertTrue(x['attribution_review'])
        self.assertFalse(x['needs_review'])
        self.assertEqual(x['identity_confidence'],'medium')

    def test_review_queue_prioritizes_possible_representatives(self):
        x=inferred_identity({'filer_raw':'Jane Doe | E-Rate Funding Services LLC'},
            'named_person_capacity_unstated','On behalf of our school client, we recommend procurement reforms.')
        priority=review_priority(x,'On behalf of our school client, we recommend procurement reforms.')
        self.assertEqual(priority['level'],'not_required')
        self.assertTrue(x['attribution_review'])
        self.assertFalse(x['needs_review'])
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
                self.assertEqual(x['identity_confidence'],'high')
                self.assertFalse(x['needs_review'])
    def test_school_employee_signature_at_end_resolves_role_and_affiliation(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
            'Dear Commissioners,\nThe E-Rate program helps our students.\n'
            'Respectfully submitted,\nJane Doe\nDirector of Technology\n'
            'Riverton Unified School District\n')
        self.assertEqual(x['role'],'school_technology_staff')
        self.assertEqual(x['organization'],'Riverton Unified School District')
        self.assertEqual(x['basis'],'signed_role_and_organization')
        self.assertFalse(x['needs_review'])

    def test_school_signature_org_without_title_recovers_institution(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
            'Please protect our library connectivity.\nSincerely,\n'
            'Jane Doe\nFranklin Public Library\n')
        self.assertEqual(x['role'],'library_institution')
        self.assertEqual(x['organization'],'Franklin Public Library')
        self.assertFalse(x['needs_review'])

    def test_opening_letterhead_recovers_school(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
            'Riverton Unified School District\n'
            'October 12\nDear Commission, we support broadband funding.')
        self.assertEqual(x['role'],'school_district')
        self.assertEqual(x['organization'],'Riverton Unified School District')
        self.assertFalse(x['needs_review'])

    def test_company_filing_tech_signature_does_not_turn_into_school_staff(self):
        x=inferred_identity({'filer_raw':'Cisco Systems, Inc.'},'other_business_or_vendor',
            'We recommend continuing Category 2 funding.\n'
            'Respectfully submitted,\nJane Doe\nDirector of Technology\nCisco Systems, Inc.')
        self.assertEqual(x['role'],'network_technology_vendor')
        self.assertFalse(x['needs_review'])

    def test_generic_advocacy_phrase_not_assumed_proxy_client(self):
        x=inferred_identity({'filer_raw':'Springfield Unified School District'},
            'school_district_or_school',
            'On behalf of students and parents, we request sustained internet access.')
        self.assertFalse(x['speaker_is_proxy_possible'])
        self.assertFalse(x['needs_review'])

    def test_consultant_representing_client_still_needs_attribution_check(self):
        x=inferred_identity({'filer_raw':'Example E-Rate Services LLC'},
            'consultant_or_e_rate_services_firm',
            'On behalf of our school clients we ask for simpler requirements.')
        self.assertEqual(x['role'],'erate_consultant')
        self.assertTrue(x['speaker_is_proxy_possible'])
        self.assertTrue(x['attribution_review'])
        self.assertFalse(x['needs_review'])

    def test_quoted_consultant_reference_not_self_identification(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
            'We are submitting this comment to improve E-Rate integrity.\n'
            'References:\nAccording to a consultant registration study, '
            'E-Rate providers face new rules.')
        self.assertEqual(x['role'],'named_person_capacity_unstated')
        self.assertEqual(x['identity_confidence'],'not_established')
        self.assertFalse(x['needs_review'])

    def test_explicit_but_unparsed_affiliation_clue_is_reviewable(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
            'I work for a local education nonprofit and would like to comment on E-Rate.')
        self.assertTrue(x['needs_review'])
        self.assertEqual(x['identity_review_reason'],'capacity_clue_without_role')

    def test_parent_taxpayer_context(self):
        x=inferred_identity({'filer_raw':'Lisa Cline'},'named_person_capacity_unstated',
            'I wish to supply comments regarding E-Rate. As a taxpayer and a parent, '
            'I object to Wi-Fi hotspots.')
        self.assertEqual(x['role'],'parent_guardian')
        self.assertFalse(x['needs_review'])

    def test_library_first_person_affiliation_without_employment_claim(self):
        x=inferred_identity({'filer_raw':'Stephen Lackey'},'named_person_capacity_unstated',
            'Our library is their broadband. Our library provides internet service to residents.')
        self.assertEqual(x['role'],'library_affiliated')
        self.assertFalse(x['needs_review'])
        self.assertEqual(x['identity_confidence'],'medium')

    def test_school_first_person_affiliation_without_specific_job(self):
        x=inferred_identity({'filer_raw':'John Doe'},'school_district_or_school',
            'Our district serves 2,000 students. E-Rate connectivity is vital.')
        self.assertEqual(x['role'],'school_connected_unknown')
        self.assertEqual(x['identity_status'],'source_inferred')
        self.assertFalse(x['needs_review'])

    def test_school_affiliation_from_source_role_census_also_no_manual_review(self):
        x=inferred_identity({'filer_raw':'John Doe'},'school_district_or_school',
            'We believe broadband is essential.')
        self.assertEqual(x['role'],'school_connected_unknown')
        self.assertEqual(x['identity_confidence'],'medium')
        self.assertFalse(x['needs_review'])

    def test_parent_with_signed_school_role_is_primarily_school_staff(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
            'As a parent I value classroom connectivity.\nSincerely,\n'
            'Jane Doe\nDirector of Technology\nRiverton School District')
        self.assertEqual(x['role'],'school_technology_staff')
        self.assertFalse(x['needs_review'])

    def test_elite_fund_verified_erate_consultancy(self):
        x=inferred_identity({'filer_raw':'Elite Fund Inc'},'other_business_or_vendor',
            'We assist schools with E-Rate procurement.')
        self.assertEqual(x['role'],'erate_consultant')
        self.assertFalse(x['needs_review'])

    def test_adtec_organization_external_e_rate_identity(self):
        for name in ['AdTec', 'AdTec E-Rate Administrative and Technical Consulting']:
            with self.subTest(name=name):
                x=inferred_identity({'filer_raw':name},'unresolved',
                    'We provide E-Rate support to schools and libraries.')
                self.assertEqual(x['role'],'erate_consultant')
                self.assertEqual(x['industry_focus'],'erate_consulting')
                self.assertFalse(x['needs_review'])

    def test_generic_parent_policy_discussion_not_personal_parent(self):
        x=inferred_identity({'filer_raw':'Jane Doe'},'named_person_capacity_unstated',
            'Parents should be able to opt students out of screen use.')
        self.assertEqual(x['role'],'named_person_capacity_unstated')

    def test_joint_education_professional_associations_are_not_school_staff(self):
        from scripts.build_player_registry import joint_education_associations
        names=("Massachusetts Computer Using Educators | "
               "Massachusetts Educational Technology Administrators Association | "
               "Massachusetts Association of School Superintendents")
        self.assertTrue(joint_education_associations(names))
        self.assertFalse(joint_education_associations(
            "Massachusetts Educational Technology Administrators Association | "
            "Riverton Unified School District"))
        self.assertFalse(joint_education_associations(
            "Jane Doe | Springfield Unified School District"))

    def test_parent_reference_to_my_children(self):
        x=inferred_identity({'filer_raw':'Nicole Lewis'},'named_person_capacity_unstated',
            'I live in an economically diverse district whose public schools are '
            'educating my children. E-Rate is critical.')
        self.assertEqual(x['role'],'parent_guardian')
        self.assertFalse(x['needs_review'])

    def test_school_network_technician_first_person(self):
        x=inferred_identity({'filer_raw':'Camden McCroskey'},'named_person_capacity_unstated',
            "As a network technician for a local school district serving a "
            "disadvantaged area, I've seen firsthand what E-Rate does.")
        self.assertEqual(x['role'],'school_technology_staff')
        self.assertFalse(x['needs_review'])

    def test_library_language_our_library_will(self):
        x=inferred_identity({'filer_raw':'Lisa Melone'},'named_person_capacity_unstated',
            'The library cannot operate without internet. If E-Rate funding ends, '
            'our library will be forced to cut vital services.')
        self.assertEqual(x['role'],'library_affiliated')
        self.assertFalse(x['needs_review'])

    def test_school_affiliation_in_our_district(self):
        x=inferred_identity({'filer_raw':'Dr. Josh Oster'},'named_person_capacity_unstated',
            'If E-Rate ends districts will pay more. In our district that would '
            'increase the budget burden.')
        self.assertEqual(x['role'],'school_connected_unknown')
        self.assertFalse(x['needs_review'])

    def test_monterey_supervisor_first_person_role(self):
        x=inferred_identity({'filer_raw':'Supervisor Chris Lopez'},'named_person_capacity_unstated',
            'I represent the Third District of the Monterey County Board of Supervisors.')
        self.assertEqual(x['role'],'government')
        self.assertFalse(x['needs_review'])

    def test_known_institution_abbreviation(self):
        for raw,role in [('Coastline ROP','school_district'),
                         ('Wireline Competition Bureau','government')]:
            with self.subTest(raw=raw):
                x=inferred_identity({'filer_raw':raw},'named_person_capacity_unstated',
                    'We submit comments to the FCC.')
                self.assertEqual(x['role'],role)
                self.assertFalse(x['needs_review'])

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


    def test_named_library_association_is_not_library_system(self):
        x=inferred_identity({'filer_raw':'American Library Association'},
            'library_or_library_system','Our members are public libraries.')
        self.assertEqual(x['role'],'trade_association')
        y=inferred_identity({'filer_raw':'American Association of People with Disabilities'},
            'advocacy_nonprofit_or_trade_association','We advocate for accessible services.')
        self.assertEqual(y['role'],'advocacy_organization')

    def test_source_typing_edge_cases_from_registry_diff(self):
        x=inferred_identity({'filer_raw':'Minnesota Association of Charter Schools'},
            'school_district_or_school','Our association submits comments on E-Rate.')
        self.assertEqual(x['role'],'trade_association')
        x=inferred_identity({'filer_raw':'Santa Rosa County District Schools'},
            'school_district_or_school','Our school system submits comments.')
        self.assertEqual(x['role'],'school_district')
        x=inferred_identity({'filer_raw':'Saint Regis Sch District 1 A.K.A. St Regis K-12 Schools'},
            'school_district_or_school','Our district submits comments.')
        self.assertEqual(x['role'],'school_district')
        x=inferred_identity({'filer_raw':'Tel/Logic Inc. dba E-Rate Central'},
            'consultant_or_e_rate_services_firm','We help schools obtain E-Rate funding.')
        self.assertEqual(x['role'],'erate_consultant')
        self.assertEqual(x['organization'],'Tel/Logic Inc. dba E-Rate Central')
        x=inferred_identity({'filer_raw':'C/W MARS Member Libraries'},
            'library_or_library_system','Public libraries need internet access.')
        self.assertEqual(x['organization'],'C/W MARS Member Libraries')
        self.assertEqual(organization_label('school'), '')

if __name__=='__main__':unittest.main()
