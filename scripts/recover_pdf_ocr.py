#!/usr/bin/env python3
"""Locally recover text from PDFs flagged in the read-only deep audit.

Never changes the corpus originals, its attachment_text, combined_text, or manifests.
OCR outputs are candidates for human review, not automatically verified source text.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import local_path, read_csv, sha256, write_csv

OUTPUT_FIELDS = [
    'submission_id', 'document_number', 'source_url', 'original_path',
    'original_sha256', 'pages', 'pages_ocr_successful', 'pages_with_text',
    'ocr_chars', 'text_path', 'evidence_path', 'ocr_engine', 'ocr_method_version',
    'status', 'error', 'human_review_status',
]
METHOD_VERSION = '1.0'


def parse_tesseract_tsv(tsv: str) -> list[dict]:
    """Group words into lines without inventing text or changing word order."""
    buckets: dict[tuple, list[dict]] = {}
    for row in csv.DictReader(tsv.splitlines(), delimiter='\t'):
        if row.get('level') != '5' or not (row.get('text') or '').strip():
            continue
        try:
            conf = float(row['conf'])
            if conf < 0: continue
            key = tuple(int(row[k]) for k in ('page_num','block_num','par_num','line_num'))
            buckets.setdefault(key, []).append(row)
        except (ValueError, KeyError, TypeError):
            continue
    lines = []
    for key, words in sorted(buckets.items()):
        words.sort(key=lambda w: int(w['word_num']))
        text = ' '.join(w['text'].strip() for w in words if w['text'].strip())
        if not text: continue
        conf = round(sum(float(w['conf']) for w in words) / len(words) / 100, 4)
        lines.append({'text': text, 'confidence': conf, 'location': list(key)})
    return lines


def build_engine(engine: str, work: Path) -> tuple[str, list[str]]:
    if engine == 'vision':
        if sys.platform != 'darwin':
            raise RuntimeError('Apple Vision is available only on macOS; use --engine tesseract elsewhere')
        compiler = shutil.which('swiftc')
        if not compiler:
            raise RuntimeError('swiftc not found. Install Apple Command Line Tools or use --engine tesseract')
        binary = work/'vision_ocr'
        source = Path(__file__).with_name('macos_vision_ocr.swift')
        command = [compiler, str(source), '-o', str(binary)]
        print('Compiling local Apple Vision helper (once)...', flush=True)
        proc = subprocess.run(command, capture_output=True, text=True, timeout=240)
        if proc.returncode:
            raise RuntimeError('Swift compilation failed: ' + proc.stderr[-1400:])
        return 'apple_vision', [str(binary)]
    executable = shutil.which('tesseract')
    if not executable:
        raise RuntimeError('tesseract not found; on macOS use --engine vision (default)')
    return 'tesseract', [executable]


def recognize(image: Path, engine_name: str, prefix: list[str], timeout: int) -> list[dict]:
    if engine_name == 'apple_vision':
        cmd = prefix + [str(image)]
    else:
        cmd = prefix + [str(image), 'stdout', '-l', 'eng', '--psm', '3', 'tsv']
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode:
        raise RuntimeError((proc.stderr or proc.stdout)[-800:] or f'OCR exited {proc.returncode}')
    if engine_name == 'apple_vision':
        raw = json.loads(proc.stdout)
        return raw['lines']
    return parse_tesseract_tsv(proc.stdout)


def evidence_ready(out: Path, doc: dict, original_hash: str, engine: str) -> bool:
    if (doc.get('original_sha256') != original_hash or doc.get('ocr_engine') != engine
            or doc.get('ocr_method_version') != METHOD_VERSION
            or doc.get('status') != 'completed'):
        return False
    text_path = out / doc.get('text_path', '')
    evidence_path = out / doc.get('evidence_path', '')
    if not text_path.is_file() or not evidence_path.is_file(): return False
    try:
        data=json.loads(evidence_path.read_text(encoding='utf-8'))
        return (data['original_sha256'] == original_hash and
                data['ocr_text_sha256'] == sha256(text_path.read_bytes()) and
                data['ocr_method_version'] == METHOD_VERSION)
    except (KeyError, OSError, ValueError):
        return False


def recover_one(row: dict, base: Path, out: Path, engine: str, prefix: list[str],
                dpi: int, timeout: int) -> dict:
    import pymupdf
    sid,number=row['submission_id'],row['document_number']
    rel=row['original_path']
    result={field:'' for field in OUTPUT_FIELDS}
    result.update(submission_id=sid, document_number=number, source_url=row['source_url'],
                  original_path=rel, ocr_engine=engine,
                  ocr_method_version=METHOD_VERSION, human_review_status='pending')
    path=local_path(base,rel)
    if not path or not path.is_file():
        result['status']='missing_source'
        result['error']='Original PDF missing'
        return result
    result['original_sha256']=sha256(path.read_bytes())
    if not path.suffix.casefold()=='.pdf':
        result.update(status='not_pdf',error='Original document extension is not .pdf')
        return result
    doc_key=f'{sid}_{number}'
    pages=[];full_text=[];n_ok=0;n_with_text=0;errors=[]
    try:
        with pymupdf.open(path) as pdf:
            result['pages']=len(pdf)
            for page_index, page in enumerate(pdf):
                page_result={'page_number':page_index+1,'lines':[], 'error':'',
                             'text_chars':0,'dpi':dpi}
                try:
                    # Hard bound rendered pixel count to limit memory.
                    scale=dpi / 72.0
                    pixel_estimate=page.rect.width*page.rect.height*scale**2
                    if pixel_estimate>16_000_000:
                        scale *= (16_000_000/pixel_estimate)**0.5
                        page_result['effective_dpi']=round(scale*72,1)
                    with tempfile.TemporaryDirectory(prefix='fcc_page_') as temp:
                        image=Path(temp)/'page.png'
                        pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False,
                                            colorspace=pymupdf.csRGB)
                        pix.save(str(image))
                        del pix
                        lines=recognize(image,engine,prefix,timeout)
                    text='\n'.join(x['text'] for x in lines if (x.get('text') or '').strip()).strip()
                    page_result['lines']=lines
                    page_result['text_chars']=len(text)
                    full_text.append(f'===== OCR PAGE {page_index+1} =====\n{text}')
                    n_ok+=1
                    n_with_text+=int(bool(text))
                except Exception as ex:
                    error=f'{type(ex).__name__}: {str(ex)[:700]}'
                    page_result['error']=error
                    errors.append(f'page {page_index+1}: {error}')
                pages.append(page_result)
    except Exception as ex:
        errors.append(f'Cannot open PDF: {type(ex).__name__}: {str(ex)[:600]}')
    result['pages_ocr_successful']=n_ok
    result['pages_with_text']=n_with_text
    body='\n\n'.join(full_text).strip()+'\n' if full_text else ''
    result['ocr_chars']=sum(x['text_chars'] for x in pages)
    result['error']='; '.join(errors)[:1200]
    # An incomplete per-page extraction MUST NOT be labeled completed.
    result['status']='completed' if not errors and n_ok==len(pages) and len(pages)>0 else 'partial_or_error'
    if result['status']=='completed':
        # Save only when all pages executed, but preserve an empty result for visual review.
        text_rel=Path('text')/f'{doc_key}.txt'
        evidence_rel=Path('evidence')/f'{doc_key}.json'
        evidence={
            'submission_id':sid,'document_number':number,'source_url':row['source_url'],
            'original_path':rel,'original_sha256':result['original_sha256'],
            'ocr_engine':engine,'ocr_method_version':METHOD_VERSION,'dpi_requested':dpi,
            'page_results':pages,'ocr_text_sha256':sha256(body.encode('utf-8')),
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'human_review_status':'pending','reading_order_caveat':'Multi-column lines may need manual reordering',
        }
        (out/text_rel).parent.mkdir(parents=True,exist_ok=True)
        (out/evidence_rel).parent.mkdir(parents=True,exist_ok=True)
        (out/text_rel).write_text(body,encoding='utf-8')
        (out/evidence_rel).write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        result['text_path']=str(text_rel)
        result['evidence_path']=str(evidence_rel)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    ap.add_argument('--engine',choices=['vision','tesseract'],default='vision')
    ap.add_argument('--dpi',type=int,default=180)
    ap.add_argument('--timeout',type=int,default=120,help='Seconds per rendered page')
    ap.add_argument('--limit',type=int,default=None,help='Try first N PDFs; rerun without limit afterward')
    ap.add_argument('--force',action='store_true',help='Reprocess even if verified result already exists')
    ap.add_argument('--include-remaining-pdfs',action='store_true',
                    help='Include 12 separately audited PDF coverage gaps in the OCR queue')
    a=ap.parse_args()
    if a.dpi<72 or a.dpi>300:ap.error('--dpi must be from 72 to 300')
    if a.limit is not None and a.limit<1:ap.error('--limit must be positive')
    if a.timeout<1:ap.error('--timeout must be positive')
    base=a.corpus.expanduser().resolve()
    audit=base/'analysis_observatory'
    review_path=audit/'pdf_deep_review.csv'
    if not review_path.is_file():ap.error(f'Run scripts/pdf_deep_audit.py first; missing {review_path}')
    documents,_=read_csv(base/'documents_manifest.csv')
    by_key={(x['submission_id'],x['document_number']):x for x in documents}
    review,_=read_csv(review_path)
    initial_review_count=len(review)
    extra_count=0
    if a.include_remaining_pdfs:
        extra_path=audit/'additional_recovery/additional_pdf_review_queue.csv'
        if not extra_path.is_file():
            ap.error(f'Run scripts/reconcile_remaining_pdfs.py first; missing {extra_path}')
        extras,_=read_csv(extra_path)
        known={(x['submission_id'],x['document_number']) for x in review}
        for extra in extras:
            key=(extra['submission_id'],extra['document_number'])
            if extra['triage_class']!='ocr_candidate_existing_extraction_discrepancy':
                raise RuntimeError(f'Unexpected additional OCR queue classification: {key}')
            if key in known:
                raise RuntimeError(f'Duplicate main/additional OCR queue key: {key}')
            known.add(key)
        review += extras
        extra_count=len(extras)
    to_ocr=[]
    for r in review:
        key=(r['submission_id'],r['document_number'])
        if key not in by_key:raise RuntimeError(f'OCR queue contains an unknown attachment: {key}')
        d=by_key[key]
        if d['local_file']!=r['original_path']:
            raise RuntimeError(f'OCR queue source does not match current document manifest: {key}')
        original=local_path(base,d['local_file'])
        if original and original.is_file() and d['sha256']:
            actual_hash=sha256(original.read_bytes())
            if actual_hash.casefold()!=d['sha256'].casefold():
                raise RuntimeError(f'Source hash mismatch for {key}; resolve integrity discrepancy before OCR')
        if r['triage_class'] not in {'ocr_candidate_image_based','no_native_text_no_image_detected',
                                     'ocr_candidate_existing_extraction_discrepancy'}:
            continue
        to_ocr.append(r)
    if a.limit is not None:to_ocr=to_ocr[:a.limit]
    if not to_ocr:print('No flagged PDFs require OCR');return
    import pymupdf  # noqa: F401
    out=audit/'ocr_recovery'
    out.mkdir(parents=True,exist_ok=True)
    name,prefix=build_engine(a.engine,out)
    print(f'Using {name}; {len(to_ocr)} PDFs selected; originals never changed.',flush=True)
    manifest=out/'run_manifest.csv'
    previous,_=read_csv(manifest) if manifest.exists() else ([],OUTPUT_FIELDS)
    records={(x['submission_id'],x['document_number']):x for x in previous}
    for index,r in enumerate(to_ocr,1):
        sid,number=r['submission_id'],r['document_number']
        key=(sid,number)
        path=local_path(base,r['original_path'])
        original_hash=sha256(path.read_bytes()) if path and path.is_file() else ''
        current=records.get(key)
        if not a.force and current and evidence_ready(out,current,original_hash,name):
            print(f'[{index}/{len(to_ocr)}] {sid}/{number}: verified existing OCR, skipped',flush=True)
            continue
        rec=recover_one(r,base,out,name,prefix,a.dpi,a.timeout)
        records[key]=rec
        write_csv(manifest,sorted(records.values(),key=lambda x:(x['submission_id'],int(x['document_number']))),OUTPUT_FIELDS)
        print(f"[{index}/{len(to_ocr)}] {sid}/{number}: {rec['status']}, pages={rec['pages_ocr_successful']}/{rec['pages']}, chars={rec['ocr_chars']}",flush=True)
    complete=sum(x['status']=='completed' for x in records.values())
    nonempty=sum(x['status']=='completed' and int(x['ocr_chars'])>0 for x in records.values())
    errors=sum(x['status']!='completed' for x in records.values())
    summary={'generated_utc':datetime.now(timezone.utc).isoformat(),
             'method_version':METHOD_VERSION,'engine':name,
             'pdfs_in_full_review_queue':initial_review_count,
             'additional_pdf_gaps_included':extra_count,
             'total_pdf_review_queue_this_run':len(review),
             'pdfs_selected_this_run':len(to_ocr),
             'recorded_ocr_documents':len(records),'completed':complete,
             'completed_with_nonempty_text':nonempty,'incomplete_or_error':errors,
             'source_data_unchanged':True,
             'analysis_caveat':'OCR output is an unverified candidate until visually reviewed against original PDF; not automatically merged into canonical text.'}
    (out/'ocr_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)
    print('Per-document outputs:',out,flush=True)

if __name__=='__main__':main()
