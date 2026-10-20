#!/usr/bin/env python3
"""Reproducible full-text, document-level inverted index for browser RAG.
Raw source filing text is never shortened during indexing. Only singleton
tokens and common stop words are removed from the *fast search index*.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data'/'fcc_corpus'
DEST=ROOT/'docs'/'data'/'qa_index'
WORD=re.compile(r'[a-z][a-z0-9]{2,}', re.IGNORECASE | re.ASCII)
STOP=set('''the and for are was were that this with from have has had will would could should shall
does did doing into onto also they them their there here where when what while these those some
many more most just you your our not but its his her she him who whom which may can all one
two three four other any such each both being been because about above below under over after
before than then through between among upon per regarding thereof hereby herein pursuant
paragraphs pdf page pages attached attachments respectfully submitted filing filed date name
number herein stated proposed proposal submit submission information please see hereby theirs
year years since like only even although whereas however therefore thus further including included
yes its those many thereby accordingly said says would further must every another very within
without according point first second third document documents appendix attachment review provided
provides provide providing make makes made use uses used using based become well part parts
more less other each way ways same different new old due current previous'''.split())

def words(s):
    for match in WORD.finditer(s.lower()):
        w=match.group()
        if len(w)<=24 and w not in STOP:yield w

def build(source=SRC,out=DEST):
    manifest=json.loads((source/'manifest.json').read_text('utf-8'))
    if {p.name for p in (source/'shards').glob('filings-*.jsonl.gz')} != {x['name'] for x in manifest['shards']}:
        raise ValueError('Source shard files differ from corpus manifest')
    docs=[];postings=defaultdict(list);sumlength=0;covered=0
    for spec in manifest['shards']:
        path=source/'shards'/spec['name']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=spec['sha256']:
            raise ValueError('Invalid source shard checksum: '+path.name)
        count=0
        with gzip.open(path,'rt',encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():continue
                record=json.loads(line);body=str(record.get('text') or '')
                if body and hashlib.sha256(body.encode()).hexdigest()!=record.get('text_sha256'):
                    raise ValueError('Source text checksum mismatch '+str(record['submission_id']))
                tf=Counter(words(body));length=sum(tf.values());sumlength+=length
                docid=len(docs)
                docs.append({'id':str(record['submission_id']),'filer':str(record.get('filer_raw') or ''),
                             'date':str(record.get('date_submission') or ''),
                             'shard':spec['name'],'length':length,'has_text':bool(body)})
                covered+=bool(body)
                for term,n in tf.items():postings[term].extend((docid,min(n,15)))
                count+=1
        if count!=spec['records']:raise ValueError('Shard record count mismatch')
    if len(docs)!=manifest['records'] or covered!=manifest['records_with_text']:
        raise ValueError('Index does not cover every source record')
    buckets=defaultdict(dict)
    for term,flat in postings.items():
        df=len(flat)//2
        if 2<=df<int(len(docs)*.94):buckets[term[0]][term]=flat
    out.mkdir(parents=True,exist_ok=True)
    for bucket,posting in buckets.items():
        (out/(bucket+'.json')).write_text(json.dumps(posting,separators=(',',':')),encoding='utf-8')
    for f in out.glob('?.json'):
        if f.stem not in buckets:f.unlink()
    result={'schema_version':'1.0','snapshot':manifest['snapshot_id'],
      'corpus_source_sha256':manifest['source_archive_sha256'],'records':len(docs),
      'with_text':covered,'avg_doc_length':sumlength/max(len(docs),1),
      'terms_indexed':sum(map(len,buckets.values())),'buckets':sorted(buckets),
      'docs':docs,'limitations':['Fast index excludes single-occurrence tokens; complete source text is still browsable.',
                                 'Lexical retrieval is not a population-level policy stance analysis.',
                                 'Text matches are not proof that factual assertions in filings are true.']}
    (out/'manifest.json').write_text(json.dumps(result,separators=(',',':'),ensure_ascii=False),encoding='utf-8')
    return {key:value for key,value in result.items() if key!='docs'}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=SRC)
    parser.add_argument('--out',type=Path,default=DEST)
    args=parser.parse_args();print(json.dumps(build(args.source,args.out),indent=2))
