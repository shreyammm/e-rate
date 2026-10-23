#!/usr/bin/env python3
"""Reconcile independent human review CSV exports into auditable filing counts.

This script NEVER uses the unvalidated Kaggle stance, review-candidate label,
or a single reviewer as a verified position. It publishes two-reviewer
agreement counts only for the subset actually reviewed. No population-wide
support percentages are inferred without a complete adjudication or formally
designed probability-sample analysis.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter,defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/data/kaggle/priority_position_candidates.json'
INPUT=ROOT/'data/priority_reviews'
OUT=ROOT/'docs/data/kaggle/priority_adjudicated_positions.json'
AXIS_LABELS={
 'funding':{'preserve_expand','abolish_program','targeted_restriction','conditional_or_redesign'},
 'conditions':{'favor_new_federal_condition','oppose_new_federal_condition','conditional_or_locally_controlled','existing_rules_only'},
 'screen_harms':{'affirmative_harm_concern','questions_harm_claim','acknowledges_concern_no_policy'},
 'misuse':{'specific_allegation','general_misuse_allegation','risk_or_hypothetical','oversight_only'},
}
EXTRA_FIELDS=('misuse_legal_characterization','misuse_allegation_type','screen_harm_to_funding_condition_link','new_condition_type')

def load_reviews(folder):
    entries=[]
    for p in sorted(Path(folder).glob('*.csv')):
        with p.open(newline='',encoding='utf-8-sig') as handle:
            entries.extend(list(csv.DictReader(handle)))
    return entries

def decision_key(v):
    labels=tuple(sorted(v['labels']))
    supplementary=[]
    if v['axis']=='misuse':
        supplementary.extend((v['misuse_legal_characterization'],v['misuse_allegation_type']))
    if v['axis']=='conditions':
        supplementary.append(v['new_condition_type'])
    if v['axis'] in ('funding','conditions','screen_harms'):
        supplementary.append(v['screen_harm_to_funding_condition_link'])
    return labels+('|||',)+tuple(supplementary)

def reconcile(records,eligible_ids):
    valid=[]
    excluded=Counter()
    dedup={}
    for raw in records:
        id=str(raw.get('filing_id') or '').strip()
        reviewer=str(raw.get('reviewer') or '').strip()
        axis=str(raw.get('axis') or '')
        labels=sorted(set(x.strip() for x in str(raw.get('labels') or '').split(';') if x.strip()))
        stage=str(raw.get('review_stage') or '')
        if id not in eligible_ids or axis not in AXIS_LABELS or not reviewer or not set(labels)<=AXIS_LABELS[axis]:
            excluded['unknown_filing_axis_or_code']+=1;continue
        if stage!='one_reviewer_only_not_validated' or str(raw.get('read_entire_source')).lower() not in ('true','1','yes'):
            excluded['not_fully_read_or_wrong_review_stage']+=1;continue
        if len(str(raw.get('explanation') or '').strip())<12:
            excluded['missing_review_rationale']+=1;continue
        if labels and (not str(raw.get('chosen_source_quote') or '').strip() or not str(raw.get('source_offset') or '').strip()):
            excluded['missing_exact_evidence']+=1;continue
        if axis=='misuse' and any(x in labels for x in ('specific_allegation','general_misuse_allegation')):
            if (str(raw.get('misuse_legal_characterization') or '') in ('','not_assessed')):
                excluded['missing_misuse_distinction']+=1;continue
        key=(id,axis,reviewer)
        if key in dedup:
            excluded['duplicate_reviewer_entry']+=1
            # Treat identical or conflicting duplicate row as invalid unless
            # the reviewer exports a single unambiguous final record.
            dedup[key]=None;continue
        v={'filing_id':id,'axis':axis,'reviewer':reviewer,'labels':labels,
           'explanation':str(raw.get('explanation') or '').strip(),
           'chosen_source_quote':str(raw.get('chosen_source_quote') or ''),
           'source_offset':str(raw.get('source_offset') or ''),
           **{k:str(raw.get(k) or 'not_assessed') for k in EXTRA_FIELDS}}
        dedup[key]=v
    valid=[x for x in dedup.values() if x is not None]
    by_case=defaultdict(list)
    for v in valid:by_case[v['axis'],v['filing_id']].append(v)
    agreed,disputed,once=[],[],[]
    for (axis,id),entries in sorted(by_case.items()):
        if len(entries)<2:
            once.append({'filing_id':id,'axis':axis,'reviewers':len(entries)});continue
        kinds={decision_key(v) for v in entries}
        if len(kinds)!=1:
            disputed.append({'filing_id':id,'axis':axis,'reviewers':len(entries),
                 'proposed_codes':[{'reviewer':v['reviewer'],'labels':v['labels']} for v in entries]})
            continue
        one=entries[0]
        agreed.append({'filing_id':id,'axis':axis,'labels':one['labels'],
            'reviewer_count':len(entries),
            'misuse_legal_characterization':one['misuse_legal_characterization'],
            'misuse_allegation_type':one['misuse_allegation_type'],
            'screen_harm_to_funding_condition_link':one['screen_harm_to_funding_condition_link'],
            'new_condition_type':one['new_condition_type'],
            'fcc_url':'https://www.fcc.gov/ecfs/filing/'+id,
            'status':'independent_reviewer_agreement_not_legal_finding'})
    by_axis={}
    for axis,labels in AXIS_LABELS.items():
        selected=[r for r in agreed if r['axis']==axis]
        by_axis[axis]={'double_reviewed_agreed_filings':len(selected),
            'two_reviewers_agree_no_supported_label':sum(not x['labels'] for x in selected),
            'adjudicated_label_counts_within_reviewed_subset':{
                label:sum(label in x['labels'] for x in selected) for label in sorted(labels)},
            'pending_or_disputed_vs_total_readable':3230-len(selected),
            'denominator_description':'Only the double-reviewed agreed filings are counted; NOT an estimate for all 3,230 filings'}
    screen_ids={x['filing_id'] for x in agreed if x['axis']=='screen_harms' and 'affirmative_harm_concern' in x['labels']}
    related=[]
    for x in agreed:
        if x['filing_id'] not in screen_ids or x['screen_harm_to_funding_condition_link']!='yes_explicit':continue
        if x['axis']=='funding' and ('targeted_restriction' in x['labels'] or 'abolish_program' in x['labels']):
            related.append(x['filing_id'])
        if x['axis']=='conditions' and 'favor_new_federal_condition' in x['labels']:
            related.append(x['filing_id'])
    return {'valid_input_review_rows':len(valid),'excluded_review_rows':dict(excluded),
        'single_reviewer_cases':once,'disputed_cases':disputed,'two_reviewer_agreements':agreed,
        'by_axis':by_axis,
        'screen_harm_explicitly_motivates_e_rate_restriction_or_condition':{
            'double_reviewed_linked_filings':len(set(related)),
            'filing_ids':sorted(set(related)),
            'denominator':'only source-reviewed, two-reviewer agreed intersection with explicit causal link'},
        'publication_status':'TWO_REVIEWER_AGREEMENT_SUBSET_ONLY_NO_FULL_CORPUS_PREVALENCE'}

def build(source=SOURCE,review_dir=INPUT,output=OUT):
    data=json.loads(Path(source).read_text(encoding='utf-8'))
    if data['source_records']!=3231 or data['readable_filings']!=3230:raise ValueError('Incorrect baseline')
    ids={str(x['id']) for x in data['filings'] if x['has_source_text']}
    results=reconcile(load_reviews(review_dir),ids)
    results.update({'schema_version':'priority-reviewed-agreements-v1',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'readable_corpus_filings':len(ids),
        'limitations':[
          'No full-corpus support/opposition prevalence is reported from partial reviewer coverage.',
          'Two self-declared reviewer IDs and agreement are not proof of independent review or legal adjudication.',
          'Misuse allegations in comments are assertions, NOT verified misconduct or FCC findings.',
          'Stratified sample estimates require separate sampling-weighted statistical analysis after human adjudication.',
        ]})
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(results,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return results

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--source',type=Path,default=SOURCE)
    a.add_argument('--review-dir',type=Path,default=INPUT)
    a.add_argument('--output',type=Path,default=OUT)
    args=a.parse_args()
    out=build(args.source,args.review_dir,args.output)
    print(json.dumps({'valid_rows':out['valid_input_review_rows'],
        'double_agreements':len(out['two_reviewer_agreements']),
        'disputes':len(out['disputed_cases']),
        'publication_status':out['publication_status']},indent=2))
