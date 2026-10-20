"""Read-only inventory, provenance audit and exact-duplicate/participation analysis.

No source files modified. No API calls. No guesswork about policy position or filer identity.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ['submission_id','date_submission','submission_type','filers','text_data_chars','document_count',
          'documents_downloaded','documents_extracted','status','issues','source_url']
DOCFIELDS = ['submission_id','document_number','filename','url','local_file','sha256','http_status',
             'file_status','text_file','text_chars','extraction_status','error']
SUSPICIOUS_TEXT = ('no extractable text','ocr unavailable','no text found','scanned document')
AGENCY_TYPE_CANDIDATES = {'nprm','notice','pub notice','public draft'}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_text(s: str) -> str:
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', s)).strip().casefold()


def filer_key(s: str) -> str:
    """Exact-normalized filer field, NOT a verified unique person.

    Intentionally does not merge different spellings, aliases, or composites.
    """
    return normalized_text(s)


def read_csv(path: Path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)


def local_path(base: Path, relative: str) -> Path | None:
    if not relative: return None
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError(f'UNSAFE local path in manifest: {relative}')
    result = (base / p).resolve()
    if not result.is_relative_to(base.resolve()):
        raise ValueError(f'Path escapes corpus: {relative}')
    return result


def read_combined(base: Path, sid: str):
    # Do not silently select one file if two candidate conventions both exist.
    candidates = [base/'combined_text'/f'{sid}.txt', base/'combined_text'/f'{sid}_combined.txt']
    matches = [p for p in candidates if p.is_file()]
    if len(matches) != 1: return '', '', len(matches)
    p = matches[0]
    return p.read_text(encoding='utf-8-sig', errors='replace'), str(p.relative_to(base)), 1


def analyze(base: Path, out: Path):
    base = base.expanduser().resolve();out = out.expanduser().resolve()
    filings, fields = read_csv(base/'filings_manifest.csv')
    documents, docfields = read_csv(base/'documents_manifest.csv')
    if not set(FIELDS).issubset(fields) or not set(DOCFIELDS).issubset(docfields):
        raise ValueError('Unrecognized manifest schema; aborting to avoid silent misinterpretation')
    ids=[r['submission_id'] for r in filings]
    if len(ids) != len(set(ids)) or not all(re.fullmatch(r'\d+',sid) for sid in ids):
        raise ValueError('Duplicate or invalid submission IDs; manual reconciliation required')
    doc_keys=[(r['submission_id'],r['document_number']) for r in documents]
    if len(doc_keys) != len(set(doc_keys)):
        raise ValueError('Duplicate document keys in manifest')
    valid_ids=set(ids)
    if any(sid not in valid_ids for sid,_ in doc_keys):
        raise ValueError('Documents reference filing IDs absent from filings manifest')
    docs_by_sid=defaultdict(list)
    audit=[]
    for d in documents:
        sid=d['submission_id']; docs_by_sid[sid].append(d)
        errors=[]
        original=local_path(base,d['local_file']); textfile=local_path(base,d['text_file'])
        orig_exists=bool(original and original.is_file())
        text_exists=bool(textfile and textfile.is_file())
        orig_sha=''
        if not orig_exists: errors.append('original_missing')
        else:
            orig_sha=sha256(original.read_bytes())
            if d['sha256'] and orig_sha.lower()!=d['sha256'].lower(): errors.append('sha256_mismatch')
        if d['text_file'] and not text_exists:errors.append('attachment_text_missing')
        extracted=''
        if text_exists:
            extracted=textfile.read_text(encoding='utf-8-sig', errors='replace')
            if d['text_chars'].isdigit() and int(d['text_chars'])!=len(extracted):
                errors.append('manifest_text_length_mismatch')
            if '\ufffd' in extracted:errors.append('replacement_character')
        is_pdf=bool((d['filename'] or '').lower().endswith('.pdf') or (original and original.suffix.lower()=='.pdf'))
        if is_pdf and len(extracted.strip())<=100:
            errors.append('pdf_text_100_chars_or_fewer_review_ocr')
        if text_exists and any(s in normalized_text(extracted[:300]) for s in SUSPICIOUS_TEXT):
            errors.append('possibly_extraction_placeholder')
        if not text_exists and d['extraction_status'] not in ('link_only_no_substantive_text',''):
            errors.append('extraction_marked_but_text_missing')
        audit.append({
            'submission_id':sid,'document_number':d['document_number'],'filename':d['filename'],
            'is_pdf':int(is_pdf),'original_path':d['local_file'], 'original_exists':int(orig_exists),
            'original_hash_matches':int(bool(orig_exists and (not d['sha256'] or orig_sha.lower()==d['sha256'].lower()))),
            'text_path':d['text_file'],'text_exists':int(text_exists),'text_chars_actual':len(extracted),
            'extraction_status':d['extraction_status'],'quality_flags':';'.join(errors),
            'source_url':d['url']
        })
    rows=[]; missing_text=[]
    by_filer=defaultdict(list); by_hash=defaultdict(list)
    for f in filings:
        sid=f['submission_id'];text,rel,num_matches=read_combined(base,sid)
        digest=sha256(normalized_text(text).encode('utf-8')) if text.strip() else ''
        fk=filer_key(f['filers']); words=len(text.split()); chars=len(text.strip()); flags=[]
        if num_matches!=1: flags.append('combined_text_'+('missing' if num_matches==0 else 'ambiguous'))
        if chars==0: flags.append('no_substantive_combined_text')
        elif chars<=100: flags.append('short_combined_text_review')
        if '\ufffd' in text:flags.append('replacement_character')
        if re.fullmatch(r'blob:\S+', text.strip(), flags=re.I):flags.append('blob_only')
        if '<html' in text[:200].casefold():flags.append('html_in_combined_text')
        doclist=docs_by_sid[sid]
        if f['document_count'].isdigit() and int(f['document_count'])!=len(doclist):
            flags.append('filing_document_count_mismatch')
        if f['status']!='complete': flags.append('not_marked_complete')
        if '|' in f['filers']:flags.append('composite_filer_field_review')
        if not fk:flags.append('no_filer_name')
        record={
            'submission_id':sid,'date_submission':f['date_submission'], 'submission_type':f['submission_type'],
            'filer_raw':f['filers'], 'filer_key':fk, 'filer_identity_method':'normalized_exact_field',
            'agency_record_candidate':int(f['submission_type'].strip().casefold() in AGENCY_TYPE_CANDIDATES),
            'status':f['status'],'source_url':f['source_url'],'document_count':len(doclist),
            'combined_text_path':rel,'text_chars':chars,'text_words':words,
            'normalized_text_sha256':digest,'quality_flags':';'.join(flags),
        }
        rows.append(record)
        if fk:by_filer[fk].append(sid)
        if digest:by_hash[digest].append(sid)
        if flags:missing_text.append({'submission_id':sid,'flags':';'.join(flags),'source_url':f['source_url']})
    # Exact duplicates in normalized text, not duplicate filing records.
    dup_clusters=[];hash_to_cluster={}
    for digest, sids in sorted(by_hash.items(),key=lambda a:(-len(a[1]),a[0])):
        if len(sids)<2:continue
        cluster_id=f'exact_{len(dup_clusters)+1:05}'
        dup_clusters.append({'cluster_id':cluster_id,'normalized_text_sha256':digest,
                            'filing_count':len(sids),'submission_ids':';'.join(sids)})
        hash_to_cluster[digest]=cluster_id
    for r in rows:r['exact_duplicate_cluster_id']=hash_to_cluster.get(r['normalized_text_sha256'],'')
    filer_rows=[]
    for fk,sids in sorted(by_filer.items(), key=lambda a:(-len(a[1]),a[0])):
        relevant=[r for r in rows if r['submission_id'] in set(sids)]
        filer_rows.append({'filer_key':fk,'display_filer':relevant[0]['filer_raw'],
                           'filing_count':len(sids),'unique_substantive_texts':len({r['normalized_text_sha256'] for r in relevant if r['normalized_text_sha256']}),
                           'composite_name_field':int(any('|' in r['filer_raw'] for r in relevant)),
                           'submission_ids':';'.join(sids),
                           'identity_caveat':'Exact-normalized filer string, not confirmed unique person'})
    # Stable sorted outputs; no agency documents silently removed.
    rows.sort(key=lambda r:(r['date_submission'],r['submission_id']))
    audit.sort(key=lambda r:(r['submission_id'],int(r['document_number'] or 0)))
    filefields=list(rows[0].keys()) if rows else []
    write_csv(out/'filing_inventory.csv',rows,filefields)
    write_csv(out/'document_audit.csv',audit,list(audit[0]) if audit else [])
    write_csv(out/'filer_concentration.csv',filer_rows,list(filer_rows[0]) if filer_rows else ['filer_key','display_filer','filing_count','unique_substantive_texts','composite_name_field','submission_ids','identity_caveat'])
    write_csv(out/'exact_duplicate_clusters.csv',dup_clusters,['cluster_id','normalized_text_sha256','filing_count','submission_ids'])
    write_csv(out/'review_queue.csv',missing_text,['submission_id','flags','source_url'])
    filer_freq=sorted([len(v) for v in by_filer.values()],reverse=True)
    n=max(1,len(filer_freq))
    n_total=max(1,sum(filer_freq))
    def top_share(f):return sum(filer_freq[:max(1,int(n*f+0.999999))])/n_total
    document_flags=Counter(flag for r in audit for flag in r['quality_flags'].split(';') if flag)
    summary={
      'methodology_version':'0.1.0','generated_utc':datetime.now(timezone.utc).isoformat(),
      'index_filings':len(rows),'document_records':len(audit),
      'filings_by_status':dict(Counter(r['status'] for r in rows)),
      'filings_by_submission_type':dict(Counter(r['submission_type'] for r in rows)),
      'filings_with_nonempty_combined_text':sum(r['text_chars']>0 for r in rows),
      'filings_with_missing_or_ambiguous_combined_text':sum('combined_text_' in r['quality_flags'] for r in rows),
      'filings_with_short_combined_text_100_chars_or_fewer':sum(0<r['text_chars']<=100 for r in rows),
      'agency_record_candidates_not_verified':sum(r['agency_record_candidate'] for r in rows),
      'filer_keys_exact_normalized_unverified':len(by_filer),
      'filers_with_multiple_filings':sum(v>1 for v in filer_freq),
      'largest_single_filer_count':max(filer_freq,default=0),
      'top_1_percent_filer_share_of_filings':round(top_share(.01),6),
      'top_5_percent_filer_share_of_filings':round(top_share(.05),6),
      'top_10_percent_filer_share_of_filings':round(top_share(.1),6),
      'unique_normalized_nonempty_texts':len(by_hash),
      'exact_duplicate_clusters':len(dup_clusters),
      'filings_in_exact_duplicate_clusters':sum(len(v) for v in by_hash.values() if len(v)>1),
      'document_quality_flag_counts':dict(document_flags),
      'warnings':['filing status complete does not mean all PDF content is readable',
                  'exact-normalized filer strings are not verified unique people',
                  'near-duplicate template campaigns and stakeholder/stance labels are not yet classified',
                  'agency_record_candidate is based on submission type, not verified identity',
                  'public comments are self-selected, not a population survey'],
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description='Build verified FCC filing inventory, QC and exact-duplicate tables')
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--out',type=Path,default=None)
    args=p.parse_args()
    out=args.out or args.corpus/'analysis_observatory'
    print(json.dumps(analyze(args.corpus,out),indent=2,ensure_ascii=False))
    print('Output:',out,'\nSource corpus unchanged.')

if __name__=='__main__':main()
