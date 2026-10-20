#!/usr/bin/env python3
"""Find candidate near-duplicate comment families in an immutable research snapshot.

Similarity is measured on *content*, not agreement. Connected components are
candidate families, and not all family members necessarily match each other.
Outputs are local and may contain filing URLs/metadata: do not publish raw CSVs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import filer_key, normalized_text, read_csv, sha256, write_csv
from erate.near_duplicates import find_candidates

FAMILY_FIELDS = [
    'family_id', 'filing_count', 'edge_count', 'distinct_exact_filer_fields',
    'members_with_ocr_candidates', 'example_submission_id',
    'member_submission_ids', 'interpretation'
]
MEMBER_FIELDS = [
    'family_id','submission_id','source_url','filing_date','filer_key',
    'text_view','had_ocr_candidate'
]
PAIR_FIELDS=[
    'submission_id_a','submission_id_b','shingle_jaccard','method','interpretation'
]


def families_from_pairs(pairs: list[dict], inventory: dict[str,dict], view: str):
    """Connected components; never assert all cross-pairs are above threshold."""
    parent={}
    size={}
    def root(x):
        parent.setdefault(x,x)
        size.setdefault(x,1)
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    def unite(a,b):
        a,b=root(a),root(b)
        if a==b:return
        if (size[a],a)<(size[b],b):a,b=b,a
        parent[b]=a
        size[a]+=size[b]
    for pair in pairs:
        a,b=pair['submission_id_a'],pair['submission_id_b']
        if a==b or a not in inventory or b not in inventory:
            raise ValueError('Candidate edge has missing or repeated filing IDs')
        unite(a,b)
    groups=defaultdict(set)
    for key in parent:
        groups[root(key)].add(key)
    ranked=sorted((sorted(members) for members in groups.values()),
                  key=lambda v:(-len(v),v[0]))
    edge_count=Counter()
    cluster_for={}
    for i,members in enumerate(ranked,1):
        cid=f'near_{i:05d}'
        for sid in members:cluster_for[sid]=cid
    for pair in pairs:edge_count[cluster_for[pair['submission_id_a']]]+=1
    family_rows=[]
    member_rows=[]
    for i,members in enumerate(ranked,1):
        cid=f'near_{i:05d}'
        keys={filer_key(inventory[sid]['filer_raw']) for sid in members
              if filer_key(inventory[sid]['filer_raw'])}
        family_rows.append({
            'family_id':cid,'filing_count':len(members),'edge_count':edge_count[cid],
            'distinct_exact_filer_fields':len(keys),
            'members_with_ocr_candidates':sum(
                int(inventory[sid].get('has_unreviewed_ocr') or 0) for sid in members),
            'example_submission_id':members[0],
            'member_submission_ids':';'.join(members),
            'interpretation':'near_duplicate_connected_component_requires_manual_review'
        })
        for sid in members:
            row=inventory[sid]
            member_rows.append({
                'family_id':cid,'submission_id':sid,'source_url':row['source_url'],
                'filing_date':row['date_submission'],
                'filer_key':filer_key(row['filer_raw']),
                'text_view':view,
                'had_ocr_candidate':row.get('has_unreviewed_ocr','0')
            })
    return family_rows,member_rows


def analyze(corpus: Path, snapshot_id: str, view: str, threshold: float = .87) -> dict:
    if view not in {'baseline','augmented'}:
        raise ValueError('Invalid view')
    if not 0<threshold<=1:
        raise ValueError('Similarity threshold must be in (0,1]')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',snapshot_id):
        raise ValueError('Invalid snapshot ID')
    corpus=corpus.expanduser().resolve()
    snap=corpus/'analysis_observatory'/f'research_snapshot_{snapshot_id}'
    inventory,fields=read_csv(snap/'research_inventory.csv')
    if len({r['submission_id'] for r in inventory})!=len(inventory):
        raise ValueError('Repeated submission ID')
    inventory_by_id={r['submission_id']:r for r in inventory}
    column='baseline' if view=='baseline' else 'augmented'
    folder=snap/('baseline_text' if view=='baseline' else 'ocr_augmented_text')
    texts={}
    quality_exclusions=Counter()
    for r in inventory:
        if r['agency_record_candidate']=='1':
            quality_exclusions['agency_record_candidate']+=1
            continue
        if int(r[f'{column}_chars'])<120:
            quality_exclusions['short_or_missing_text']+=1
            continue
        sid=r['submission_id']
        source=folder/f'{sid}.txt'
        if not source.is_file():
            raise FileNotFoundError(f'Snapshot claims content but it is missing: {source}')
        content=source.read_text(encoding='utf-8-sig').strip()
        if sha256(normalized_text(content).encode())!=r[f'{column}_sha256']:
            raise ValueError(f'Immutable snapshot text hash mismatch: {sid}')
        texts[sid]=content
    pairs,method=find_candidates(texts,threshold)
    families,members=families_from_pairs(pairs,inventory_by_id,view)
    out=snap/f'templates_{view}'
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'near_duplicate_candidates.csv',pairs,PAIR_FIELDS)
    write_csv(out/'near_duplicate_families.csv',families,FAMILY_FIELDS)
    write_csv(out/'near_duplicate_members.csv',members,MEMBER_FIELDS)
    summary={
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'snapshot_id':snapshot_id,'text_view':view,'threshold':threshold,
        'minhash_method':method,
        'filings_considered':len(texts),
        'excluded_counts':dict(quality_exclusions),
        'candidate_pairs_above_threshold':len(pairs),
        'candidate_near_duplicate_families':len(families),
        'filings_in_candidate_families':len(members),
        'family_size_max':max((int(r['filing_count']) for r in families),default=0),
        'candidate_families_with_multiple_exact_filer_fields':sum(
            int(r['distinct_exact_filer_fields'])>1 for r in families),
        'warnings':[
            'Candidates use approximate MinHash LSH, not exhaustive pair search.',
            'Five-word Jaccard on texts emphasizes repeated language, not semantic agreement.',
            'Connected components are transitive: members need not match each other.',
            'Repeated letters do not prove coordinated or inauthentic conduct.',
            'Exact-normalized filer strings are not verified unique people.',
            'OCR-augmented texts are candidate transcripts pending human validation.',
            'Agency candidates excluded by unverified submission type; correct entity resolution is pending.',
            'All individual-level research output stays local and must not be pushed to public GitHub.'
        ]
    }
    (out/'near_duplicate_method_report.json').write_text(
        json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--view',choices=['baseline','augmented'],default='augmented')
    p.add_argument('--threshold',type=float,default=.87)
    args=p.parse_args()
    result=analyze(args.corpus,args.snapshot_id,args.view,args.threshold)
    print(json.dumps(result,indent=2))
    print('Results:',args.corpus/'analysis_observatory'/
          f'research_snapshot_{args.snapshot_id}'/f'templates_{args.view}')


if __name__=='__main__':
    main()
