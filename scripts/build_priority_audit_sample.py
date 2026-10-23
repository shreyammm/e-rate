#!/usr/bin/env python3
"""Deterministic stratified QA assignments: positive/negative candidate checks.

Includes clean and risky strata to reveal false negatives. Machine labels are
NOT true positive/negative verdicts; these sampling strata are just retrieval
triggers. Never estimate final prevalence without independent adjudication.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/data/kaggle/priority_position_candidates.json'
OUTPUT=ROOT/'docs/data/kaggle/priority_audit_sample.json'
SEED='erate-priority-positions-20261023-v1'
STRATA=('candidate_clean','candidate_risk','no_candidate_clean','no_candidate_risk')

def classify(f,axis):
    hit=bool(f['axes'][axis]['candidate_labels'])
    risk=bool(f.get('ocr_candidate') or f.get('model_semantic_scope')!='full_text' or
              len(f['axes'][axis]['candidate_labels'])>1 or f.get('duplicate_count',1)>1)
    return ('candidate_' if hit else 'no_candidate_')+('risk' if risk else 'clean')

def rank(axis,stratum,id):
    return hashlib.sha256((SEED+'|'+axis+'|'+stratum+'|'+id).encode()).hexdigest()

def build(src=DATA,dest=OUTPUT,per_stratum=24):
    data=json.loads(Path(src).read_text(encoding='utf-8'))
    assert data['status'].startswith('UNADJUDICATED_'), 'Cannot audit an unexpected data version'
    assert len(data['filings'])==3231
    population=[r for r in data['filings'] if r['has_source_text']]
    assert len(population)==3230
    selections=[];stratum_summary=[]
    for axis in data['axis_labels']:
        strata={k:[] for k in STRATA}
        for filing in population:strata[classify(filing,axis)].append(filing)
        assert sum(map(len,strata.values()))==3230
        for stratum,pool in strata.items():
            ordered=sorted(pool,key=lambda f:rank(axis,stratum,f['id']))
            selected=ordered[:min(per_stratum,len(ordered))]
            stratum_summary.append({'axis':axis,'stratum':stratum,'population':len(pool),
                'sampled':len(selected),
                'selection_method':'deterministic_sha256_pseudorandom_sort',
                'weight_if_probability_sample':len(pool)/len(selected) if selected else None})
            for r in selected:
                evid=r['axes'][axis]['evidence'][:2]
                selections.append({'filing_id':r['id'],'axis':axis,'stratum':stratum,
                    'filer':r['filer'],'role':r['role'],
                    'model_semantic_scope':r['model_semantic_scope'],
                    'ocr_candidate':r['ocr_candidate'],
                    'machine_candidate_labels':r['axes'][axis]['candidate_labels'],
                    'source_evidence':evid,
                    'selection_seed':SEED,
                    'review_status':'awaits_independent_source_review'})
    out={'schema_version':'priority-positions-audit-sample-v1',
        'generated_utc':datetime.now(timezone.utc).isoformat(),'source_filings':3230,
        'seed':SEED,'target_per_stratum':per_stratum,'strata':stratum_summary,
        'total_assignments':len(selections),
        'unique_filings':len({x['filing_id'] for x in selections}),
        'limitations':[
          'A sample assignment is NOT an adjudicated stance or proven misuse allegation.',
          'Both candidate-positive and candidate-negative strata are sampled to assess false positives and missed arguments.',
          'Stratum sampling weights are usable only AFTER independent source-level labels are adjudicated; no accuracy or supporter estimate is present now.',
          'At least a subset should be double-coded by a second independent reviewer, especially alleged misconduct and conflicting recommendations.',
        ],'assignments':selections}
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=DATA)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--per-stratum',type=int,default=24)
    a=parser.parse_args()
    z=build(a.input,a.output,a.per_stratum)
    print(json.dumps({'total_assignments':z['total_assignments'],
        'unique_filings':z['unique_filings'],'strata':z['strata']},indent=2))
if __name__=='__main__':main()
