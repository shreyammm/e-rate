#!/usr/bin/env python3
"""Reconcile missing substantive text, OCR-needed PDFs, and duplicate clusters.

All output remains local in analysis_observatory. Never modifies source documents.
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv,write_csv

GAP_FIELDS=['submission_id','submission_type','status','combined_text_file_count',
            'combined_text_chars','substantive_text_chars','pdf_flagged_count',
            'pdf_triage_classes','document_count','quality_flags','source_url','investigation_category']
CLUSTER_FIELDS=['cluster_id','filing_count','texts_available','substantive_text_chars_min',
                'substantive_text_chars_max','filings_with_quality_flags','distinct_filer_keys',
                'cluster_size_note']


def analyze(analysis:Path):
    a=analysis.expanduser().resolve()
    inventory,_=read_csv(a/'filing_inventory.csv')
    review,_=read_csv(a/'pdf_deep_review.csv')
    clusters,_=read_csv(a/'exact_duplicate_clusters.csv')
    by_id={r['submission_id']:r for r in inventory}
    if len(by_id)!=len(inventory):raise ValueError('Duplicate filing identifiers in inventory')
    by_pdf=defaultdict(list)
    for d in review:
        if d['submission_id'] not in by_id:raise ValueError('PDF audit references unknown filing')
        by_pdf[d['submission_id']].append(d)
    gap=[]
    for r in inventory:
        sid=r['submission_id']; chars=int(r['substantive_text_chars'])
        if chars:continue
        docs=by_pdf.get(sid,[])
        kinds=sorted(set(d['triage_class'] for d in docs))
        if not int(r.get('combined_text_file_count',0)):
            reason='combined_text_file_missing'
        elif docs:
            reason='likely_ocr_recoverable_attachment'
        else:
            reason='no_substantive_text_without_flagged_pdf'
        gap.append({'submission_id':sid,'submission_type':r['submission_type'],
           'status':r['status'],'combined_text_file_count':r.get('combined_text_file_count',''),
           'combined_text_chars':r['text_chars'],'substantive_text_chars':chars,
           'pdf_flagged_count':len(docs),'pdf_triage_classes':';'.join(kinds),
           'document_count':r['document_count'],'quality_flags':r['quality_flags'],
           'source_url':r['source_url'],'investigation_category':reason})
    with_pdf=sum(bool(by_pdf.get(r['submission_id'])) for r in gap)
    flagged_filing_count=len(by_pdf)
    dedup=[]
    for d in clusters:
        ids=d['submission_ids'].split(';')
        if any(sid not in by_id for sid in ids):raise ValueError('Duplicate cluster references absent filing')
        rows=[by_id[sid] for sid in ids]
        lengths=[int(r['substantive_text_chars']) for r in rows]
        dedup.append({'cluster_id':d['cluster_id'],'filing_count':len(ids),
                      'texts_available':sum(v>0 for v in lengths),
                      'substantive_text_chars_min':min(lengths),
                      'substantive_text_chars_max':max(lengths),
                      'filings_with_quality_flags':sum(bool(r['quality_flags']) for r in rows),
                      'distinct_filer_keys':len({r['filer_key'] for r in rows if r['filer_key']}),
                      'cluster_size_note':'A matching text hash is not proof of coordinated behavior'})
    summary={
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'total_filings':len(inventory),
        'filings_without_substantive_text':len(gap),
        'filings_without_substantive_text_and_with_flagged_pdf':with_pdf,
        'filings_without_substantive_text_no_flagged_pdf':len(gap)-with_pdf,
        'filings_with_substantive_text_but_flagged_pdf':flagged_filing_count-with_pdf,
        'distinct_filings_with_flagged_pdf':flagged_filing_count,
        'flagged_pdf_attachments':len(review),
        'gap_investigation_categories':dict(Counter(r['investigation_category'] for r in gap)),
        'exact_duplicate_clusters_for_manual_review':len(dedup),
        'note':'OCR is a candidate extraction requiring quality control and does not retroactively change the original collection status.',
    }
    write_csv(a/'coverage_gap_review.csv',gap,GAP_FIELDS)
    write_csv(a/'duplicate_cluster_quality.csv',dedup,CLUSTER_FIELDS)
    (a/'coverage_diagnostics_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    args=p.parse_args()
    summary=analyze(args.corpus/'analysis_observatory')
    print(json.dumps(summary,indent=2))
    print('Local report:',args.corpus/'analysis_observatory/coverage_gap_review.csv')

if __name__=='__main__':main()
