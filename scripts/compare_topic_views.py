#!/usr/bin/env python3
"""Compare separately fitted baseline and augmented NMF topics on common filings.

Optimal matches maximize shared-filings overlap, NOT semantic equivalence.
Produces local aggregate tables and source-linked human review candidates.
No comment text or filer names are uploaded anywhere.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv, write_csv, sha256

ALIGN_FIELDS=[
    'baseline_topic','augmented_topic','baseline_top_terms','augmented_top_terms',
    'baseline_common_filings','augmented_common_filings','shared_filing_overlap',
    'union_common_filings','filing_jaccard_on_common','retained_baseline_fraction',
    'augmented_newly_eligible_filings','augmented_all_filings','top10_term_jaccard',
    'interpretation'
]
TRANSITION_FIELDS=['baseline_topic','augmented_topic','common_filing_count']
ADDITION_FIELDS=['augmented_topic','augmented_top_terms',
                 'filings_newly_eligible_after_ocr','share_of_newly_eligible_filings']
REVIEW_FIELDS=['submission_id','source_url','augmented_topic','augmented_top_terms',
               'selection_stratum','topic_strength','baseline_topic','human_review_notes']


def read_table(path: Path, key: str) -> tuple[list[dict], dict[str,dict]]:
    rows,_=read_csv(path)
    keys=[r[key] for r in rows]
    if len(keys)!=len(set(keys)):
        raise ValueError(f'Duplicate {key} in {path}')
    return rows,{r[key]:r for r in rows}


def top_terms(row: dict) -> set[str]:
    return {t.strip().casefold() for t in row['top_terms'].split(';') if t.strip()}


def match_topics(
    baseline_ids: list[str], augmented_ids: list[str],
    common_baseline: dict[str,str], common_augmented: dict[str,str]
) -> list[tuple[str,str,int]]:
    """Return one-to-one overlap-optimal topic pairs; ties are deterministic."""
    from scipy.optimize import linear_sum_assignment
    if set(common_baseline)!=set(common_augmented):
        raise ValueError('Both topic mappings must reference the same common filings')
    if not baseline_ids or not augmented_ids:
        return []
    matrix=[[0 for _ in augmented_ids] for _ in baseline_ids]
    bi={v:i for i,v in enumerate(baseline_ids)}
    ai={v:i for i,v in enumerate(augmented_ids)}
    for sid,b in common_baseline.items():
        a=common_augmented[sid]
        if b not in bi or a not in ai:
            raise ValueError(f'Unknown topic label on filing {sid}')
        matrix[bi[b]][ai[a]]+=1
    # Maximize common-filing overlap, not lexical terms or topic-ID similarities.
    rows,cols=linear_sum_assignment(matrix,maximize=True)
    return [(baseline_ids[i],augmented_ids[j],matrix[i][j]) for i,j in zip(rows,cols)]


def analyze(snapshot: Path, sample_per_topic: int = 3) -> dict:
    snapshot=snapshot.expanduser().resolve()
    if sample_per_topic<0 or sample_per_topic>30:
        raise ValueError('sample-per-topic must be between 0 and 30')
    if not (snapshot/'snapshot_summary.json').is_file():
        raise FileNotFoundError('Research snapshot not found. Run build_research_snapshot.py first.')
    snapshot_info=json.loads((snapshot/'snapshot_summary.json').read_text(encoding='utf-8'))
    base=snapshot/'themes_baseline'
    aug=snapshot/'themes_augmented'
    required=[
        base/'exploratory_topic_map.csv',base/'exploratory_topics.csv',base/'exploratory_topic_method.json',
        aug/'exploratory_topic_map.csv',aug/'exploratory_topics.csv',aug/'exploratory_topic_method.json'
    ]
    missing=[str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError('Both topic models must finish first. Missing: '+'; '.join(missing))
    baseline,base_by_sid=read_table(base/'exploratory_topic_map.csv','submission_id')
    augmented,aug_by_sid=read_table(aug/'exploratory_topic_map.csv','submission_id')
    base_topics,base_by_topic=read_table(base/'exploratory_topics.csv','topic_id')
    aug_topics,aug_by_topic=read_table(aug/'exploratory_topics.csv','topic_id')
    base_method=json.loads((base/'exploratory_topic_method.json').read_text())
    aug_method=json.loads((aug/'exploratory_topic_method.json').read_text())

    for m,v in ((base_method,'baseline'),(aug_method,'augmented')):
        if m.get('text_view')!=v or m.get('source_snapshot_id')!=snapshot_info.get('run_id'):
            raise ValueError(f'Topic model method manifest does not match {v} research snapshot')
    if len(baseline)!=int(base_method['eligible_filings']) or len(augmented)!=int(aug_method['eligible_filings']):
        raise ValueError('Topic map row counts do not match method reports')
    base_ids=sorted(base_by_topic)
    aug_ids=sorted(aug_by_topic)
    for label, rows, valid in [('baseline',baseline,base_by_topic),('augmented',augmented,aug_by_topic)]:
        if len(valid)!=len(rows) and not rows:
            raise ValueError(f'{label} has no mapped filings')
        for r in rows:
            if r['topic_id'] not in valid:
                raise ValueError(f'Unknown {label} topic {r["topic_id"]}')
            try: value=float(r['topic_strength'])
            except (TypeError, ValueError): raise ValueError(f'Invalid topic strength in {label}')
            if not 0<=value<=1:
                raise ValueError(f'Out-of-range topic strength in {label}')
    common=set(base_by_sid)&set(aug_by_sid)
    removed=set(base_by_sid)-set(aug_by_sid)
    added=set(aug_by_sid)-set(base_by_sid)
    # Intentionally explicit: cannot silently call removed documents "OCR additions".
    if removed:
        raise ValueError(f'{len(removed)} baseline-eligible filings missing in augmented view')
    cb={sid:base_by_sid[sid]['topic_id'] for sid in common}
    ca={sid:aug_by_sid[sid]['topic_id'] for sid in common}
    pairs=match_topics(base_ids,aug_ids,cb,ca)
    cc=Counter((cb[sid],ca[sid]) for sid in common)
    cb_size=Counter(cb.values());ca_size=Counter(ca.values())
    all_aug=Counter(r['topic_id'] for r in augmented)
    new_aug=Counter(aug_by_sid[sid]['topic_id'] for sid in added)
    align=[]
    for b,a,intersection in pairs:
        union=cb_size[b]+ca_size[a]-intersection
        term_b=top_terms(base_by_topic[b]);term_a=top_terms(aug_by_topic[a])
        align.append(dict(
            baseline_topic=b,augmented_topic=a,
            baseline_top_terms=base_by_topic[b]['top_terms'],
            augmented_top_terms=aug_by_topic[a]['top_terms'],
            baseline_common_filings=cb_size[b],augmented_common_filings=ca_size[a],
            shared_filing_overlap=intersection,union_common_filings=union,
            filing_jaccard_on_common=round(intersection/union,4) if union else 0,
            retained_baseline_fraction=round(intersection/cb_size[b],4) if cb_size[b] else 0,
            augmented_newly_eligible_filings=new_aug[a],
            augmented_all_filings=all_aug[a],
            top10_term_jaccard=round(len(term_a&term_b)/len(term_a|term_b),4) if (term_a|term_b) else 0,
            interpretation='algorithmic_overlap_match_not_proven_semantic_equivalence'
        ))
    transitions=[
        {'baseline_topic':b,'augmented_topic':a,'common_filing_count':cc[(b,a)]}
        for b in base_ids for a in aug_ids
    ]
    additions=[
        {'augmented_topic':a,'augmented_top_terms':aug_by_topic[a]['top_terms'],
         'filings_newly_eligible_after_ocr':new_aug[a],
         'share_of_newly_eligible_filings':round(new_aug[a]/len(added),4) if added else 0}
        for a in aug_ids
    ]
    # Both a random sample and high-scoring exemplar are useful; here we select
    # high-scoring within each topic, split between newly recovered and shared.
    # Exemplars are NOT representative and may include duplicate form letters.
    review=[]
    for a in aug_ids:
        for stratum,ids in [('newly_eligible_after_ocr',added),('shared_with_baseline',common)]:
            records=[aug_by_sid[sid] for sid in ids if aug_by_sid[sid]['topic_id']==a]
            records.sort(key=lambda r:(-float(r['topic_strength']),r['submission_id']))
            for r in records[:sample_per_topic]:
                sid=r['submission_id']
                review.append({
                    'submission_id':sid,'source_url':r['source_url'],
                    'augmented_topic':a,'augmented_top_terms':aug_by_topic[a]['top_terms'],
                    'selection_stratum':stratum,'topic_strength':r['topic_strength'],
                    'baseline_topic':cb.get(sid,''),
                    'human_review_notes':''
                })
    total_overlap=sum(x[2] for x in pairs)
    aggregate={
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'snapshot_id':snapshot_info['run_id'],
        'baseline_eligible_filings':len(baseline),
        'augmented_eligible_filings':len(augmented),
        'filings_in_both_views':len(common),
        'filings_newly_eligible_after_ocr':len(added),
        'baseline_only_filings':len(removed),
        'baseline_n_topics':len(base_ids),'augmented_n_topics':len(aug_ids),
        'optimal_matched_topics':len(pairs),
        'common_filings_retaining_matched_topic':total_overlap,
        'matched_topic_assignment_stability_on_common':
            round(total_overlap/len(common),4) if common else 0,
        'source_map_sha256':{
            'baseline':sha256((base/'exploratory_topic_map.csv').read_bytes()),
            'augmented':sha256((aug/'exploratory_topic_map.csv').read_bytes())},
        'sample_filings_selected_for_manual_review':len(review),
        'limitations':[
            'NMF models are fitted independently; topic numbers are NOT aligned a priori.',
            'Optimal assignment maximizes filing membership overlap; it is not proof of semantic equivalence.',
            'Assignment stability is not a validation metric and does not establish meaningful thematic categories.',
            'Newly eligible after OCR means the text crossed the model eligibility threshold, not a new public comment.',
            'OCR transcripts are provisional unless visually validated.',
            'Strongly associated topic is not a policy position or evidence of agreement.',
            'High-scoring review examples are intentionally nonrepresentative; review duplicates and filer concentration separately.',
            'Eligibility excludes agency-record candidates by unverified ECFS submission-type proxy.',
            'This is a self-selected filing sample and not representative public opinion.'
        ]
    }
    out=snapshot/'theme_comparison'
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'topic_alignment.csv',align,ALIGN_FIELDS)
    write_csv(out/'topic_transitions.csv',transitions,TRANSITION_FIELDS)
    write_csv(out/'ocr_newly_eligible_by_topic.csv',additions,ADDITION_FIELDS)
    write_csv(out/'human_theme_review_sample.csv',review,REVIEW_FIELDS)
    (out/'topic_comparison_summary.json').write_text(
        json.dumps(aggregate,indent=2)+'\n',encoding='utf-8')
    return aggregate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--sample-per-topic',type=int,default=3)
    args=p.parse_args()
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',args.snapshot_id):
        p.error('Invalid snapshot ID')
    dest=args.corpus.expanduser()/'analysis_observatory'/f'research_snapshot_{args.snapshot_id}'
    result=analyze(dest,args.sample_per_topic)
    print(json.dumps(result,indent=2))
    print('Local reports:',dest/'theme_comparison')


if __name__=='__main__':
    main()
