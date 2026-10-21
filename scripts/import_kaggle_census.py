#!/usr/bin/env python3
"""Import public Kaggle output without Kaggle/GitHub credentials in the notebook."""
import argparse, json
from pathlib import Path
from scripts import llm_census as c
from scripts.kaggle_census import MODEL, SIZE, OVERLAP, BUNDLE, restore

def import_bundle(bundle, source, out, preview):
    records=c.load_corpus(source,None,'ocr_candidate_v1','augmented');book=c.load_book()
    if len(records)!=3231 or sum(bool(r['text'].strip()) for r in records)!=3230:
        raise ValueError('Unexpected source corpus')
    n=restore(bundle,out,records,book)
    summary=c.summarize(records,out,book,MODEL,SIZE,OVERLAP)
    summary['audit_queue_url']='./data/llm_kaggle_audit_queue.json'
    summary['execution_environment']='Kaggle free T4 x2'
    summary['limitations'].append('Long appendices use prioritized author-advocacy windows, not exhaustive model reading. See semantic_scope counts.')
    c.atomic_json(preview,summary)
    c.atomic_json(preview.parent/'llm_kaggle_audit_queue.json',json.loads((out/'suggested_human_audit.json').read_text()))
    return {'imported':n,'completed_filings':summary['completed_filings'],'readable_filings':3230}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path)
    p.add_argument('--notebook',default='shreyammm/fcc-e-rate-gpu-census')
    p.add_argument('--source',type=Path,default=c.ROOT/'data/fcc_corpus')
    p.add_argument('--out',type=Path,default=c.ROOT/'data/llm_census_kaggle')
    p.add_argument('--preview',type=Path,default=c.ROOT/'docs/data/llm_kaggle_exploratory.json')
    a=p.parse_args();bundle=a.bundle
    if bundle is None:
        import kagglehub
        bundle=Path(kagglehub.notebook_output_download(a.notebook,path=BUNDLE,force_download=True))
    print(json.dumps(import_bundle(bundle,a.source,a.out,a.preview)))
