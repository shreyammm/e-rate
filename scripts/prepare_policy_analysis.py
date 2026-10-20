#!/usr/bin/env python3
"""Retrieve exact FCC-provision evidence windows; do NOT infer commenter stance.

The source passages and filer metadata remain in the local corpus. Keyword
retrieval is incomplete and cannot classify a person as supporting a proposal.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv, normalized_text, sha256, write_csv

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'analysis_methods/provision_codebook_v1.json'
FIELDS=['submission_id','provision_id','source_url','notice_paragraph_range',
        'ocr_candidate','matched_terms','hit_count','excerpt',
        'excerpt_start','excerpt_end','source_text_sha256','retrieval_status']
QUEUE=['submission_id','provision_id','source_url','matched_terms','ocr_candidate',
       'review_status','position','requested_action','rationale','reason_families',
       'stakeholder_role','stakeholder_evidence','evidence_quote','evidence_start',
       'evidence_end','coder_id','notes']
TOTAL=['provision_id','category','policy_option','notice_status','paragraph_range',
       'candidate_filing_count','candidate_passage_count']


def candidate_windows(text: str, terms: list[str], limit: int = 2, radius: int = 240) -> list[dict]:
    hits=[]
    for term in terms:
        expr=r'(?<!\w)'+r'[\s-]+'.join(re.escape(w) for w in term.split())+r'(?!\w)'
        for m in re.finditer(expr,text,flags=re.IGNORECASE):
            hits.append((m.start(),m.end(),term))
    hits.sort()
    windows=[]
    for start,end,term in hits:
        left=max(0,start-radius);right=min(len(text),end+radius)
        if windows and left<=windows[-1]['end']:
            w=windows[-1];w['end']=max(right,w['end'])
            w['terms'].add(term);w['hits']+=1
        else:
            windows.append({'start':left,'end':right,'terms':{term},'hits':1})
    ordered=sorted(windows,key=lambda x:(-len(x['terms']),-x['hits'],x['start']))[:limit]
    output=[]
    for w in ordered:
        # A dense collection of mentions can span pages; bound the excerpt.
        start=w['start'];end=min(w['end'],start+1400)
        if end<=start:continue
        output.append({'excerpt':text[start:end],'excerpt_start':start,
                       'excerpt_end':end,'matched_terms':'; '.join(sorted(w['terms'])),
                       'hit_count':w['hits']})
    return output


def analyze(corpus: Path, snapshot_id='ocr_candidate_v1',view='augmented',max_excerpts=2) -> dict:
    if view not in {'baseline','augmented'}:raise ValueError('Invalid text view')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',snapshot_id):
        raise ValueError('Invalid snapshot ID')
    if not 1<=max_excerpts<=10:raise ValueError('max_excerpts should be 1..10')
    base=corpus.expanduser().resolve()
    snapshot=base/'analysis_observatory'/f'research_snapshot_{snapshot_id}'
    inventory,_=read_csv(snapshot/'research_inventory.csv')
    codebook=json.loads(BOOK.read_text(encoding='utf-8'))
    pids=[p['id'] for p in codebook['provisions']]
    if len(set(pids))!=len(pids):raise ValueError('Duplicate codebook issue IDs')
    text_dir=snapshot/('ocr_augmented_text' if view=='augmented' else 'baseline_text')
    out=snapshot/f'policy_analysis_{view}'
    candidates=[];queue=[];mention_counts=Counter();passage_counts=Counter();missing=0
    for row in inventory:
        sid=row['submission_id'];path=text_dir/f'{sid}.txt'
        if not path.is_file():
            missing+=1;continue
        text=path.read_text(encoding='utf-8-sig').strip()
        if sha256(normalized_text(text).encode())!=row[f'{view}_sha256']:
            raise ValueError('Immutable snapshot hash mismatch for '+sid)
        for provision in codebook['provisions']:
            pid=provision['id']
            windows=candidate_windows(text,provision['search_terms'],max_excerpts)
            if not windows:continue
            mention_counts[pid]+=1;passage_counts[pid]+=len(windows)
            for w in windows:
                candidates.append({
                  'submission_id':sid,'provision_id':pid,
                  'source_url':row['source_url'],
                  'notice_paragraph_range':provision['notice_paragraph_range'],
                  'ocr_candidate':row['has_unreviewed_ocr'],
                  'matched_terms':w['matched_terms'],'hit_count':w['hit_count'],
                  'excerpt':w['excerpt'],'excerpt_start':w['excerpt_start'],
                  'excerpt_end':w['excerpt_end'],
                  'source_text_sha256':row[f'{view}_sha256'],
                  'retrieval_status':'CANDIDATE_ONLY_NOT_A_POSITION'
                })
            queue.append({
                'submission_id':sid,'provision_id':pid,'source_url':row['source_url'],
                'matched_terms':'; '.join(sorted(set(t for w in windows for t in w['matched_terms'].split('; ')))),
                'ocr_candidate':row['has_unreviewed_ocr'],
                'review_status':'pending','position':'','requested_action':'',
                'rationale':'','reason_families':'','stakeholder_role':'',
                'stakeholder_evidence':'','evidence_quote':'','evidence_start':'',
                'evidence_end':'','coder_id':'','notes':''
            })
    totals=[{
      'provision_id':p['id'],'category':p['category'],
      'policy_option':p['policy_option'],'notice_status':p['notice_status'],
      'paragraph_range':p['notice_paragraph_range'],
      'candidate_filing_count':mention_counts[p['id']],
      'candidate_passage_count':passage_counts[p['id']]
    } for p in codebook['provisions']]
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'candidate_passages.csv',candidates,FIELDS)
    write_csv(out/'review_queue_GENERATED.csv',queue,QUEUE)
    write_csv(out/'provision_retrieval_summary.csv',totals,TOTAL)
    report={
      'timestamp_utc':datetime.now(timezone.utc).isoformat(),'snapshot_id':snapshot_id,
      'text_view':view,'codebook_version':codebook['version'],
      'codebook_sha256':sha256(BOOK.read_bytes()),
      'indexed_filings':len(inventory),'filings_missing_text':missing,
      'filings_with_any_keyword_candidate':len({r['submission_id'] for r in queue}),
      'distinct_filing_provision_candidate_pairs':len(queue),
      'retrieved_passages':len(candidates),'provisions':len(totals),
      'stance_counts_inferred':0,
      'warning':'Keyword hits are candidates ONLY, not verified discussion/support/opposition. Keyword-negative filings are not certified not_addressed. Generated queue is overwritten on rerun: human annotations must be saved separately.'
    }
    (out/'retrieval_method_summary.json').write_text(
        json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--view',choices=['baseline','augmented'],default='augmented')
    p.add_argument('--max-excerpts',type=int,default=2)
    a=p.parse_args()
    print(json.dumps(analyze(a.corpus,a.snapshot_id,a.view,a.max_excerpts),indent=2))


if __name__=='__main__':main()
