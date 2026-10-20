#!/usr/bin/env python3
"""Stage forensic PDF-text checks for non-OCR coverage gaps.

Reads existing originals/manifests. Never rewrites source PDF, attachment text,
combined text, filing status, or OCR evidence. Candidate outputs stay local.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import local_path, read_csv, read_combined, sha256, write_csv

DIAGNOSTIC_FIELDS = [
    'submission_id', 'document_number', 'submission_type', 'source_url',
    'original_path', 'original_sha256', 'previous_attachment_path',
    'previous_attachment_chars', 'previous_attachment_sha256',
    'previous_combined_file_count', 'previous_combined_chars',
    'pdf_pages', 'pdf_pages_with_native_text', 'pdf_pages_with_images',
    'native_text_chars', 'native_candidate_path', 'native_evidence_path',
    'diagnosis', 'ocr_staging_required', 'review_status'
]
QUEUE_FIELDS = [
    'submission_id', 'document_number', 'source_url', 'original_path',
    'triage_class', 'original_sha256'
]
TRIAGE_CLASS = 'ocr_candidate_existing_extraction_discrepancy'


def select_remaining_pdf_gaps(gaps: list[dict]) -> list[str]:
    """Only unflagged, zero-substantive-text PDFs; exclude known link-only."""
    return sorted(set(r['submission_id'] for r in gaps
                      if r.get('diagnosis') == 'existing_source_text_needs_reconciliation'))


def analyze(base: Path) -> dict:
    import pymupdf

    base = base.expanduser().resolve()
    analysis = base / 'analysis_observatory'
    gaps, _ = read_csv(analysis / 'non_ocr_gap_triage.csv')
    documents, _ = read_csv(base / 'documents_manifest.csv')
    filings, _ = read_csv(base / 'filings_manifest.csv')
    filer_by_id = {r['submission_id']: r for r in filings}
    by_id = defaultdict(list)
    for doc in documents:
        by_id[doc['submission_id']].append(doc)

    target_ids = select_remaining_pdf_gaps(gaps)
    if not target_ids:
        raise ValueError('No additional PDF gaps found; run non_ocr_gap_triage.py first')
    out = analysis / 'additional_recovery'
    originals = []
    queue = []
    for sid in target_ids:
        if sid not in filer_by_id:
            raise ValueError(f'Unknown filing {sid}')
        docs = by_id.get(sid, [])
        if len(docs) != 1 or not docs[0]['local_file'].casefold().endswith('.pdf'):
            raise ValueError(f'Expected exactly one local PDF for gap {sid}; manually investigate')
        d = docs[0]
        pdf_path = local_path(base, d['local_file'])
        if pdf_path is None or not pdf_path.is_file():
            raise FileNotFoundError(f'Missing original PDF {sid}: {d["local_file"]}')
        pdf_bytes = pdf_path.read_bytes()
        original_hash = sha256(pdf_bytes)
        if not d.get('sha256') or original_hash.casefold() != d['sha256'].casefold():
            raise ValueError(f'Original attachment SHA-256 does not match manifest for {sid}')
        previous_path = local_path(base, d.get('text_file', ''))
        previous_text = (previous_path.read_text(encoding='utf-8-sig', errors='replace')
                         if previous_path is not None and previous_path.is_file() else '')
        combined, _, combined_files = read_combined(base, sid)
        native_pages = []
        with pymupdf.open(pdf_path) as pdf:
            page_count = len(pdf)
            pages_with_text = 0
            pages_with_images = 0
            for page in pdf:
                extracted = page.get_text('text', sort=True).strip()
                native_pages.append(extracted)
                pages_with_text += bool(extracted)
                try:
                    pages_with_images += bool(page.get_image_info())
                except Exception:
                    pages_with_images += bool(page.get_images(full=True))
        native_body = '\n\n'.join(
            f'===== NATIVE PAGE {n} =====\n{body}'
            for n, body in enumerate(native_pages, 1)).strip() + '\n'
        raw_chars = sum(len(x) for x in native_pages)
        filename = f'{sid}_{d["document_number"]}'
        native_rel = ''
        evidence_rel = ''
        if raw_chars > 0:
            native_rel = str(Path('native_text') / f'{filename}.txt')
            evidence_rel = str(Path('native_evidence') / f'{filename}.json')
            (out / native_rel).parent.mkdir(parents=True, exist_ok=True)
            (out / evidence_rel).parent.mkdir(parents=True, exist_ok=True)
            (out / native_rel).write_text(native_body, encoding='utf-8')
            evidence = {
                'submission_id': sid, 'document_number': d['document_number'],
                'original_sha256': original_hash, 'native_text_sha256':
                    sha256(native_body.encode('utf-8')),
                'source_url': d['url'], 'method': 'pymupdf_page_get_text_sort_true',
                'pages': [{'page': i+1, 'native_chars': len(p)}
                          for i, p in enumerate(native_pages)],
                'generated_utc': datetime.now(timezone.utc).isoformat(),
                'human_review_status': 'pending',
                'warning': 'Native PDF text is an unverified candidate, not confirmed complete text'
            }
            (out / evidence_rel).write_text(
                json.dumps(evidence, indent=2)+'\n', encoding='utf-8')
        diagnosis = ('native_text_candidate_for_manual_comparison'
                     if raw_chars > 100 else
                     ('image_based_or_mixed_pdf_ocr_recommended'
                      if pages_with_images else
                      'minimal_native_text_pdf_requires_visual_review'))
        originals.append({
            'submission_id':sid, 'document_number':d['document_number'],
            'submission_type':filer_by_id[sid]['submission_type'],
            'source_url':d['url'], 'original_path':d['local_file'],
            'original_sha256':original_hash,
            'previous_attachment_path':d.get('text_file', ''),
            'previous_attachment_chars':len(previous_text),
            'previous_attachment_sha256':sha256(previous_text.encode('utf-8')),
            'previous_combined_file_count':combined_files,
            'previous_combined_chars':len(combined),
            'pdf_pages':page_count,
            'pdf_pages_with_native_text':pages_with_text,
            'pdf_pages_with_images':pages_with_images,
            'native_text_chars':raw_chars, 'native_candidate_path':native_rel,
            'native_evidence_path':evidence_rel, 'diagnosis':diagnosis,
            'ocr_staging_required':1, 'review_status':'pending'
        })
        queue.append({
            'submission_id':sid, 'document_number':d['document_number'],
            'source_url':d['url'], 'original_path':d['local_file'],
            'triage_class':TRIAGE_CLASS, 'original_sha256':original_hash
        })
    write_csv(out / 'additional_pdf_diagnostics.csv', originals, DIAGNOSTIC_FIELDS)
    write_csv(out / 'additional_pdf_review_queue.csv', queue, QUEUE_FIELDS)
    summary = {
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'newly_triaged_pdf_attachments':len(queue),
        'pdfs_with_candidate_native_text_more_than_100_chars':
            sum(r['native_text_chars']>100 for r in originals),
        'pdfs_with_any_native_text':
            sum(r['native_text_chars']>0 for r in originals),
        'pdfs_with_images':
            sum(r['pdf_pages_with_images']>0 for r in originals),
        'diagnoses':dict(Counter(r['diagnosis'] for r in originals)),
        'filing_ids':target_ids,
        'method': 'Read-only original-PDF inspection with independent native text staging; '
                  'OCR on the additional queue still requires a separate command',
        'input_corpus_unchanged': True
    }
    (out / 'additional_pdf_summary.json').write_text(
        json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,
        default=Path.home()/'Downloads/fcc_complete_corpus')
    args = parser.parse_args()
    print(json.dumps(analyze(args.corpus), indent=2))


if __name__ == '__main__':
    main()
