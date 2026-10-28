"""Tests for stakeholder and argument-counting methods; independent of model outputs."""
import unittest
from scripts.build_stakeholder_census import (
    topics_for_claim, stakeholder_group, compute, THEMES, GROUP_NAMES, NTIA_LISTENING_REPORT
)
class CensusTest(unittest.TestCase):
    def test_named_types_are_not_collapsed(self):
        self.assertEqual(stakeholder_group({'role':'edtech_learning_vendor','industry_focus':'edtech_learning'}),'edtech_vendors')
        self.assertEqual(stakeholder_group({'role':'trade_association','industry_focus':'edtech_industry'}),'edtech_trade_associations')
        self.assertEqual(stakeholder_group({'role':'erate_consultant','industry_focus':'erate_consulting'}),'erate_consultants')
        self.assertEqual(stakeholder_group({'role':'trade_association','industry_focus':'erate_consulting'}),'consultant_associations')
        self.assertEqual(stakeholder_group({'role':'school_technology_staff'}),'school_professionals')
        self.assertEqual(stakeholder_group({'role':'school_connected_unknown'}),'school_affiliation_uncertain')
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
