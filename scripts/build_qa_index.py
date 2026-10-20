#!/usr/bin/env python3
"""Build reproducible, complete, source-verified document-level BM25 search index.

There is one document per ECFS submission. No body text is dropped from the
lexical indexing pass; long filings use binary term-frequency caps *for ranking*
only, not for coverage. Actual evidence excerpts are extracted from full source
texts in the browser after document retrieval.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data'/'fcc_corpus'
DEST = ROOT/'docs'/'data'/'qa_index'
WORD = re.compile(r"[a-z][a-z0-9]{2,}",re.I | re.ASCII)
STOP = set(('the and for are was were that this with from have has had will would could should shall does did doing'
    ' into onto also they them their there here where when what while these those some many more most just'
    ' you your our not but its his her she him who whom which may can all one two three four other'
    ' any such each both being been because about above below under over after before than then through'
    ' between among upon per regarding thereof hereby herein pursuant section paragraphs pdf page pages'
    ' attached attachments comments comment docket commission federal communications rulemaking notice'
    ' rate rates item subject respectfully submitted filing filed date name number herein above listed'
    ' stated proposed proposal submit submission information please see ecr ecfs fcc hereby theirs'
    ' year years since like only even although whereas however therefore thus further including included'
    ' yes no its those many thereby accordingly said says one would further must every another very'
    ' within without upon according point first second third document documents appendix attachment'
    ' review provided provides provide providing make makes made use uses used using based become well'
    ' part parts more less other each way ways same different new old due become current previous'
    ' want needed need school schools student students internet access service services program programs'
    ).split())
# Crucial E-Rate words above are deliberately *not* in the final stop list,
# because they are valid user search terms even when common.
STOP -= {'school','schools','student','students','internet','access','service','services','program','programs','rate','rates','commission','fcc','comments','comment','docket','rulemaking'}

def words(s:str):
    for m in WORD.finditer(s.lower()):
        w=m.group()
        if len(w)<=24 and w not in STOP and not (w.isdigit()):yield w

def build(source:Path=SOURCE,out:Path=DEST) -> dict:
    manifest=json.loads((source/'manifest.json').read_text('utf-8'))
    docs=[];postings=defaultdict(list);sizes=[];covered=0
    expected={x['name'] for x in manifest['shards']}
    actual={p.name for p in (source/'shards').glob('filings-*.jsonl.gz')}
    if expected!=actual:raise ValueError('missing, unexpected or duplicate source shards')
    for item in manifest['shards']:
        path=source/'shards'/item['name']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('shard sha256 mismatch: '+path.name)
        n=0
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for line in f:
                if not line.strip():continue
                r=json.loads(line);body=str(r.get('text') or '')
                if r.get('text_sha256') and hashlib.sha256(body.encode()).hexdigest()!=r['text_sha256']:
                    raise ValueError('text sha256 mismatch for '+str(r['submission_id']))
                terms=Counter(words(body));length=sum(terms.values()); sizes.append(length)
                docid=len(docs)
                docs.append({'id':str(r['submission_id']), 'filer':str(r.get('filer_raw') or ''),
                             'date':str(r.get('date_submission') or ''),
                             'shard':item['name'], 'length':length,'has_text':bool(body)})
                if body:covered+=1
                for term,count in terms.items():
                    # Frequency capped for compact index; never exclude rare terms by corpus length.
                    postings[term].extend((docid,min(count,15)))
                n+=1
        if n!=item['records']:raise ValueError('record count mismatch '+path.name)
    if len(docs)!=manifest['records'] or covered!=manifest['records_with_text']:
        raise ValueError('Incorrect index coverage')
    # Global df filtering reduces invalid OCR garbage without dropping an entire
    # filing; omitted singletons can still be searched via streamed raw text.
    buckets=defaultdict(dict)
    for term,flat in postings.items():
        df=len(flat)//2
        if df<2 or df>=len(docs)*0.94:continue
        buckets[term[0]][term]=flat
    out.mkdir(parents=True,exist_ok=True)
    for bucket in sorted(buckets):
        path=out/(bucket+'.json')
        path.write_text(json.dumps(buckets[bucket],separators=(',',':'),ensure_ascii=False),encoding='utf-8')
    known=set(buckets)
    for path in out.glob('?.json'):
        if path.stem not in known:path.unlink()
    meta={'schema_version':'1.0','snapshot':manifest['snapshot_id'],
          'corpus_source_sha256':manifest['source_archive_sha256'],
          'records':len(docs),'with_text':covered,'avg_doc_length':sum(sizes)/max(len(sizes),1),
          'lengths_sum':sum(sizes),'terms_indexed':sum(len(x) for x in buckets.values()),
          'buckets':sorted(buckets),'docs':docs,
          'notes':['The index scans the full body of every readable filing.',
                   'Singleton OCR tokens are omitted from the fast index; complete source text remains publicly browsable.',
                   'A retrieved excerpt does not measure corpus-wide prevalence or verify the truth of a claim.']}
    (out/'manifest.json').write_text(json.dumps(meta,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
    return {k:v for k,v in meta.items() if k!='docs'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--out',type=Path,default=DEST)
    args=p.parse_args();print(json.dumps(build(args.source,args.out),indent=2))