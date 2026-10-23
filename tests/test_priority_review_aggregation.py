"""Do not mistake auto-flags or one reviewer for validated supporters."""
import unittest
from scripts.aggregate_priority_reviews import reconcile

SOURCE={'100','200','300'}

def review(id,axis,reviewer,labels,**kw):
 return {'filing_id':id,'axis':axis,'reviewer':reviewer,'labels':';'.join(labels),
  'review_stage':'one_reviewer_only_not_validated','read_entire_source':'true',
  'chosen_source_quote':'Real source quote demonstrating the filer view',
  'source_offset':'45','explanation':'I checked the original letter and this is the filing author position.',
  'screen_harm_to_funding_condition_link':kw.get('link','not_assessed'),
  'misuse_legal_characterization':kw.get('legal','not_applicable'),
  'misuse_allegation_type':kw.get('misuse_type','not_assessed'),
  'new_condition_type':kw.get('condition','not_assessed')}

class AgreementTest(unittest.TestCase):
 def test_single_reviewer_never_becomes_counted_as_validated(self):
  d=reconcile([review('100','funding','r1',['preserve_expand'])],SOURCE)
  self.assertEqual(len(d['two_reviewer_agreements']),0)
  self.assertEqual(d['by_axis']['funding']['adjudicated_label_counts_within_reviewed_subset']['preserve_expand'],0)
  self.assertEqual(len(d['single_reviewer_cases']),1)

 def test_agreed_two_reviewers_count_only_one_filing(self):
  r=[review('100','funding','r1',['preserve_expand']),
    review('100','funding','r2',['preserve_expand'])]
  d=reconcile(r,SOURCE)
  self.assertEqual(d['by_axis']['funding']['double_reviewed_agreed_filings'],1)
  self.assertEqual(d['by_axis']['funding']['adjudicated_label_counts_within_reviewed_subset']['preserve_expand'],1)
  self.assertEqual(d['by_axis']['funding']['pending_or_disputed_vs_total_readable'],3229)

 def test_disagreement_is_not_counted(self):
  r=[review('200','funding','r1',['abolish_program']),
     review('200','funding','r2',['preserve_expand'])]
  d=reconcile(r,SOURCE)
  self.assertEqual(len(d['disputed_cases']),1)
  self.assertEqual(len(d['two_reviewer_agreements']),0)

 def test_misuse_legal_vs_normative_disagreement_is_held_out(self):
  r=[review('300','misuse','r1',['specific_allegation'],legal='alleges_illegal_or_ineligible',misuse_type='improper_billing'),
     review('300','misuse','r2',['specific_allegation'],legal='normative_objection_not_illegal',misuse_type='improper_billing')]
  d=reconcile(r,SOURCE)
  self.assertEqual(len(d['disputed_cases']),1)
  self.assertEqual(d['by_axis']['misuse']['adjudicated_label_counts_within_reviewed_subset']['specific_allegation'],0)

 def test_misuse_allegation_not_confused_with_oversight(self):
  r=[review('100','misuse','r1',['oversight_only']),
     review('100','misuse','r2',['oversight_only'])]
  d=reconcile(r,SOURCE)
  self.assertEqual(d['by_axis']['misuse']['adjudicated_label_counts_within_reviewed_subset']['specific_allegation'],0)
  self.assertEqual(d['by_axis']['misuse']['adjudicated_label_counts_within_reviewed_subset']['oversight_only'],1)

 def test_explicit_screen_harm_causation_requires_two_axis_agreements(self):
  r=[review('100','screen_harms','r1',['affirmative_harm_concern'],link='yes_explicit'),
     review('100','screen_harms','r2',['affirmative_harm_concern'],link='yes_explicit'),
     review('100','funding','r1',['targeted_restriction'],link='yes_explicit'),
     review('100','funding','r2',['targeted_restriction'],link='yes_explicit'),
     review('200','funding','r1',['targeted_restriction'],link='yes_explicit'),
     review('200','funding','r2',['targeted_restriction'],link='yes_explicit')]
  d=reconcile(r,SOURCE)
  self.assertEqual(d['screen_harm_explicitly_motivates_e_rate_restriction_or_condition']['filing_ids'],['100'])

 def test_invalid_evidence_not_released_as_verified(self):
  r=review('100','funding','r1',['preserve_expand'])
  r['chosen_source_quote']=''
  z=reconcile([r,review('100','funding','r2',['preserve_expand'])],SOURCE)
  self.assertEqual(len(z['two_reviewer_agreements']),0)
  self.assertEqual(z['excluded_review_rows']['missing_exact_evidence'],1)

if __name__=='__main__':unittest.main()
