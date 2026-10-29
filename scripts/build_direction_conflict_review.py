#!/usr/bin/env python3
"""Prioritize evidence-identical and issue-mixed model stance labels for review.

The word 'support' from a source-grounded model claim is NOT normalized
support for an FCC proposal. These collisions are triage leads, not verified
contradictions in commenter positions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'docs/data/kaggle/machine_claim_rows.json'
AUDIT=ROOT/'docs/data/kaggle/claim_context_audit.json'
CENSUS=ROOT/'docs/data/stakeholder_argument_census.json'
OUT=ROOT/'docs/data/kaggle/direction_conflict_review.csv'
META=ROOT/'docs/data/kaggle/direction_conflict_review_summary.json'
INDUSTRY={'edtech_vendors','edtech_trade_associations',
          'erate_consultants','consultant_associations'}
SEED='erate-machine-direction-audit-20261029-v1'
COLUMNS=[
    'review_stratum','filing_id','fcc_provision_model_issue','stakeholder_candidate',
    'role_candidate','organization_candidate','joint_filing','source_text_scope',
    'has_unreviewed_ocr','machine_support_label','machine_oppose_label',
    'support_model_action','oppose_model_action',
    'support_redacted_quote','oppose_redacted_quote',
    'support_start','oppose_start','identical_quote_and_offset',
    'fcc_url','reviewer_id','actual_fcc_provision','source_author_attribution',
    'normalized_filer_position','source_evidence_checked','explanation_of_model_label_collision',
    'review_status'
]


def seed_rank(group,filing,issue):
    return hashlib.sha256((SEED+'|'+group+'|'+filing+'|'+issue).encode()).hexdigest()


def safest(row):
    """Only previously published redacted excerpts; don't re-read PII."""
    return {key:str(row.get(key) or '') for key in ('action','quote')}


