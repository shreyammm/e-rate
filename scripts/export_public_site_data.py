#!/usr/bin/env python3
"""Export reviewed aggregate FCC positions to a static GitHub Pages data file.

Default is private PREVIEW ONLY outside the public Git repository. Publishing
requires --publish-reviewed and explicitly includes no filer names and no
bulk comment transcripts. Do not publish pilot statistics as corpus prevalence.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv, sha256

ROOT=Path(__file__).resolve().parents[1]
POSITIONS=['support','oppose','conditional_or_amend','alternative_proposal',
           'discussion_no_position','unclear','not_addressed']


def build(corpus:Path,snapshot_id='ocr_candidate_v1',view='augmented',
          publish=False,include_quotes=False) -> tuple[Path,dict]:
    base=corpus.expanduser().resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',snapshot_id):
        raise ValueError('Invalid snapshot ID')
    snap=base/'analysis_observatory'/f'research_snapshot_{snapshot_id}'
    book=json.loads((ROOT/'analysis_methods/provision_codebook_v1.json').read_text())
    approved_path=snap/f'policy_analysis_{view}'/'validated_positions.csv'
    if not approved_path.exists():
        raise FileNotFoundError('Run the human annotation validator first. Missing '+str(approved_path))
    rows,_=read_csv(approved_path)
    valid_ids={p['id'] for p in book['provisions']}
    if len({(r['submission_id'],r['provision_id']) for r in rows})!=len(rows):
        raise ValueError('Duplicate human-reviewed filing/provision pair')
    if any(r['provision_id'] not in valid_ids or r['position'] not in POSITIONS for r in rows):
        raise ValueError('Unknown reviewed provision or position')
    if any(r['review_status'] not in {'manual_reviewed','adjudicated'} for r in rows):
        raise ValueError('Model-only or pending annotation in validated positions')
    argument_file=snap/f'policy_analysis_{view}'/'validated_argument_claims.csv'
    argument_rows,_=read_csv(argument_file) if argument_file.is_file() else ([],[])
    if len({r['argument_id'] for r in argument_rows})!=len(argument_rows):
        raise ValueError('Duplicate argument identifiers')
    if any(r['provision_id'] not in valid_ids or
           r['review_status'] not in {'manual_reviewed','adjudicated'}
           for r in argument_rows):
        raise ValueError('Unreviewed or unknown argument in validated table')
    arguments_by_provision=defaultdict(list)
    for r in argument_rows:arguments_by_provision[r['provision_id']].append(r)
    seen=defaultdict(list)
    for row in rows:seen[row['provision_id']].append(row)
    records=[]
    for prov in book['provisions']:
        group=seen[prov['id']]
        count=Counter(r['position'] for r in group)
        # Review links are included only for stance-bearing reviewed filings.
        evidence=[]
        for pos in POSITIONS[:4]:
            related=[r for r in group if r['position']==pos and r['source_url'].startswith('https://www.fcc.gov/')]
            for r in related[:3]:
                e={'position':pos,'source_url':r['source_url'],'filing_id':r['submission_id']}
                if include_quotes and r['evidence_quote']:
                    e['quote']=r['evidence_quote'][:350]
                evidence.append(e)
        records.append({
            'id':prov['id'],'label':prov['label'],'category':prov['category'],
            'policy_option':prov['policy_option'],
            'notice_status':prov['notice_status'],
            'notice_paragraph_range':prov['notice_paragraph_range'],
            'adjudicated_filing_count':len(group),
            'counts':{pos:count[pos] for pos in POSITIONS},
            'reviewed_argument_count':len(arguments_by_provision[prov['id']]),
            'reviewed_argument_types':dict(Counter(
                r['claim_kind'] for r in arguments_by_provision[prov['id']])),
            'evidence':evidence
        })
    payload={
        'schema_version':'1.0',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'publication_status':'limited_human_review_not_corpus_wide_estimate' if rows else 'awaiting_validated_position_data',
        'dataset_snapshot_id':snapshot_id,
        'text_view':view,
        'reviewed_filing_provision_pairs':len(rows),
        'unique_filings_reviewed':len({r['submission_id'] for r in rows}),
        'reviewed_arguments':len(argument_rows),
        'unique_filings_with_reviewed_arguments':len({r['submission_id'] for r in argument_rows}),
        'indexed_filing_count':3231,
        'position_denominator':'Only filing/provision pairs that were explicitly reviewed and validated. Nonmatching/unreviewed records are excluded, not classified not_addressed.',
        'notice_url':book['notice_url'],'codebook_version':book['version'],
        'method_notes':[
            'All positions are provision-specific, not generic positive or negative sentiment.',
            'This is a self-selected FCC filing record, not an opinion survey.',
            'Keyword candidate counts are excluded from stance charts.',
            'Argument counts are different units from filing-position counts. A single filing can contain multiple arguments.',
            'Claims cited by commenters have not necessarily been independently fact-checked.',
            'OCR candidate provenance and unresolved agency/document and identity classifications limit inference.',
            'Counts may be biased by the review sample. Do not infer all-comment prevalence until an audited sample or census is complete.'
        ],
        'provisions':records
    }
    if publish:
        dest=ROOT/'docs/data/public_results.json'
    else:
        dest=snap/f'policy_analysis_{view}'/'site_preview'/'public_results.json'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return dest,payload


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--view',choices=['baseline','augmented'],default='augmented')
    p.add_argument('--publish-reviewed',action='store_true',
                   help='Explicitly write reviewed aggregate data into public docs/data directory')
    p.add_argument('--include-quotes',action='store_true',
                   help='Explicitly include short human-reviewed excerpt examples in public JSON')
    a=p.parse_args()
    if a.include_quotes and not a.publish_reviewed:
        p.error('Including quotes requires --publish-reviewed')
    file,payload=build(a.corpus,a.snapshot_id,a.view,a.publish_reviewed,a.include_quotes)
    print(json.dumps({'file':str(file),
        'adjudicated_pairs':payload['reviewed_filing_provision_pairs'],
        'publish_requested':a.publish_reviewed},indent=2))


if __name__=='__main__':
    main()
