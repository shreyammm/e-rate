#!/usr/bin/env python3
"""Audit new ECFS metadata against the frozen October 20 source snapshot.

Accepts a locally exported CSV, JSON array, JSON object with a 'filings' or
'results' array, or JSONL. NEVER edits source shards or imports new unverified
attachments. Never claims a partial export is the complete FCC docket.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=ROOT/'docs/data/corpus_index.json'
OUTPUT=ROOT/'private_data/ecfs_refresh_qa'
ECFS='https://www.fcc.gov/ecfs/filing/'
DIGITS=re.compile(r'^\d{8,17}$')
DATE=re.compile(r'^\d{4}-\d{2}-\d{2}')
SNAPSHOT_DAY='2026-10-20'

def filing_id(row):
    values=[row.get(k) for k in ('submission_id','filing_id','id','filingId','submissionId') if row.get(k) is not None]
    normalized=[]
    for v in values:
        if isinstance(v,dict):v=v.get('id')
        if isinstance(v,bool):raise ValueError('Invalid filing identifier')
        s=str(v).strip()
        if not DIGITS.fullmatch(s):raise ValueError('Invalid ECFS numeric filing identifier '+repr(s[:50]))
        normalized.append(s)
    if not normalized or len(set(normalized))!=1:
        raise ValueError('Missing or conflicting ECFS filing IDs')
    return normalized[0]

def string_field(row, *names):
    for k in names:
        v=row.get(k)
        if isinstance(v,(str,int)) and str(v).strip():return str(v).strip()
    return ''

def date_prefix(v):
    if not v:return ''
    match=DATE.match(v)
    if not match:return ''
    try:return date.fromisoformat(match.group(0)).isoformat()
    except ValueError:return ''

def parse_input(path):
    path=Path(path)
    if path.suffix.lower()=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as f:
            return list(csv.DictReader(f))
    if path.suffix.lower()=='.jsonl':
        return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    obj=json.loads(path.read_text(encoding='utf-8-sig'))
    if isinstance(obj,dict):
        obj=obj.get('filings',obj.get('results'))
    if not isinstance(obj,list):raise ValueError('Expected CSV, JSONL or JSON filings array')
    return obj

def validate_ecfs_url(url, sid):
    if not url:return ECFS+sid
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in {'www.fcc.gov','fcc.gov'}:
        raise ValueError('Source URL must be an official HTTPS FCC filing URL')
    if parsed.path.rstrip('/')!='/ecfs/filing/'+sid:
        raise ValueError('Source URL ID conflicts with filing record')
    return ECFS+sid

def normalized_export(rows):
    records={}
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Each export row must be an object')
        sid=filing_id(row)
        submitted=string_field(row,'date','date_received','dateReceived','date_submission','dateSubmission','submission_date','submissionDate')
        modified=string_field(row,'last_modified','lastModified','date_modified','dateModified')
        if submitted and not date_prefix(submitted):
            raise ValueError('Unparseable submission date for '+sid)
        if modified and not date_prefix(modified):
            raise ValueError('Unparseable modification date for '+sid)
        result={'id':sid,'date':date_prefix(submitted),'modified':date_prefix(modified),
                'type':string_field(row,'type','filing_type','filingType'),
                'source_url':validate_ecfs_url(string_field(row,'source_url','sourceUrl','url'),sid)}
        if sid in records:
            if records[sid]!=result:
                raise ValueError('Conflicting export entries for ECFS ID '+sid)
            raise ValueError('Duplicate export row for ECFS ID '+sid+'; deduplicate with source provenance first')
        records[sid]=result
    return records

def compare(snapshot, export, complete=False):
    if snapshot.get('snapshot')!='ocr_candidate_v1' or not isinstance(snapshot.get('filings'),list):
        raise ValueError('Unrecognized research snapshot')
    originals={str(f['id']):f for f in snapshot['filings']}
    if len(originals)!=len(snapshot['filings']) or len(originals)!=3231:
        raise ValueError('Snapshot filing ID mismatch')
    other=normalized_export(export)
    new_ids=sorted(set(other)-set(originals))
    common=sorted(set(other)&set(originals))
    absent=sorted(set(originals)-set(other))
    changed=[]
    for sid in common:
        old=originals[sid];fresh=other[sid]
        changes={}
        if fresh['date'] and old.get('date') and fresh['date']!=old['date']:
            changes['submission_date']=dict(snapshot=old['date'],export=fresh['date'])
        if fresh['type'] and old.get('type') and fresh['type'].casefold()!=str(old['type']).casefold():
            changes['filing_type']=dict(snapshot=old['type'],export=fresh['type'])
        if fresh['modified'] and fresh['modified']>SNAPSHOT_DAY:
            changes['post_snapshot_modified']=fresh['modified']
        if changes:changed.append(dict(id=sid,changes=changes,source_url=fresh['source_url']))
    candidate=[dict(id=sid,submission_date=other[sid]['date'],
                    type=other[sid]['type'],source_url=other[sid]['source_url'])
               for sid in new_ids]
    report={
        'status':'UNVERIFIED_METADATA_DIFF_ONLY',
        'snapshot_date':SNAPSHOT_DAY,'snapshot_filing_records':len(originals),
        'export_records':len(other),'export_declared_complete':bool(complete),
        'matched_original_ids':len(common),'new_filing_candidates':len(new_ids),
        'metadata_changes_to_recheck':len(changed),
        'original_ids_absent_from_export':len(absent) if complete else None,
        'absence_interpretation':('Check docket scope, export pagination and filing withdrawal before treating absent records as missing.'
                                  if complete else 'Not evaluated: a partial export cannot establish missing source filings.'),
        'source_not_imported':True,
        'limitations':[
            'New metadata IDs are candidates, not downloaded, text-extracted or verified FCC filings.',
            'An ECFS export may include proceedings, joint-docket filings, corrections or reply comments missing from the snapshot.',
            'The original corpus remains immutable; any new collection requires source identity, attachment, docket-scope, OCR and hash reconciliation.',
            'No machine labels, stakeholder types, endorsement counts or model-derived analysis are computed on new records.',
        ],
        'new_filings':candidate,'changed_existing_metadata':changed,
        'absent_ids_if_complete':absent if complete else [],
    }
    return report

def build(source, snapshot=SNAPSHOT, output=OUTPUT, complete=False):
    rows=parse_input(source)
    data=json.loads(Path(snapshot).read_text(encoding='utf-8'))
    result=compare(data,rows,complete)
    out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    (out/'ecfs_metadata_delta.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return {k:result[k] for k in ('status','snapshot_filing_records','export_records',
            'matched_original_ids','new_filing_candidates','metadata_changes_to_recheck',
            'original_ids_absent_from_export','export_declared_complete')}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--snapshot',type=Path,default=SNAPSHOT)
    parser.add_argument('--out',type=Path,default=OUTPUT)
    parser.add_argument('--complete-export',action='store_true',
                        help='Only set when all intended dockets/dates and ALL pagination are verified.')
    a=parser.parse_args()
    print(json.dumps(build(a.input,a.snapshot,a.out,a.complete_export),indent=2))

if __name__=='__main__':
    main()