def make_queue(ledger, audit, census, max_other_per_group=12):
    if max_other_per_group<1:
        raise ValueError('Positive group sampling size required')
    if audit.get('machine_claim_ledger_sha256')!=ledger.get('_file_sha256'):
        raise ValueError('Source audit hash does not match machine ledger')
    if audit.get('coverage',{}).get('machine_claim_rows_checked')!=len(ledger['rows']):
        raise ValueError('Audit claim count mismatch')
    if len(census.get('filings',[]))!=census.get('coverage',{}).get('filings'):
        raise ValueError('Incomplete stakeholder census')
    if census.get('inputs',{}).get('machine_claim_ledger_sha256')!=ledger['_file_sha256']:
        raise ValueError('Stakeholder census and machine ledger differ')
    by_file={str(f['id']):f for f in census['filings']}
    by_issue=defaultdict(list)
    for i,record in enumerate(ledger['rows']):
        sid=str(record.get('id') or '')
        issue=str(record.get('issue') or '')
        pos=str(record.get('position') or '')
        if sid not in by_file:raise ValueError('Claim with unindexed filing ID '+sid)
        if issue not in ('','other_policy_issue') and pos in ('support','oppose'):
            by_issue[(sid,issue)].append((i,record))
    all_candidates=[]
    for (sid,issue),items in by_issue.items():
        supports=[(i,r) for i,r in items if r.get('position')=='support']
        opposes=[(i,r) for i,r in items if r.get('position')=='oppose']
        if not supports or not opposes:continue
        overlap=sorted({(r.get('start'),str(r.get('quote') or '')) for _,r in supports}&
                       {(r.get('start'),str(r.get('quote') or '')) for _,r in opposes},
                       key=lambda x:(str(x[0]),x[1]))
        same=bool(overlap)
        if same:
            key=overlap[0]
            first=next(x for x in supports if (x[1].get('start'),str(x[1].get('quote') or ''))==key)
            second=next(x for x in opposes if (x[1].get('start'),str(x[1].get('quote') or ''))==key)
        else:
            first=min(supports,key=lambda x:(x[1].get('start',0),x[0]))
            second=min(opposes,key=lambda x:(x[1].get('start',0),x[0]))
        f=by_file[sid]
        x={
            'filing_id':sid,'fcc_provision_model_issue':issue,
            'stakeholder_candidate':f.get('group',''),
            'role_candidate':f.get('role',''),
            'organization_candidate':f.get('organization',''),
            'joint_filing':bool(f.get('joint_filing')),
            'source_text_scope':f.get('quality_scope',''),
            'has_unreviewed_ocr':bool(f.get('ocr_candidate')),
            'machine_support_label':'support','machine_oppose_label':'oppose',
            'support_model_action':str(first[1].get('action') or '')[:240],
            'oppose_model_action':str(second[1].get('action') or '')[:240],
            'support_redacted_quote':str(first[1].get('quote') or '')[:320],
            'oppose_redacted_quote':str(second[1].get('quote') or '')[:320],
            'support_start':first[1].get('start'),'oppose_start':second[1].get('start'),
            'identical_quote_and_offset':same,
            'fcc_url':'https://www.fcc.gov/ecfs/filing/'+sid,
        }
        x.update({k:'' for k in COLUMNS if k not in x and k!='review_stratum'})
        all_candidates.append(x)

    selected=[];other_by_group=defaultdict(list)
    by_case={}
    for x in all_candidates:
        key=(x['filing_id'],x['fcc_provision_model_issue'])
        if key in by_case:raise ValueError('Duplicate filing issue case')
        by_case[key]=x
        if x['identical_quote_and_offset']:
            x['review_stratum']='identical_span_conflicting_machine_labels'
            selected.append(x)
        elif x['stakeholder_candidate'] in INDUSTRY:
            x['review_stratum']='industry_issue_mixed_machine_labels'
            selected.append(x)
        else:
            other_by_group[x['stakeholder_candidate']].append(x)
    strata=[]
    for group,rows in sorted(other_by_group.items()):
        chosen=sorted(rows,key=lambda x:seed_rank(group,x['filing_id'],x['fcc_provision_model_issue']))[:max_other_per_group]
        for x in chosen:
            x['review_stratum']='group_stratified_other_mixed_issue'
        selected.extend(chosen)
        strata.append({'stakeholder_group':group,'population':len(rows),
                       'selected':len(chosen),
                       'selection':'deterministic_pseudorandom_filing_issue_pairs',
                       'weight_if_adjudicated':len(rows)/len(chosen) if chosen else None})
    selected.sort(key=lambda x:(x['review_stratum'],x['stakeholder_candidate'],
                                x['filing_id'],x['fcc_provision_model_issue']))
    stats=Counter(x['review_stratum'] for x in selected)
    count_exact=sum(x['identical_quote_and_offset'] for x in all_candidates)
    known=audit.get('machine_direction_consistency',{})
    # A single filing+issue may contain multiple exact-span collisions.
    # This queue counts filing/issue cases while the audit counts source spans.
    if known and count_exact>known.get('identical_source_spans_with_opposing_machine_labels',0):
        raise ValueError('Conflicting model spans exceed the source-matched audit')
    summary={
        'schema':'machine-direction-conflict-review-v1',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'source_machine_ledger_sha256':ledger['_file_sha256'],
        'source_census_registry_sha256':census.get('inputs',{}).get('player_registry_sha256',''),
        'status':'UNREVIEWED_MACHINE_LABEL_AMBIGUITIES',
        'filing_issue_pairs_with_both_machine_labels':len(all_candidates),
        'same_span_case_count':count_exact,
        'cases_selected_for_review':len(selected),
        'review_strata':dict(stats),'other_group_sampling':strata,
        'machine_context_audit_summary':known,
        'limitations':[
            'Support/oppose are unverified LLM action labels, NOT opposing positions on one normalized FCC proposal.',
            'Opposite machine labels on identical evidence may describe one consistent preference using positive and negative wording.',
            'A mixed filing/issue may contain different subproposals or genuine conditional views; read the complete FCC filing.',
            'Selected comparator cases are a reproducible sample and may not support inference without independent adjudication.',
        ],
    }
    return selected,summary


def export(ledger_path=LEDGER,audit_path=AUDIT,census_path=CENSUS,
           output=OUT,meta=META,max_other_per_group=12):
    lp=Path(ledger_path);raw=lp.read_bytes();ledger=json.loads(raw)
    ledger['_file_sha256']=hashlib.sha256(raw).hexdigest()
    rows,stats=make_queue(ledger,json.loads(Path(audit_path).read_text()),
                          json.loads(Path(census_path).read_text()),max_other_per_group)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    def cell(v):
        s=str(v if v is not None else '')
        return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
    with output.open('w',encoding='utf-8',newline='') as file:
        w=csv.DictWriter(file,fieldnames=COLUMNS);w.writeheader()
        for row in rows:w.writerow({k:cell(row.get(k,'')) for k in COLUMNS})
    meta=Path(meta);meta.parent.mkdir(parents=True,exist_ok=True)
    meta.write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {k:stats[k] for k in ('status','filing_issue_pairs_with_both_machine_labels',
                  'same_span_case_count','cases_selected_for_review','review_strata')}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ledger',type=Path,default=LEDGER)
    p.add_argument('--audit',type=Path,default=AUDIT)
    p.add_argument('--census',type=Path,default=CENSUS)
    p.add_argument('--output',type=Path,default=OUT)
    p.add_argument('--summary',type=Path,default=META)
    p.add_argument('--per-other-group',type=int,default=12)
    a=p.parse_args()
    print(json.dumps(export(a.ledger,a.audit,a.census,a.output,a.summary,a.per_other_group),indent=2))

if __name__=='__main__':main()
