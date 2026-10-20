#!/usr/bin/env python3
"""One-way, source-validated portable export for the optional public automated LLM lane.

Does not change originals or other research outputs. Public export includes unredacted
filer metadata and text: review ECFS personal contact information before publication.
"""
import argparse
import json
from pathlib import Path
from scripts.llm_census import load_corpus, digest


def export(corpus: Path, target: Path, snapshot_id='ocr_candidate_v1', view='augmented') -> dict:
    rows=load_corpus(None,corpus,snapshot_id,view)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('w',encoding='utf-8') as f:
        for row in rows:
            row['text_sha256']=digest(row['text']) if row['text'] else ''
            row['source_text_view']=view
            row['snapshot_id']=snapshot_id
            f.write(json.dumps(row,ensure_ascii=False)+'\n')
    result={'filings':len(rows),'with_text':sum(bool(r['text']) for r in rows),
            'snapshot_id':snapshot_id,'view':view,'path':str(target)}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--output',type=Path,default=Path('data/fcc_corpus/filings.jsonl'))
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--view',choices=['augmented','baseline'],default='augmented')
    a=p.parse_args()
    print(json.dumps(export(a.corpus.expanduser(),a.output,a.snapshot_id,a.view),indent=2))

if __name__=='__main__':main()
