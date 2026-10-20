#!/usr/bin/env python3
"""Write a prioritized list of candidate PDFs for OCR. Does NOT overwrite extracted text."""
import argparse, csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv, write_csv

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    corpus=args.corpus.expanduser().resolve()
    out=args.out or corpus/'analysis_observatory'
    rows,_=read_csv(out/'document_audit.csv')
    flagged=[r for r in rows if r['is_pdf']=='1' and 'pdf_text_100_chars_or_fewer_review_ocr' in r['quality_flags']]
    for r in flagged:
        r['recommended_action']='Visually inspect PDF; run OCR if scanned; compare extracted text; retain original'
    write_csv(out/'pdf_ocr_review_queue.csv',flagged,list(flagged[0]) if flagged else
        ['submission_id','document_number','filename','is_pdf','original_path','original_exists','original_hash_matches','text_path','text_exists','text_chars_actual','extraction_status','quality_flags','source_url','recommended_action'])
    print(f'{len(flagged)} PDFs need extraction-quality review. Queue: {out}/pdf_ocr_review_queue.csv')
    print('NO originals, manifests, or extracted texts modified.')
if __name__=='__main__':main()
