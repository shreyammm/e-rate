#!/usr/bin/env python3
"""Build two immutable, per-filing research-text views with source-level provenance.

baseline: direct ECFS text and non-OCR attachment text.
augmented: baseline + hash-verified staged OCR candidate passages.
Neither view implies valid policy-position coding or human-verified OCR.
Does not modify original documents, historical combined text, or manifests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

# Allow `python3 scripts/build_research_snapshot.py` from any working directory.
# Direct script execution sets sys.path[0] to scripts/, not the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from erate.engine import (DOCFIELDS, FIELDS, local_path, normalized_text, read_combined,
                          read_csv, sha256, substantive_text, write_csv)
from scripts.recover_pdf_ocr import evidence_ready

SNAPSHOT_VERSION='1.0.0'
SEGMENT_FIELDS=['submission_id','segment_id','document_number','source_kind','source_url',
                'original_path','original_sha256','transcript_path','transcript_sha256',
                'text_sha256','text_chars','included_baseline','included_augmented',
                'evidence_path','review_status']
FILING_FIELDS=['submission_id','date_submission','submission_type','filer_raw','source_url',
               'status','agency_record_candidate','document_count','baseline_chars','augmented_chars',
               'baseline_sha256','augmented_sha256','baseline_segment_count',
               'augmented_segment_count','ocr_candidate_attachment_count',
               'has_unreviewed_ocr','coverage_class','quality_flags']
AGENCY_TYPES={'nprm','notice','pub notice','public draft'}
HEADINGS=re.compile(r'^===== (?:OCR|NATIVE) PAGE \d+ =====$')
PLACEHOLDERS={'no text found','no extractable text','ocr unavailable',
              'scanned document','text extraction failed'}


def clean_passage(raw: str) -> str:
    """Remove only known internal wrapper lines; never rewrite source evidence."""
    cleaned,_=substantive_text(raw)
    body='\n'.join(line for line in cleaned.splitlines()
                   if not HEADINGS.fullmatch(line.strip())).strip()
    if body.casefold() in PLACEHOLDERS:
        return ''
    return body


def source_text(path: Path | None) -> tuple[str, str]:
    if path is None or not path.is_file():
        return '', ''
    raw=path.read_bytes()
    return clean_passage(raw.decode('utf-8-sig',errors='replace')),sha256(raw)


def count_duplicates(rows: list[dict], col: str) -> dict:
    groups=Counter(r[col] for r in rows if r[col])
    return {
        'distinct_nonempty_text_hashes':len(groups),
        'exact_duplicate_clusters':sum(count>1 for count in groups.values()),
        'filings_in_exact_duplicate_clusters':sum(count for count in groups.values() if count>1)
    }


def build(base: Path, run_id: str = 'ocr_candidate_v1') -> dict:
    base=base.expanduser().resolve()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',run_id):
        raise ValueError('run_id must contain only letters, digits, underscores and hyphens')
    analysis=base/'analysis_observatory'
    dest=analysis/f'research_snapshot_{run_id}'
    if dest.exists():
        raise FileExistsError(f'Immutable snapshot already exists: {dest}. Use a NEW --run-id.')
    filings,filing_fields=read_csv(base/'filings_manifest.csv')
    documents,document_fields=read_csv(base/'documents_manifest.csv')
    if not set(FIELDS).issubset(filing_fields) or not set(DOCFIELDS).issubset(document_fields):
        raise ValueError('The FCC manifest schema differs from the audited version')
    if len({r['submission_id'] for r in filings})!=len(filings):
        raise ValueError('Duplicate submission IDs')
    idset={r['submission_id'] for r in filings}
    document_keys=[(d['submission_id'],d['document_number']) for d in documents]
    if len(set(document_keys))!=len(document_keys) or any(s not in idset for s,n in document_keys):
        raise ValueError('Document identifiers duplicated or not in filing manifest')
    docs_by_id=defaultdict(list)
    for d in documents:docs_by_id[d['submission_id']].append(d)
    ocr_root=analysis/'ocr_recovery'
    ocr_path=ocr_root/'run_manifest.csv'
    ocr_list,_=read_csv(ocr_path) if ocr_path.is_file() else ([],[])
    ocr_records={(r['submission_id'],r['document_number']):r for r in ocr_list}
    if len(ocr_records)!=len(ocr_list):
        raise ValueError('Duplicate OCR manifest keys')
    if any(key not in document_keys for key in ocr_records):
        raise ValueError('OCR manifest references unknown source attachments')
    if not ocr_records:
        raise ValueError('No staged OCR candidate files found; run the OCR workflow first')

    analysis.mkdir(parents=True,exist_ok=True)
    working=Path(tempfile.mkdtemp(prefix='.research_snapshot_staging_',dir=analysis))
    segments=[];inventory=[];unmatched=[];ocr_used=set()
    try:
        (working/'baseline_text').mkdir()
        (working/'ocr_augmented_text').mkdir()
        for f in filings:
            sid=f['submission_id']
            base_parts=[];aug_parts=[];flags=[];n_ocr=0
            direct_rel=f'direct_text/{sid}.txt'
            direct_path=local_path(base,direct_rel)
            direct,source_hash=source_text(direct_path)
            if direct:
                base_parts.append(direct);aug_parts.append(direct)
                segments.append({
                    'submission_id':sid,'segment_id':f'{sid}:direct','document_number':'',
                    'source_kind':'fcc_ecfs_direct_text','source_url':f['source_url'],
                    'original_path':direct_rel,'original_sha256':source_hash,
                    'transcript_path':direct_rel,'transcript_sha256':source_hash,
                    'text_sha256':sha256(direct.encode()),'text_chars':len(direct),
                    'included_baseline':1,'included_augmented':1,'evidence_path':'',
                    'review_status':'source_text_unreviewed'
                })
            elif int(f.get('text_data_chars') or 0)>0:
                flags.append('missing_or_empty_direct_text')
            for d in sorted(docs_by_id[sid],key=lambda r:int(r['document_number'])):
                key=(sid,d['document_number'])
                source=local_path(base,d['local_file'])
                if source is None or not source.is_file():
                    raise FileNotFoundError(f'Missing original attachment for {sid}/{d["document_number"]}')
                original_hash=sha256(source.read_bytes())
                if not d['sha256'] or original_hash.lower()!=d['sha256'].lower():
                    raise ValueError(f'Original attachment SHA-256 mismatch for {key}')
                ocr=ocr_records.get(key)
                if ocr:
                    if not evidence_ready(ocr_root,ocr,original_hash,ocr.get('ocr_engine','')):
                        raise ValueError(f'Staged OCR/evidence integrity or completion failure for {key}')
                    if int(ocr.get('pages') or 0)!=int(ocr.get('pages_ocr_successful') or 0):
                        raise ValueError(f'Incomplete OCR pages for {key}')
                    transcript=local_path(ocr_root,ocr['text_path'])
                    evidence_path=local_path(ocr_root,ocr['evidence_path'])
                    if transcript is None or evidence_path is None:
                        raise ValueError(f'Unsafe OCR source paths for {key}')
                    body,transcript_hash=source_text(transcript)
                    if not body:
                        flags.append('ocr_candidate_empty')
                    else:
                        aug_parts.append(body);n_ocr+=1
                    ocr_used.add(key)
                    kind='ocr_candidate_apple_vision' if ocr['ocr_engine']=='apple_vision' else 'ocr_candidate_other'
                    selected_rel=str(transcript.relative_to(base))
                    evidence_rel=str(evidence_path.relative_to(base))
                    review_status='ocr_candidate_not_human_verified'
                    include_base=0;include_aug=int(bool(body))
                else:
                    textpath=local_path(base,d.get('text_file',''))
                    body,transcript_hash=source_text(textpath)
                    if not body:
                        flags.append('attachment_text_empty_or_placeholder')
                    else:
                        base_parts.append(body);aug_parts.append(body)
                    kind='attachment_existing_extraction'
                    selected_rel=str(textpath.relative_to(base)) if textpath and textpath.is_file() else ''
                    evidence_rel=''
                    review_status='source_text_unreviewed'
                    include_base=int(bool(body));include_aug=int(bool(body))
                segments.append({
                    'submission_id':sid,'segment_id':f'{sid}:document:{d["document_number"]}',
                    'document_number':d['document_number'],'source_kind':kind,
                    'source_url':d['url'],'original_path':d['local_file'],
                    'original_sha256':original_hash,'transcript_path':selected_rel,
                    'transcript_sha256':transcript_hash,'text_sha256':sha256(body.encode()) if body else '',
                    'text_chars':len(body),'included_baseline':include_base,
                    'included_augmented':include_aug,'evidence_path':evidence_rel,
                    'review_status':review_status
                })
            baseline='\n\n'.join(base_parts).strip()
            augmented='\n\n'.join(aug_parts).strip()
            if baseline:(working/'baseline_text'/f'{sid}.txt').write_text(baseline+'\n',encoding='utf-8')
            if augmented:(working/'ocr_augmented_text'/f'{sid}.txt').write_text(augmented+'\n',encoding='utf-8')
            existing,_,n_existing=read_combined(base,sid)
            if not augmented and clean_passage(existing):
                flags.append('existing_combined_has_unreconciled_substantive_text')
                unmatched.append(sid)
            if n_existing!=1: flags.append('missing_or_ambiguous_historical_combined_text')
            inventory.append({
                'submission_id':sid,'date_submission':f['date_submission'],
                'submission_type':f['submission_type'],'filer_raw':f['filers'],
                'source_url':f['source_url'],'status':f['status'],
                'agency_record_candidate':int(f['submission_type'].strip().casefold() in AGENCY_TYPES),
                'document_count':len(docs_by_id[sid]),
                'baseline_chars':len(baseline),'augmented_chars':len(augmented),
                'baseline_sha256':sha256(normalized_text(baseline).encode()) if baseline else '',
                'augmented_sha256':sha256(normalized_text(augmented).encode()) if augmented else '',
                'baseline_segment_count':len(base_parts),'augmented_segment_count':len(aug_parts),
                'ocr_candidate_attachment_count':n_ocr,
                'has_unreviewed_ocr':int(n_ocr>0),
                'coverage_class':'has_ocr_candidate' if n_ocr else ('native_text_only' if augmented else 'metadata_only'),
                'quality_flags':';'.join(sorted(set(flags)))
            })
        if len(ocr_used)!=len(ocr_records):
            raise ValueError('Not all OCR records were linked to a filing')
        write_csv(working/'research_inventory.csv',inventory,FILING_FIELDS)
        write_csv(working/'source_segments.csv',segments,SEGMENT_FIELDS)
        summary={
            'version':SNAPSHOT_VERSION,'run_id':run_id,
            'created_utc':datetime.now(timezone.utc).isoformat(),
            'indexed_filings':len(inventory),'indexed_document_attachments':len(documents),
            'baseline_filings_with_text':sum(int(x['baseline_chars'])>0 for x in inventory),
            'augmented_filings_with_text':sum(int(x['augmented_chars'])>0 for x in inventory),
            'filings_with_ocr_candidates':sum(x['has_unreviewed_ocr'] for x in inventory),
            'ocr_attachment_candidates_included':len(ocr_used),
            'filings_metadata_only_even_with_ocr':sum(not x['augmented_chars'] for x in inventory),
            'agency_type_candidates_unverified':sum(x['agency_record_candidate'] for x in inventory),
            'filings_requiring_existing_combined_text_reconciliation':len(unmatched),
            'baseline_duplicates':count_duplicates(inventory,'baseline_sha256'),
            'augmented_duplicates':count_duplicates(inventory,'augmented_sha256'),
            'inputs_sha256':{
                'filings_manifest.csv':sha256((base/'filings_manifest.csv').read_bytes()),
                'documents_manifest.csv':sha256((base/'documents_manifest.csv').read_bytes()),
                'ocr_recovery/run_manifest.csv':sha256(ocr_path.read_bytes())},
            'human_verified_ocr_documents':0,
            'warnings':[
                'OCR-augmented text is an exploratory candidate, NOT human-verified transcription.',
                'Do not publish stakeholder/position statistics from OCR candidates before validation.',
                'Agency-record candidates are guessed from submission type; require provenance verification.',
                'Exact filers in raw metadata are not verified unique people.',
                'Public comments are self-selected and are not population opinion polls.',
                'The source manifests and original combined text have NOT been modified.'
            ]
        }
        (working/'snapshot_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        working.rename(dest)
        return summary
    except Exception:
        shutil.rmtree(working,ignore_errors=True)
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--run-id',default='ocr_candidate_v1')
    args=p.parse_args()
    report=build(args.corpus,args.run_id)
    print(json.dumps(report,indent=2))
    print('Private, immutable local output:',args.corpus/'analysis_observatory'/f'research_snapshot_{args.run_id}')


if __name__=='__main__':
    main()
