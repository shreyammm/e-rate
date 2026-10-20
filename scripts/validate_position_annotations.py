#!/usr/bin/env python3
"""Validate and count manually adjudicated provision-specific filing positions.

NEVER treats keyword candidates, proposed model labels, or unreviewed OCR as
verified stances. Human annotation input remains private and is never published.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv, normalized_text, sha256, write_csv

POSITIONS={'support','oppose','conditional_or_amend','alternative_proposal',
           'discussion_no_position','unclear','not_addressed'}
NEEDS_QUOTE={'support','oppose','conditional_or_amend','alternative_proposal','discussion_no_position'}
STATUSES={'adjudicated','manual_reviewed'}
RESULT_FIELDS=['submission_id','provision_id','position','requested_action','rationale',
               'reason_families','stakeholder_role','stakeholder_evidence',
               'evidence_quote','evidence_start','evidence_end','source_url',
               'coder_id','review_status','text_view','ocr_candidate','source_text_sha256','notes']
ERROR_FIELDS=['row_number','submission_id','provision_id','error_codes']


def analyze(corpus: Path, annotated_file: Path, snapshot_id='ocr_candidate_v1',
            view='augmented') -> dict:
    base=corpus.expanduser().resolve()
    snap=base/'analysis_observatory'/f'research_snapshot_{snapshot_id}'
    book=json.loads((Path(__file__).resolve().parents[1]/'analysis_methods/provision_codebook_v1.json').read_text())
    pids={p['id'] for p in book['provisions']}
    source=snap/('ocr_augmented_text' if view=='augmented' else 'baseline_text')
    inventory,_=read_csv(snap/'research_inventory.csv')
    by_id={r['submission_id']:r for r in inventory}
    rows,_=read_csv(annotated_file.expanduser().resolve())
    out=snap/f'policy_analysis_{view}'
    out.mkdir(parents=True,exist_ok=True)
    errors=[];approved=[];seen=set();rejected=Counter()
    for no,r in enumerate(rows,start=2):
        sid=r.get('submission_id','');pid=r.get('provision_id','')
        position=r.get('position','');status=r.get('review_status','')
        problem=[]
        if (sid,pid) in seen:problem.append('duplicate_filing_provision')
        seen.add((sid,pid))
        if sid not in by_id:problem.append('unknown_filing')
        if pid not in pids:problem.append('unknown_provision')
        if position not in POSITIONS:problem.append('invalid_position')
        if status not in STATUSES:problem.append('not_human_reviewed')
        if not r.get('coder_id','').strip():problem.append('missing_coder')
        quote=r.get('evidence_quote','').strip()
        if position in NEEDS_QUOTE and not quote:problem.append('missing_evidence')
        if position in {'support','oppose','conditional_or_amend','alternative_proposal'}:
            if not r.get('requested_action','').strip():problem.append('missing_requested_action')
            if not r.get('rationale','').strip():problem.append('missing_rationale')
        start=end=None;content='';hash_value=''
        if sid in by_id:
            path=source/f'{sid}.txt'
            if path.is_file():
                content=path.read_text(encoding='utf-8-sig').strip()
                hash_value=sha256(normalized_text(content).encode())
                if hash_value!=by_id[sid][f'{view}_sha256']:problem.append('source_hash_mismatch')
            elif position!='not_addressed':
                problem.append('missing_source_text')
            if quote:
                match_positions=[m.start() for m in re.finditer(re.escape(quote),content)]
                if len(match_positions)!=1:problem.append('evidence_not_unique_or_absent_in_source')
                else:start=match_positions[0];end=start+len(quote)
            elif position=='not_addressed' and not r.get('notes','').strip():
                problem.append('not_addressed_requires_document_review_note')
        if problem:
            errors.append({'row_number':no,'submission_id':sid,'provision_id':pid,
                           'error_codes':';'.join(sorted(set(problem)))})
            for x in set(problem):rejected[x]+=1
            continue
        approved.append({
            'submission_id':sid,'provision_id':pid,'position':position,
            'requested_action':r.get('requested_action',''),
            'rationale':r.get('rationale',''),
            'reason_families':r.get('reason_families',''),
            'stakeholder_role':r.get('stakeholder_role','unknown') or 'unknown',
            'stakeholder_evidence':r.get('stakeholder_evidence',''),
            'evidence_quote':quote,
            'evidence_start':start if start is not None else '',
            'evidence_end':end if end is not None else '',
            'source_url':by_id[sid]['source_url'],'coder_id':r['coder_id'],
            'review_status':status,'text_view':view,
            'ocr_candidate':by_id[sid]['has_unreviewed_ocr'],
            'source_text_sha256':hash_value,'notes':r.get('notes','')
        })
    write_csv(out/'validated_positions.csv',approved,RESULT_FIELDS)
    write_csv(out/'position_validation_errors.csv',errors,ERROR_FIELDS)
    summary={
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'annotated_rows':len(rows),'valid_human_reviews':len(approved),
        'invalid_or_unreviewed_rows':len(errors),'distinct_reviewed_filings':len({r['submission_id'] for r in approved}),
        'distinct_provisions_reviewed':len({r['provision_id'] for r in approved}),
        'position_counts_in_reviewed_rows':dict(Counter(r['position'] for r in approved)),
        'rejection_reasons':dict(rejected),
        'critical_caveat':'Counts are restricted to the manually reviewed subset. They are NOT population or corpus-wide position percentages. Unreviewed filings and non-matches cannot be counted as oppose or not_addressed.',
        'human_ocr_review_status':'OCR source flag is retained; coding does not independently certify OCR quality.'
    }
    (out/'position_validation_summary.json').write_text(
        json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--annotations',type=Path,required=True,help='Private CSV written by human coder; never the generated queue')
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--view',choices=['baseline','augmented'],default='augmented')
    a=p.parse_args()
    print(json.dumps(analyze(a.corpus,a.annotations,a.snapshot_id,a.view),indent=2))


if __name__=='__main__':main()
