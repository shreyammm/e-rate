#!/usr/bin/env python3
"""Validate distinct human-coded arguments separately from filing-level positions.

One filing/provision may advance multiple reasons, consequences, legal arguments,
or opposing arguments. Exact source quotes are required for accepted rows.
All individual-level outputs remain private on the owner's Mac.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from erate.engine import normalized_text, sha256, read_csv, write_csv

KINDS={'normative_value','empirical_claim','predicted_consequence','legal_claim',
       'implementation_burden','cost_or_savings','equity_access','child_safety',
       'privacy_expression','alternative_design','personal_experience',
       'citation_of_external_evidence','other'}
EVIDENCE_TYPES={'personal_experience','data_or_statistics','academic_study',
 'government_source','statute_or_case','budget_or_invoice','business_practice',
 'logical_argument','quoted_other_person','unspecified'}
VALIDATION_STATUSES={'adjudicated','manual_reviewed'}
RECORD_FIELDS=['argument_id','submission_id','provision_id','claim_kind','argument_summary',
 'asserted_mechanism','requested_action','evidence_quote','evidence_start','evidence_end',
 'source_url','source_text_sha256','ocr_candidate','evidence_type','cited_authority',
 'cited_reference','evidence_independently_verified','coder_id','review_status','notes']
ERROR_FIELDS=['row_number','argument_id','submission_id','provision_id','error_codes']


def validate(base: Path, annotations: Path, snapshot_id='ocr_candidate_v1',
             view='augmented') -> dict:
    if view not in {'baseline','augmented'}:
        raise ValueError('Invalid text view')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',snapshot_id):
        raise ValueError('Invalid snapshot ID')
    corpus=base.expanduser().resolve()
    snapshot=corpus/'analysis_observatory'/f'research_snapshot_{snapshot_id}'
    text_dir=snapshot/('ocr_augmented_text' if view=='augmented' else 'baseline_text')
    inv,_=read_csv(snapshot/'research_inventory.csv')
    inv_by_id={r['submission_id']:r for r in inv}
    book=json.loads((Path(__file__).resolve().parents[1]/
        'analysis_methods/provision_codebook_v1.json').read_text())
    provisions={p['id'] for p in book['provisions']}
    rows,_=read_csv(annotations.expanduser().resolve())
    approved=[];errors=[];seen=set()
    for line,r in enumerate(rows,2):
        sid=r.get('submission_id','');pid=r.get('provision_id','')
        argid=r.get('argument_id','')
        kind=r.get('claim_kind','')
        q=r.get('evidence_quote','').strip()
        problems=[]
        if not argid or argid in seen:problems.append('missing_or_duplicate_argument_id')
        seen.add(argid)
        if sid not in inv_by_id:problems.append('unknown_submission')
        if pid not in provisions:problems.append('unknown_provision')
        if kind not in KINDS:problems.append('invalid_claim_kind')
        if r.get('evidence_type','') not in EVIDENCE_TYPES:problems.append('invalid_evidence_type')
        if r.get('review_status','') not in VALIDATION_STATUSES:problems.append('not_manually_reviewed')
        if not r.get('coder_id','').strip():problems.append('missing_coder_id')
        if not r.get('argument_summary','').strip():problems.append('missing_argument_summary')
        if not q:problems.append('missing_quote')
        # Cannot establish external truth from text recognition or quoting.
        verification=r.get('evidence_independently_verified','').strip().lower()
        if verification not in {'no','yes'}:
            problems.append('missing_external_verification_status')
        if verification=='yes' and not r.get('cited_reference','').strip():
            problems.append('verification_yes_requires_reference')
        content='';digest='';start=end=None
        if sid in inv_by_id:
            text_path=text_dir/f'{sid}.txt'
            if not text_path.is_file():
                problems.append('missing_research_text')
            else:
                content=text_path.read_text(encoding='utf-8-sig').strip()
                digest=sha256(normalized_text(content).encode())
                if digest!=inv_by_id[sid][f'{view}_sha256']:
                    problems.append('source_hash_mismatch')
                if q:
                    locations=[m.start() for m in re.finditer(re.escape(q),content)]
                    if len(locations)!=1:
                        problems.append('quote_missing_or_not_unique')
                    else:
                        start=locations[0]
                        end=start+len(q)
        if problems:
            errors.append({'row_number':line,'argument_id':argid,'submission_id':sid,
                           'provision_id':pid,'error_codes':';'.join(sorted(set(problems)))})
            continue
        approved.append({
            'argument_id':argid,'submission_id':sid,'provision_id':pid,
            'claim_kind':kind,'argument_summary':r['argument_summary'].strip(),
            'asserted_mechanism':r.get('asserted_mechanism',''),
            'requested_action':r.get('requested_action',''),
            'evidence_quote':q,'evidence_start':start,'evidence_end':end,
            'source_url':inv_by_id[sid]['source_url'],
            'source_text_sha256':digest,
            'ocr_candidate':inv_by_id[sid].get('has_unreviewed_ocr','0'),
            'evidence_type':r['evidence_type'],
            'cited_authority':r.get('cited_authority',''),
            'cited_reference':r.get('cited_reference',''),
            'evidence_independently_verified':verification,
            'coder_id':r['coder_id'],'review_status':r['review_status'],
            'notes':r.get('notes','')
        })
    out=snapshot/f'policy_analysis_{view}'
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'validated_argument_claims.csv',approved,RECORD_FIELDS)
    write_csv(out/'argument_validation_errors.csv',errors,ERROR_FIELDS)
    report={
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'submitted_argument_rows':len(rows),'accepted_argument_rows':len(approved),
        'rejected_argument_rows':len(errors),
        'source_filings_in_approved_arguments':len({r['submission_id'] for r in approved}),
        'distinct_filing_provision_pairs':len({(r['submission_id'],r['provision_id']) for r in approved}),
        'claim_kind_counts_in_reviewed_arguments':dict(Counter(r['claim_kind'] for r in approved)),
        'evidence_type_counts_in_reviewed_arguments':dict(Counter(r['evidence_type'] for r in approved)),
        'independently_verified_cited_evidence_count':sum(
            r['evidence_independently_verified']=='yes' for r in approved),
        'warning':'Argument rows are multi-valued per filing/provision. Never add argument totals to filing counts, assume factual assertions are true, or infer general-population prevalence from this sample. A quote matching an OCR candidate is not independent page-level OCR verification.'
    }
    (out/'argument_validation_summary.json').write_text(
        json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--annotations',type=Path,required=True)
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--view',choices=['baseline','augmented'],default='augmented')
    a=p.parse_args()
    print(json.dumps(validate(a.corpus,a.annotations,a.snapshot_id,a.view),indent=2))


if __name__=='__main__':main()
