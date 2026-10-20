#!/usr/bin/env python3
"""Read-only quality diagnostics and a human review sample for staged OCR.

Does not change the original PDFs, manifests, OCR transcripts or OCR evidence.
Recognition confidence is an OCR signal, not an independent accuracy estimate.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import local_path, read_csv, sha256, write_csv
from scripts.recover_pdf_ocr import evidence_ready

QC_FIELDS = [
    'submission_id', 'document_number', 'source_url', 'original_path',
    'ocr_text_path', 'status', 'human_review_status', 'pages',
    'pages_with_text', 'empty_ocr_pages', 'ocr_chars',
    'lines_total', 'median_line_confidence', 'low_confidence_lines',
    'evidence_hash_valid', 'original_sha256_valid',
    'quality_flags', 'review_priority'
]
SAMPLE_FIELDS = [
    'submission_id', 'document_number', 'source_url', 'original_path',
    'ocr_text_path', 'pages', 'ocr_chars', 'median_line_confidence',
    'quality_flags', 'review_status', 'reviewer', 'review_notes'
]


def inspect(row: dict, base: Path, out: Path, min_confidence: float) -> dict:
    """Check provenance, page coverage, OCR confidence and candidate completeness."""
    sid = row.get('submission_id', '')
    number = row.get('document_number', '')
    result = {key: '' for key in QC_FIELDS}
    result.update(
        submission_id=sid, document_number=number, source_url=row.get('source_url', ''),
        original_path=row.get('original_path', ''),
        ocr_text_path=row.get('text_path', ''),
        status=row.get('status', ''),
        human_review_status=row.get('human_review_status', 'pending'),
        pages=row.get('pages', '0'),
        pages_with_text=row.get('pages_with_text', '0'),
        ocr_chars=row.get('ocr_chars', '0'),
        empty_ocr_pages=0, lines_total=0, median_line_confidence='',
        low_confidence_lines=0, evidence_hash_valid=0, original_sha256_valid=0
    )
    problems = []
    if row.get('status') != 'completed':
        problems.append('ocr_not_completed')
    original = local_path(base, row.get('original_path', ''))
    original_hash = ''
    if original is None or not original.is_file():
        problems.append('original_pdf_missing')
    else:
        original_hash = sha256(original.read_bytes())
        if original_hash == row.get('original_sha256', ''):
            result['original_sha256_valid'] = 1
        else:
            problems.append('original_hash_mismatch')
    if original_hash and evidence_ready(out, row, original_hash, row.get('ocr_engine', '')):
        result['evidence_hash_valid'] = 1
    else:
        problems.append('ocr_evidence_missing_or_mismatch')
    evidence_rel = row.get('evidence_path', '')
    evidence = None
    if evidence_rel:
        evidence_file = (out / evidence_rel).resolve()
        if evidence_file.is_relative_to(out.resolve()) and evidence_file.is_file():
            try:
                evidence = json.loads(evidence_file.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                problems.append('evidence_unreadable')
        else:
            problems.append('evidence_file_missing_or_unsafe')
    else:
        problems.append('evidence_path_missing')
    if isinstance(evidence, dict):
        pages = evidence.get('page_results', [])
        if not isinstance(pages, list):
            pages = []
            problems.append('evidence_pages_invalid')
        expected = int(row.get('pages') or 0)
        if len(pages) != expected:
            problems.append('ocr_page_count_mismatch')
        if int(row.get('pages_ocr_successful') or 0) != expected:
            problems.append('incomplete_page_ocr')
        confidences = []
        empty = 0
        for page in pages:
            if page.get('error'):
                problems.append('page_error')
            if int(page.get('text_chars') or 0) == 0:
                empty += 1
            for line in page.get('lines', []):
                try:
                    c = float(line['confidence'])
                    if not 0 <= c <= 1:
                        raise ValueError('invalid confidence')
                    confidences.append(c)
                except (KeyError, TypeError, ValueError):
                    problems.append('invalid_line_confidence')
        result['empty_ocr_pages'] = empty
        result['lines_total'] = len(confidences)
        result['low_confidence_lines'] = sum(c < min_confidence for c in confidences)
        if confidences:
            med = statistics.median(confidences)
            result['median_line_confidence'] = round(med, 4)
            if med < min_confidence:
                problems.append('low_median_ocr_confidence')
        else:
            problems.append('no_recognized_text_lines')
        if empty:
            problems.append('one_or_more_ocr_pages_empty')
        if sum(int(p.get('text_chars') or 0) for p in pages) != int(row.get('ocr_chars') or 0):
            problems.append('manifest_ocr_char_count_mismatch')
    if not int(row.get('ocr_chars') or 0):
        problems.append('zero_ocr_characters')
    problems = sorted(set(problems))
    result['quality_flags'] = ';'.join(problems)
    result['review_priority'] = 'high' if problems else 'routine'
    return result


def select_sample(records: list[dict], n: int, seed: int = 20261020) -> list[dict]:
    """Sample anomalies plus a deterministic random cross-section of remaining documents."""
    if n <= 0:
        return []
    priority = sorted(records, key=lambda r: (
        r['review_priority'] != 'high',
        -len(r['quality_flags'].split(';')) if r['quality_flags'] else 0,
        (float(r['median_line_confidence'])
         if r['median_line_confidence'] != '' else -1),
        r['submission_id'], r['document_number']
    ))
    first = priority[:min(n // 2, len(priority))]
    seen = {(x['submission_id'], x['document_number']) for x in first}
    remaining = [r for r in records if (r['submission_id'], r['document_number']) not in seen]
    rng = random.Random(seed)
    rng.shuffle(remaining)
    chosen = first + remaining[:max(0, n - len(first))]
    return [dict(
        submission_id=r['submission_id'], document_number=r['document_number'],
        source_url=r['source_url'], original_path=r['original_path'],
        ocr_text_path=r['ocr_text_path'], pages=r['pages'],
        ocr_chars=r['ocr_chars'], median_line_confidence=r['median_line_confidence'],
        quality_flags=r['quality_flags'], review_status='', reviewer='', review_notes=''
    ) for r in chosen]


def analyze(base: Path, sample_size: int = 16, min_confidence: float = .8) -> dict:
    base = base.expanduser().resolve()
    analysis = base / 'analysis_observatory'
    out = analysis / 'ocr_recovery'
    manifest = out / 'run_manifest.csv'
    if not manifest.is_file():
        raise FileNotFoundError(f'Run OCR first: missing {manifest}')
    rows, _ = read_csv(manifest)
    reviewed = [inspect(r, base, out, min_confidence) for r in rows]
    write_csv(out / 'ocr_qc_documents.csv', reviewed, QC_FIELDS)
    sample = select_sample(reviewed, min(sample_size, len(reviewed)))
    # The generated file is overwritten on rerun. Manual annotations must be saved
    # separately and NEVER written into this generated file.
    write_csv(out / 'ocr_review_sample_generated.csv', sample, SAMPLE_FIELDS)
    deep, _ = read_csv(analysis / 'pdf_deep_review.csv')
    summary = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'review_queue_pdf_count': len(deep),
        'ocr_documents_recorded': len(rows),
        'completed_with_nonempty_text': sum(
            r['status'] == 'completed' and int(r['ocr_chars'] or 0) > 0 for r in rows),
        'validated_original_sha256_count': sum(int(r['original_sha256_valid']) for r in reviewed),
        'validated_ocr_evidence_count': sum(int(r['evidence_hash_valid']) for r in reviewed),
        'high_priority_review_count': sum(r['review_priority'] == 'high' for r in reviewed),
        'quality_flag_counts': dict(Counter(flag for r in reviewed
            for flag in r['quality_flags'].split(';') if flag)),
        'sampled_for_human_review': len(sample),
        'minimum_line_confidence_flag_threshold': min_confidence,
        'methodological_warning': (
            'OCR confidence is NOT an observed transcription accuracy rate. '
            'All OCR results remain candidate text until visually checked; '
            'the original corpus, originals and OCR evidence were unchanged.')
    }
    (out / 'ocr_qc_summary.json').write_text(
        json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path,
        default=Path.home() / 'Downloads/fcc_complete_corpus')
    parser.add_argument('--sample-size', type=int, default=16)
    parser.add_argument('--min-confidence', type=float, default=.8)
    args = parser.parse_args()
    if args.sample_size < 0:
        parser.error('--sample-size must be nonnegative')
    if not 0 <= args.min_confidence <= 1:
        parser.error('--min-confidence must be between 0 and 1')
    report = analyze(args.corpus, args.sample_size, args.min_confidence)
    print(json.dumps(report, indent=2))
    print('Read-only OCR QC:', args.corpus / 'analysis_observatory/ocr_recovery')


if __name__ == '__main__':
    main()
