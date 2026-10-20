#!/usr/bin/env python3
"""Read-only PDF text-quality triage; no OCR or source modifications."""
from __future__ import annotations
import argparse, hashlib, json, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import local_path, read_csv, write_csv

FIELDS=['submission_id','document_number','filename','source_url','original_path',
        'original_exists','bytes','pdf_pages','pages_inspected','pages_with_low_native_text',
        'pages_with_images','embedded_images','native_text_chars','inspection_truncated',
        'triage_class','review_action','inspection_error']

def triage(pdf_pages,inspected,native_chars,pages_images,inspection_error=''):
    if inspection_error:
        return 'cannot_inspect_pdf','Inspect original manually; do not infer missing content'
    if inspected<pdf_pages:
        return 'inspection_incomplete','Re-run with higher --max-pages; review full PDF'
    if native_chars>100:
        return 'extraction_pipeline_mismatch','Text layer exists but old extraction was short; re-extract separately'
    if pages_images>0:
        return 'ocr_candidate_image_based','Inspect images; attempt versioned OCR if document is scanned'
    if native_chars==0:
        return 'no_native_text_no_image_detected','Visual review: blank or vector graphics possible'
    return 'short_native_text','Check if legitimate short document or incomplete extraction'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--max-pages',type=int,default=250)
    a=ap.parse_args()
    if a.max_pages<1:ap.error('--max-pages must be positive')
    base=a.corpus.expanduser().resolve()
    out=(a.out or base/'analysis_observatory').expanduser().resolve()
    audit,_=read_csv(out/'document_audit.csv')
    targets=[r for r in audit if r.get('is_pdf')=='1' and
             'pdf_text_100_chars_or_fewer_review_ocr' in r.get('quality_flags','')]
    try:import pymupdf
    except ImportError:raise SystemExit('Install required PyMuPDF: python3 -m pip install pymupdf')
    data=[]
    for i,r in enumerate(targets,1):
        path=local_path(base,r['original_path'])
        x={k:'' for k in FIELDS}
        x.update(submission_id=r['submission_id'],document_number=r['document_number'],
                 filename=r['filename'],source_url=r['source_url'],original_path=r['original_path'],
                 original_exists=int(bool(path and path.is_file())),
                 bytes=0,pdf_pages=0,pages_inspected=0,pages_with_low_native_text=0,
                 pages_with_images=0,embedded_images=0,native_text_chars=0,inspection_truncated=0)
        if not path or not path.is_file():
            x['inspection_error']='missing_original_pdf'
        else:
            x['bytes']=path.stat().st_size
            try:
                with pymupdf.open(path) as pdf:
                    x['pdf_pages']=len(pdf)
                    for n in range(min(len(pdf),a.max_pages)):
                        page=pdf[n]
                        native=len(page.get_text('text').strip())
                        try:images=len(page.get_image_info())
                        except Exception:images=len(page.get_images(full=True))
                        x['native_text_chars']+=native
                        x['pages_inspected']+=1
                        x['pages_with_low_native_text']+=int(native<=50)
                        x['pages_with_images']+=int(images>0)
                        x['embedded_images']+=images
                    x['inspection_truncated']=int(x['pages_inspected']<len(pdf))
            except Exception as e:
                x['inspection_error']=f'{type(e).__name__}: {str(e)[:120]}'
        kind,action=triage(x['pdf_pages'],x['pages_inspected'],
                           x['native_text_chars'],x['pages_with_images'],
                           x['inspection_error'])
        x['triage_class']=kind;x['review_action']=action
        data.append(x)
        if i%25==0 or i==len(targets):
            print(f'Inspected {i}/{len(targets)} flagged PDFs',flush=True)
    write_csv(out/'pdf_deep_review.csv',data,FIELDS)
    summary={'generated_utc':datetime.now(timezone.utc).isoformat(),
      'method':'PyMuPDF read-only page-level text and image inspection',
      'max_pages_inspected_per_file':a.max_pages,
      'input_document_audit_sha256':hashlib.sha256((out/'document_audit.csv').read_bytes()).hexdigest(),
      'pdfs_flagged_by_first_pass':len(targets),
      'triage_classes':dict(Counter(r['triage_class'] for r in data)),
      'pdf_pages_total':sum(r['pdf_pages'] for r in data),
      'pdf_pages_inspected':sum(r['pages_inspected'] for r in data),
      'notes':['Short extracted text does not establish a scanned PDF.',
               'Images alone do not prove all content is image-only.',
               'No OCR performed and no corpus source files modified.']}
    (out/'pdf_deep_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    print('Detailed review:',out/'pdf_deep_review.csv')
    print('Original corpus unchanged.')
if __name__=='__main__':main()
