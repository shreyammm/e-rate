"""Tests for stakeholder and argument-counting methods; independent of model outputs."""
import unittest
from scripts.build_stakeholder_census import (
    topics_for_claim, stakeholder_group, compute, THEMES, GROUP_NAMES, NTIA_LISTENING_REPORT
)
class CensusTest(unittest.TestCase):
    def test_detailed_role_counts_are_exposed(self):
        import inspect
        source=inspect.getsource(compute)
        self.assertIn("'by_detailed_role':role_cells",source)
        self.assertIn("'pct_of_topic_filings'",source)
        self.assertIn("'distinct_source_texts'",source)
    def test_census_statistics_include_unique_named_institutions(self):
        import inspect
        source=inspect.getsource(compute)
        self.assertIn("'named_institutions'",source)
        self.assertIn("'pct_of_coded_group_filings'",source)
    def test_observed_model_label_confusions_against_actual_checkpoints(self):
        import json
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        def claim(filing, phrase):
            rows=json.loads((root/'data/llm_census_kaggle/filings'/
                             (filing+'.json')).read_text())['claims']
            found=[c for c in rows if phrase.lower() in
                   str(c.get('requested_action') or '').lower()]
            self.assertTrue(found, f'No source-linked checkpoint action {filing}: {phrase}')
            c=found[0]
            return {'issue':c.get('provision_id'),'action':c.get('requested_action'),
                    'argument':c.get('argument')}
        false=[
            ('26110079965','maintain consultant participation in bidding portal','consultant_fees'),
            ('26110080495','maintain predictable support','administrative_burden'),
            ('26110074471','maintain educational','learning_outcomes'),
            ('26110038512','revise consultant','consultant_registration'),
            ('26110038512','reject capping reseller markups','vendor_influence')
        ]
        for fid,phrase,theme in false:
            with self.subTest(source=fid,theme=theme):
                self.assertNotIn(theme,topics_for_claim(claim(fid,phrase)))
        true=[
            ('26110079965','file ACCD only','consultant_reporting'),
            ('26110079965','require mandatory annual','consultant_qualifications'),
            ('26110081267','allow percentage','consultant_fees'),
            ('26110081267','treat consulting firm','consultant_registration')
        ]
        for fid,phrase,theme in true:
            with self.subTest(source=fid,theme=theme):
                self.assertIn(theme,topics_for_claim(claim(fid,phrase)))
    def test_narrow_consultant_issue_labels_require_substantive_claim_text(self):
        bad=[
            ('consultant_form_5654','Abandon the individual Form 479 requirement for school consortium members.',
             'More CIPA documentation for consortium members is burdensome.','consultant_reporting'),
            ('consultant_registration','Scale new consultant oversight requirements to reduce burdens.',
             'Consultant regulation should be proportional, especially for small applicants.','consultant_registration'),
            ('consultant_percent_fees','Maintain consultant participation in the bidding portal.',
             'Consultants will remain essential to applicants when procurement rules change.','consultant_fees'),
            ('administrative_forms','Maintain predictable E-Rate support.',
             'Schools plan their network upgrades years in advance.','administrative_burden'),
            ('education_outcomes','Preserve the educational-purpose presumption.',
             'This legal presumption should not be reversed.','learning_outcomes'),
            ('vendor_influence','Reject price caps on reseller markups.',
             'Caps may reduce competition among broadband suppliers.','vendor_influence')
        ]
        for issue,action,argument,theme in bad:
            with self.subTest(issue=issue,theme=theme):
                self.assertNotIn(theme,topics_for_claim({
                    'issue':issue,'action':action,'argument':argument}))
    def test_actual_fee_disclosure_and_registration_actions_still_detected(self):
        cases=[
            ('consultant_percent_fees','Permit percentage-based consultant fee arrangements.','consultant_fees'),
            ('consultant_form_5654','Require annual Form 5654 filing by consultants.','consultant_reporting'),
            ('consultant_registration','Maintain a consultant registration and CRN registry.','consultant_registration'),
            ('consultant_definition','Define which persons count as E-Rate consultants.','consultant_definition'),
            ('education_outcomes','Improve student academic achievement with instructional technology.','learning_outcomes'),
            ('vendor_influence','Require disclosure of vendor influence and conflicts of interest.','vendor_influence'),
        ]
        for issue,action,theme in cases:
            with self.subTest(theme=theme):
                self.assertIn(theme,topics_for_claim({'issue':issue,'action':action,
                    'argument':'The filing recommends the stated action.'}))
    def test_consultant_filing_certificate_not_professional_qualification(self):
        x=topics_for_claim({'issue':'consultant_form_5654',
            'action':'Require annual consultant certification and disclosure Form 5654.',
            'argument':'A reporting form helps regulators check compliance.'})
        self.assertIn('consultant_reporting',x)
        self.assertNotIn('consultant_qualifications',x)
    def test_advanced_consultant_distinctions(self):
        x=topics_for_claim({'issue':'other_policy_issue','action':'Require independent consultants to disclose consultant conflicts of interest and vendor payments.',
           'argument':'Consultants paid by vendors risk recommending the vendor that compensates them.'})
        self.assertIn('consultant_independence',x)
        y=topics_for_claim({'issue':'other_policy_issue','action':'Improve consultant training and consultant qualifications.',
           'argument':'Consultant credentials would professionalize E-Rate program services.'})
        self.assertIn('consultant_qualifications',y)
        z=topics_for_claim({'issue':'other_policy_issue','action':'Permit consulting expertise for small districts.',
           'argument':'Consultants help applicants understand and complete the program.'})
        self.assertIn('consultant_value',z)
    def test_edtech_evidence_subthemes(self):
        a=topics_for_claim({'issue':'other_policy_issue','action':'Evaluate peer-reviewed research.',
           'argument':'Research shows that educational technology improves math outcomes.'})
        self.assertIn('edtech_study_evidence',a)
        b=topics_for_claim({'issue':'other_policy_issue','action':'Support adaptive learning systems.',
           'argument':'Personalized instruction can tailor content to student needs.'})
        self.assertIn('adaptive_learning',b)
        c=topics_for_claim({'issue':'other_policy_issue','action':'Limit school device deployments.',
           'argument':'Device management raises school IT administrative concerns.'})
        self.assertIn('device_management',c)
    def test_fees_do_not_imply_independence_or_specific_misuse(self):
        x=topics_for_claim({'issue':'consultant_percent_fees','action':'Limit percentage-based consultant fees.',
           'argument':'A fee tied to the funding award can raise total applicant costs.'})
        self.assertIn('consultant_fees',x)
        self.assertNotIn('consultant_independence',x)
        self.assertNotIn('alleged_misuse',x)
    def test_stale_context_audit_never_implies_low_risk(self):
        import inspect
        source=inspect.getsource(compute)
        self.assertIn('not audit_match or possible_voice_issue',source)
    def test_named_types_are_not_collapsed(self):
        self.assertEqual(stakeholder_group({'role':'edtech_learning_vendor','industry_focus':'edtech_learning'}),'edtech_vendors')
        self.assertEqual(stakeholder_group({'role':'trade_association','industry_focus':'edtech_industry'}),'edtech_trade_associations')
        self.assertEqual(stakeholder_group({'role':'erate_consultant','industry_focus':'erate_consulting'}),'erate_consultants')
        self.assertEqual(stakeholder_group({'role':'trade_association','industry_focus':'erate_consulting'}),'consultant_associations')
        self.assertEqual(stakeholder_group({'role':'school_technology_staff'}),'school_professionals')
        self.assertEqual(stakeholder_group({'role':'school_connected_unknown'}),'school_affiliation_uncertain')
        self.assertEqual(stakeholder_group({'role':'school_connected_unknown','multi_submitter_metadata':True}),'joint_institutional_filings')
    def test_issue_not_automatically_direction(self):
        x=topics_for_claim({'issue':'erate_sunset','position':'support','action':'Protect the program against cuts',
                            'argument':'Schools need E-Rate connectivity.'})
        self.assertIn('program_continuity',x)
        self.assertNotIn('alleged_misuse',x)
    def test_nonassertion_not_counted(self):
        self.assertEqual(topics_for_claim({'issue':'cipa_byod','position':'discussion_no_position',
                 'action':'none','argument':'The filing does not address school personal device requirements.'}),[])
    def test_fraud_allegation_vs_general_oversight(self):
        x=topics_for_claim({'issue':'other_policy_issue','action':'Improve routine program integrity oversight.',
                            'argument':'Conduct annual compliance audits to prevent future waste.'})
        self.assertIn('program_integrity',x)
        self.assertNotIn('alleged_misuse',x)
        y=topics_for_claim({'issue':'other_policy_issue','action':'Investigate a documented fraud incident.',
                            'argument':'The school alleges misuse of a particular grant.'})
        self.assertIn('alleged_misuse',y)
    def test_screen_condition_without_harm_not_claimed_as_health_harm(self):
        x=topics_for_claim({'issue':'screen_time_condition','action':'Keep decisions about screens local.',
                            'argument':'Schools should make screen-time policy decisions.'})
        self.assertNotIn('screen_harms',x)
    def test_privacy_preserving_is_not_erate_program_continuity(self):
        # Rego filing 26110081077 -- an unrelated privacy-preserving proposal.
        x=topics_for_claim({'issue':'cipa_age_specific',
           'action':'establish a technology-neutral safe harbor for privacy-preserving age and parental assurance credentials',
           'argument':'A safe harbor would allow schools to rely on limited, privacy-preserving age and parental assurances rather than collecting full identity data.'})
        self.assertNotIn('program_continuity',x)
    def test_performance_criteria_are_not_forms_and_admin_costs(self):
        x=topics_for_claim({'issue':'other_policy_issue',
            'action':'define performance, privacy, security, interoperability and accountability criteria for assurance methods',
            'argument':'Rego proposes that the Commission define criteria for assurance methods.'})
        self.assertNotIn('administrative_burden',x)
    def test_certification_qualification_is_not_erate_service_eligibility(self):
        x=topics_for_claim({'issue':'cipa_age_specific',
            'action':'Certify multiple assurance providers based on outcome-based standards',
            'argument':'Certification should focus on accuracy, privacy, and interoperability, allowing multiple vendors to qualify.'})
        self.assertNotIn('eligibility_rules',x)
    def test_opposing_limits_is_not_alleging_screen_harm(self):
        # OverDrive filing 26110081293: educational reading use, not a harm allegation.
        x=topics_for_claim({'issue':'education_outcomes',
            'action':'recognize E-Rate-funded networks as essential for learning and not subject to screen-time limits',
            'argument':'Students use E-Rate-funded Wi-Fi to read books and conduct research, which is core educational activity.'})
        self.assertNotIn('screen_harms',x)
        self.assertIn('screen_policy',x)
        self.assertIn('learning_outcomes',x)
    def test_explicit_developmental_harm_is_a_distinct_theme(self):
        x=topics_for_claim({'issue':'screen_time_condition',
            'action':'Require limits on excessive screen time.',
            'argument':'Students face developmental harms from excessive screen time.'})
        self.assertIn('screen_harms',x)
        self.assertIn('screen_policy',x)
    def test_explicit_erate_continuation_is_still_detected(self):
        x=topics_for_claim({'issue':'other_policy_issue',
            'action':'preserve E-Rate funding',
            'argument':'Schools depend on preserving the E-Rate program.'})
        self.assertIn('program_continuity',x)
    def test_virtual_school_parental_choice_is_not_uncategorized(self):
        # Stride: parents know best and seek choice of virtual school options.
        x=topics_for_claim({'issue':'other_policy_issue',
            'action':'preserve virtual school options',
            'argument':'Stride opposes rules limiting virtual school options. Parents should retain the right to choose virtual education for their children.'})
        self.assertIn('parent_choice',x)
        self.assertNotIn('program_continuity',x)
    def test_nonbreaking_hyphen_screen_time_limits(self):
        # OverDrive's actual model action uses a U+2011 nonbreaking hyphen.
        x=topics_for_claim({'issue':'education_outcomes',
            'action':'recognize E‑Rate‑funded networks as essential for learning and not subject to screen‑time limits',
            'argument':'Students read books through E‑Rate networks for educational purposes.'})
        self.assertIn('screen_policy',x)
        self.assertNotIn('screen_harms',x)
    def test_en_and_em_dash_variants_normalize(self):
        from scripts.build_stakeholder_census import normalized_interpretation
        self.assertEqual(normalized_interpretation('E‑Rate – screen‐time'), 'E-Rate - screen-time')
    def test_complete_denominator_and_ntia_listening_exclusion(self):
        ids=['26110081266','26110081358','26110080790']
        ids+=['27'+str(i).zfill(9) for i in range(3228)]
        roles=[
          {'role':'government','industry_focus':'unspecified','organization':'NTIA'},
          {'role':'edtech_learning_vendor','industry_focus':'edtech_learning','organization':'Curriculum Associates, LLC'},
          {'role':'edtech_virtual_school_vendor','industry_focus':'edtech_virtual_school','organization':'Stride, Inc.'}
        ]
        records=[]
        for i,fid in enumerate(ids):
            role=roles[i] if i<3 else {'role':'unresolved','industry_focus':'unspecified','organization':''}
            records.append({'id':fid,'text_sha256':str(i//2),'basis':'test','needs_review':False,
                 'proxy_possible':False,'multi_submitter_metadata':False,
                 'submitter_field_components':1,**role})
        def row(fid,action,argument,issue='education_outcomes',start=0):
            return {'id':fid,'action':action,'argument':argument,'quote':'We make an explicit recommendation here.',
                'issue':issue,'position':'support','start':start}
        ledger={'source_filings':3231,'rows':[
             row('26110081266','Support educational technology.','Learning outcomes improve.'),
             row('26110081358','Continue instructional technology.','School learning outcomes improve.'),
             row('26110081358','Use new instructional tools.','School academic achievement improves.',start=101),
             row('26110080790','Preserve virtual learning.','Student learning opportunities matter.')
        ]}
        quality={'coverage':{'processed_readable_filings':3230},
                 'filings':{fid:{'semantic_scope':'full_text'} for fid in ids[:3]}}
        result=compute({'filings':records},ledger,quality)
        self.assertEqual(result['coverage']['filings'],3231)
        self.assertEqual(result['coverage']['excluded_reported_listening_claim_rows'],1)
        x=next(t for t in result['topics'] if t['id']=='learning_outcomes')
        self.assertEqual(x['by_stakeholder']['edtech_vendors']['filings'],2)
        self.assertEqual(x['by_stakeholder']['government']['filings'],0)
        self.assertEqual(x['filings'],2)
        self.assertEqual(sum(g['filings'] for g in result['stakeholder_groups']),3231)
        self.assertEqual(next(f for f in result['filings'] if f['id']=='26110081358')['topics'][0]['claim_count'],2)
    def test_theme_ids_unique_and_all_groups_named(self):
        self.assertEqual(len({t[0] for t in THEMES}),len(THEMES))
        self.assertIn('edtech_vendors',GROUP_NAMES)

if __name__=='__main__':unittest.main()
