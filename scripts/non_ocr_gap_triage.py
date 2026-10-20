#!/usr/bin/env python3
"""Read-only triage for filings whose missing content is NOT explained by flagged PDFs.

Outputs filing IDs and technical extraction metadata, never original text or filer names.
"""
from __future__ import annotations
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import local_path, read_csv, write_csv

OUTPUT_FIELDS = [
    'submission_id','source_url','submission_type','status',
    'diagnosis','document_count','direct_text_exists','direct_text_chars',
    'combined_text_file_count','documents_without_extracted_text',
    'document_types','originals_missing','text_files_missing',
    'original_path_list','attachment_source_urls'
]


def triage_one(row: dict, by_sid: dict, base: Path) -> dict:
    sid = row['submission_id']
    docs = by_sid.get(sid, [])
    direct = base / 'direct_text' / (sid + '.txt')
    direct_chars = len(direct.read_text(encoding='utf-8-sig',errors='replace').strip()) if direct.is_file() else 0
    missing_originals = 0
    missing_text = 0
    empty_attachment = 0
    ext = []
    doc_paths = []
    urls = []
    blob_only = False
    for d in docs:
        src = local_path(base, d.get('local_file', ''))
        parsed = Path(d.get('filename', '')).suffix.lower() or (src.suffix.lower() if src else '')
        ext.append(parsed or '<no extension>')
        doc_paths.append(d.get('local_file', ''))
        urls.append(d.get('url', ''))
        if src is None or not src.is_file():
            missing_originals += 1
        elif parsed == '.txt' and src.stat().st_size <= 512:
            original = src.read_text(encoding='utf-8',errors='replace').strip()
            blob_only = blob_only or original.lower().startswith('blob:')
        text_path = local_path(base, d.get('text_file', ''))
        if d.get('text_file') and (text_path is None or not text_path.is_file()):
            missing_text += 1
        if not text_path or not text_path.is_file() or not text_path.read_text(encoding='utf-8-sig',errors='replace').strip():
            empty_attachment += 1
    if int(row.get('combined_text_file_count') or 0) != 1:
        diagnosis = 'combined_text_file_missing_or_ambiguous'
    elif blob_only:
        diagnosis = 'original_attachment_only_temporary_blob_link'
    elif missing_originals:
        diagnosis = 'missing_original_attachment'
    elif missing_text or empty_attachment:
        diagnosis = 'non_pdf_attachment_text_missing_or_empty'
    elif direct_chars == 0 and not docs:
        diagnosis = 'no_direct_text_and_no_attachments'
    elif direct_chars or docs:
        diagnosis = 'existing_source_text_needs_reconciliation'
    else:
        diagnosis = 'needs_manual_investigation'
    return {
        'submission_id': sid, 'source_url': row['source_url'],
        'submission_type': row['submission_type'], 'status': row['status'],
        'diagnosis': diagnosis, 'document_count': len(docs),
        'direct_text_exists': int(direct.is_file()), 'direct_text_chars': direct_chars,
        'combined_text_file_count': row.get('combined_text_file_count',''),
        'documents_without_extracted_text': empty_attachment,
        'document_types': ';'.join(ext),
        'originals_missing': missing_originals, 'text_files_missing': missing_text,
        'original_path_list': ';'.join(doc_paths),
        'attachment_source_urls': ';'.join(urls)
    }


def analyze(base: Path) -> dict:
    base = base.expanduser().resolve()
    analysis = base / 'analysis_observatory'
    gaps, _ = read_csv(analysis / 'coverage_gap_review.csv')
    docs, _ = read_csv(base / 'documents_manifest.csv')
    by_sid = defaultdict(list)
    for d in docs:
        by_sid[d['submission_id']].append(d)
    # Covers the exact 12 non-flagged PDF gaps PLUS any missing combined text file.
    unresolved = [r for r in gaps if int(r['pdf_flagged_count'] or 0) == 0
                  or int(r.get('combined_text_file_count') or 0) != 1]
    out = [triage_one(row, by_sid, base) for row in unresolved]
    out.sort(key=lambda r:(r['diagnosis'],r['submission_id']))
    write_csv(analysis/'non_ocr_gap_triage.csv',out,OUTPUT_FIELDS)
    summary = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'filings_for_individual_follow_up': len(out),
        'diagnoses': dict(Counter(r['diagnosis'] for r in out)),
        'disclaimer': 'Technical triage only. No public-comment positions inferred.',
        'source_documents_or_manifests_changed': False
    }
    (analysis/'non_ocr_gap_summary.json').write_text(
        json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    a=p.parse_args()
    print(json.dumps(analyze(a.corpus),indent=2))


if __name__=='__main__':
    main()
