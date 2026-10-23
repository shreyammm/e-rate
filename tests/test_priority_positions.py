"""Tests ensure priority analysis NEVER turns keywords into verified positions."""
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_priority_positions import AXES,build_one,build


class PriorityPositionTests(unittest.TestCase):
    def sample(self,text,claims=None):
        sha=hashlib.sha256(text.encode('utf-8')).hexdigest()
        d={'submission_id':'1234','status':'complete','filer_raw':'Example school',
           'source_sha256':sha,'semantic_scope':'full_text',
           'claims':claims or []}
        return build_one('1234',text,d,{'role':'school','organization':'Example school','date':'2026-10-01'})

    def test_misuse_never_a_proven_violation(self):
        text='As a parent I object to E-Rate taxpayer funds being misused on inappropriate school Wi-Fi hotspots.'
        v=self.sample(text)
        axis=v['axes']['misuse']
        self.assertIn('general_misuse_allegation',axis['candidate_labels'])
        self.assertEqual(axis['review_status'],'not_adjudicated')
        self.assertTrue(axis['flagged_as_allegation_candidate'])
        self.assertIn('no finding of misconduct',axis['caution'])
        self.assertTrue(any(e['start']>=0 for e in axis['evidence']))

    def test_sunset_budget_diversion_is_not_misconduct_allegation(self):
        text=('If E-Rate is eliminated, schools will be forced to divert scarce '
              'funds from classroom priorities to internet service costs.')
        v=self.sample(text)
        self.assertNotIn('specific_allegation',v['axes']['misuse']['candidate_labels'])
        self.assertNotIn('general_misuse_allegation',v['axes']['misuse']['candidate_labels'])

    def test_explicit_negated_waste_claim_is_not_allegation(self):
        text=('There are so many federal programs that are a waste of money; '
              "E-Rate isn't one of them. We support the E-Rate program.")
        v=self.sample(text)
        self.assertNotIn('specific_allegation',v['axes']['misuse']['candidate_labels'])
        self.assertNotIn('general_misuse_allegation',v['axes']['misuse']['candidate_labels'])

    def test_preventing_possible_ineligible_mibs_not_specific_accusation(self):
        text=('The FCC should prevent MIBS from being used to bundle '
              'ineligible equipment into future E-Rate contracts.')
        v=self.sample(text)
        self.assertNotIn('specific_allegation',v['axes']['misuse']['candidate_labels'])

    def test_prevention_is_not_a_verified_allegation(self):
        text='We favor stronger fraud prevention and program integrity to avoid potential waste of E-Rate resources.'
        v=self.sample(text)
        self.assertIn('oversight_only',v['axes']['misuse']['candidate_labels'])
        self.assertEqual(v['axes']['misuse']['review_status'],'not_adjudicated')

    def test_continuation_and_sunset_false_polarity_remain_candidates(self):
        text='We urge the Commission to continue E-Rate funding. We oppose a proposal to sunset E-Rate.'
        v=self.sample(text)
        self.assertIn('preserve_expand',v['axes']['funding']['candidate_labels'])
        # A sunset mention in opposed/quoted text might still trigger; it must
        # not be counted as someone endorsing abolition.
        self.assertEqual(v['axes']['funding']['review_status'],'not_adjudicated')

    def test_distinct_screen_concern_and_funding_condition(self):
        text='Excessive screen time damages learning and attention. However, federal blanket screen mandates would be unworkable; we favor local discretion.'
        v=self.sample(text)
        self.assertIn('affirmative_harm_concern',v['axes']['screen_harms']['candidate_labels'])
        self.assertIn('conditional_or_locally_controlled',v['axes']['conditions']['candidate_labels'])
        self.assertEqual(v['axes']['conditions']['review_status'],'not_adjudicated')

    def test_machine_stance_ignored_and_offsets_required(self):
        source='We urge the FCC to maintain E-Rate funding as currently authorized.'
        quote='maintain E-Rate funding'
        offset=source.index(quote)
        claim={'provision_id':'erate_sunset','position':'support',
               'requested_action':'maintain E-Rate funding',
               'argument':'The program should continue',
               'evidence_quote':quote,'evidence_start':offset}
        v=self.sample(source,[claim])
        self.assertIn('preserve_expand',v['axes']['funding']['candidate_labels'])
        self.assertEqual(v['axes']['funding']['review_status'],'not_adjudicated')
        matching=[e for e in v['axes']['funding']['evidence'] if e['origin']=='kaggle_claim_model_action']
        self.assertTrue(matching)
        self.assertEqual(matching[0]['start'],offset)
        self.assertTrue(all(axis['review_status']=='not_adjudicated' for axis in v['axes'].values()))

    def test_full_corpus_record_coverage_with_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            src=base/'corpus';(src/'shards').mkdir(parents=True)
            models=base/'filings';models.mkdir()
            index=base/'index.json'
            records=[{'id':'1234','role':'school','organization':'Example school'},
                     {'id':'5678','role':'library','organization':'Example library'}]
            index.write_text(json.dumps({'filings':records}))
            rows=[]
            for sid,txt in [('1234','Maintain E-Rate funding.'),('5678','Screen time causes concern.')]:
                checksum=hashlib.sha256(txt.encode()).hexdigest()
                rows.append({'submission_id':sid,'text':txt,'text_sha256':checksum})
                (models/(sid+'.json')).write_text(json.dumps({
                    'status':'complete','submission_id':sid,'source_sha256':checksum,
                    'claims':[],'semantic_scope':'full_text'}))
            zipped=src/'shards'/'part.jsonl.gz'
            with gzip.open(zipped,'wt',encoding='utf-8') as fh:
                for row in rows:fh.write(json.dumps(row)+'\n')
            (src/'manifest.json').write_text(json.dumps({
                'records':2,'records_with_text':2,
                'shards':[{'name':'part.jsonl.gz','sha256':hashlib.sha256(zipped.read_bytes()).hexdigest()}]}))
            result=build(models,src,index,base/'result.json',strict=False)
            self.assertEqual(result['source_records'],2)
            self.assertEqual(result['readable_filings'],2)
            self.assertTrue(all(a['review_status']=='not_adjudicated'
                  for row in result['filings'] for a in row['axes'].values()))
            self.assertEqual(set(result['axis_labels']),set(AXES))


if __name__=='__main__':
    unittest.main()
