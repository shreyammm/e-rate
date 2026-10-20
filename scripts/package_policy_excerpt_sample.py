#!/usr/bin/env python3
"""Create a bounded, selectively redacted FCC passage sample for researcher review.

Package remains on local Mac unless its owner explicitly shares it. Contains
only FCC filing IDs, URLs, provisional issue IDs and excerpts: no filer table.
The corpus itself, original OCR and manually coded decisions are untouched.
"""
from __future__ import annotations
import argparse, csv, json, random, re, sys, zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv, normalized_text, sha256

ROOT=Path(__file__).resolve().parents[1]
EMAIL=re.compile(r'(?<!\w)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?!\w)',re.I)
PHONE=re.compile(r'(?<!\d)(?:\+1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)')


def redact_contact(text: str) -> str:
    return PHONE.sub('[PHONE REDACTED]',EMAIL.sub('[EMAIL REDACTED]',text))


def select_sample(pairs: list[dict], n_per_provision=4, seed=20261020) -> list[dict]:
    by_issue=defaultdict(list)
    for r in pairs:by_issue[r['provision_id']].append(r)
    rng=random.Random(seed)
    selected=[]
    for pid,rows in sorted(by_issue.items()):
        rows=sorted(rows,key=lambda r:(r['submission_id'],-int(r['hit_count'])))
        # Sampling without preference for prolific filers; nonrepresentative research pilot.
        keys=sorted({r['submission_id'] for r in rows})
        rng.shuffle(keys)
        selected_keys=set(keys[:n_per_provision])
        seen=set()
        for r in rows:
            if r['submission_id'] in selected_keys and r['submission_id'] not in seen:
                selected.append(r)
                seen.add(r['submission_id'])
    return selected


def package(corpus: Path, snapshot_id: str, per_provision: int,
            max_chars: int, output: Path | None = None) -> tuple[Path,dict]:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',snapshot_id):
        raise ValueError('Invalid snapshot id')
    if not 1<=per_provision<=20 or not 200<=max_chars<=3000:
        raise ValueError('Invalid sample constraints')
    base=corpus.expanduser().resolve()
    snap=base/'analysis_observatory'/f'research_snapshot_{snapshot_id}'
    candidates,_=read_csv(snap/'policy_analysis_augmented/candidate_passages.csv')
    provisions=json.loads((ROOT/'analysis_methods/provision_codebook_v1.json').read_text())['provisions']
    lookup={p['id']:p for p in provisions}
    selected=select_sample(candidates,per_provision)
    out=[]
    for r in selected:
        if r['provision_id'] not in lookup:
            raise ValueError('Unknown provision in candidate passages')
        p=lookup[r['provision_id']]
        excerpt=redact_contact(r['excerpt'][:max_chars])
        out.append({
            'filing_id':r['submission_id'],'source_url':r['source_url'],
            'provision_id':r['provision_id'],'provision_label':p['label'],
            'policy_option':p['policy_option'],
            'notice_status':p['notice_status'],
            'matched_terms':r['matched_terms'],
            'ocr_candidate':r['ocr_candidate'],
            'excerpt':excerpt,
            'source_text_sha256':r['source_text_sha256'],
            'research_prompt':'Determine whether the passage actually discusses this specific policy option. If yes, extract what FCC action the commenter advocates, reasons, predicted harms/benefits, any alternative or condition. Cite the exact excerpt. Do not infer from keywords or filer identity.'
        })
    dest=(output or base.parent/'FCC_POLICY_EVIDENCE_SAMPLE.zip').expanduser().resolve()
    if dest.exists():
        raise FileExistsError(f'Archive already exists, choose a different --output: {dest}')
    report={
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'snapshot_id':snapshot_id,'selection':'seeded random documents within provision keyword-positive candidates',
        'sample_provision_pairs':len(out),
        'unique_filings':len({r['filing_id'] for r in out}),
        'coverage_by_provision':{p['id']:sum(r['provision_id']==p['id'] for r in out) for p in provisions},
        'not_a_census_or_probability_sample':True,
        'pii_warning':'Basic email and phone masking is applied; review excerpt contents before sharing because names, places, signatures and other personal data might remain.',
        'stance_warning':'Keyword candidate excerpts often discuss a proposal without supporting it, may be incomplete, and are NOT validated classifications.',
        'reason_for_export':'Permit direct qualitative analysis and verification of representative examples without bulk transfer of the full local corpus.'
    }
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('sample_excerpt_pairs.jsonl',
                   ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in out))
        z.writestr('sampling_method.json',json.dumps(report,indent=2)+'\n')
    return dest,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--per-provision',type=int,default=4)
    p.add_argument('--max-chars',type=int,default=1100)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    dest,report=package(args.corpus,args.snapshot_id,args.per_provision,
                        args.max_chars,args.output)
    print(json.dumps({'archive':str(dest),'sample_provision_pairs':report['sample_provision_pairs'],
                      'unique_filings':report['unique_filings'],'pii_warning':report['pii_warning']},indent=2))


if __name__=='__main__':
    main()
