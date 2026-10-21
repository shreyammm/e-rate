#!/usr/bin/env python3
"""Derive *filing-counted* open-ended argument groups from ALL completed LLM files.

This is a semantic/lexical discovery analysis of machine-extracted claims, not a
representative sample and not a certified stance survey. Every complete filing
and every accepted claim are included. Pending/error filings are explicit.
"""
from __future__ import annotations
import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime,timezone
import gzip,hashlib,json,math,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILINGS=ROOT/'data/llm_census_fast/filings'
INDEX=ROOT/'docs/data/corpus_index.json'
ROLE_MAP=ROOT/'docs/data/full_text_filer_roles.json'
OUT=ROOT/'docs/data/claim_landscape.json'
CONTACT=re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)(?:\+1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\d)')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def corpus_index(path=INDEX):
    data=read_json(path)
    filings=data['filings']
    if len({r['id'] for r in filings})!=len(filings):
        raise ValueError('Duplicate filing ID in complete corpus index')
    return filings


def role_lookup(records, path=ROLE_MAP):
    data=read_json(path)
    if not data or 'sequence' not in data:return {}
    codes=gzip.decompress(base64.b64decode(data['sequence'])).decode('ascii')
    if len(codes)!=len(records) or data['expected_records']!=len(records):
        raise ValueError('Full-text role map does not align with corpus')
    if records[0]['id']!=data['expected_first_id'] or records[-1]['id']!=data['expected_last_id']:
        raise ValueError('Full-text role ID alignment mismatch')
    if dict(Counter(codes))!=data['expected_code_counts']:
        raise ValueError('Role-code counts corrupted')
    return {r['id']:data['legend'][code] for r,code in zip(records,codes)}


def completed_claims(files, records, roles):
    allowed={r['id'] for r in records}
    claims=[]
    stats=Counter()
    seen=set()
    by_file={}
    for path in sorted(Path(files).glob('*.json')):
        row=read_json(path)
        sid=str(row.get('submission_id',''))
        if sid not in allowed or sid!=path.stem:
            raise ValueError('Unexpected or mismatched filing ID: '+path.name)
        if sid in seen:raise ValueError('Duplicate filing result: '+sid)
        seen.add(sid)
        status=row.get('status')
        stats[status or 'unknown']+=1
        if status!='complete':continue
        by_file[sid]=row
        dedupe=set()
        for c in row.get('claims',[]):
            quote=str(c.get('evidence_quote') or '')
            offset=c.get('evidence_start')
            end=c.get('evidence_end')
            if len(quote)<15 or not isinstance(offset,int) or end!=offset+len(quote):
                stats['rejected_claim_shape']+=1;continue
            key=(c.get('provision_id'),c.get('position'),quote,offset)
            if key in dedupe:continue
            dedupe.add(key)
            argument=str(c.get('argument') or '').strip()
            action=str(c.get('requested_action') or '').strip()
            # Machine-generated labels can be missing; never fill a fictional reason.
            if not (argument or action):
                stats['claims_without_action_or_argument']+=1
            claim={
                'submission_id':sid,'role':roles.get(sid,'unresolved'),
                'issue_id':c.get('provision_id','other_policy_issue'),
                'position':c.get('position','unclear'),
                'claim_kind':c.get('claim_kind','other'),
                'reason_family':c.get('reason_family','other'),
                'argument':CONTACT.sub('[CONTACT REDACTED]',argument[:450]),
                'requested_action':CONTACT.sub('[CONTACT REDACTED]',action[:230]),
                'quote':CONTACT.sub('[CONTACT REDACTED]',quote[:320]),
                'raw_quote':quote,
                'source_url':str(row.get('source_url') or 'https://www.fcc.gov/ecfs/filing/'+sid),
                'evidence_start':offset,'source_sha256':row.get('source_sha256',''),
                'ocr_candidate':str(row.get('has_unreviewed_ocr','0'))=='1',
                'text_to_group':' '.join([argument,action]) or quote[:400]
            }
            claims.append(claim)
    stats['complete_files_with_claims']=len({c['submission_id'] for c in claims})
    stats['machine_claim_rows']=len(claims)
    stats['complete_files_without_claims']=len(by_file)-stats['complete_files_with_claims']
    return claims,stats,by_file


def verify_source_spans(claims, by_file, source=ROOT/'data/fcc_corpus'):
    """Verify EVERY published evidence offset against original source bytes."""
    manifest=read_json(source/'manifest.json')
    wanted=defaultdict(list)
    for claim in claims:wanted[claim['submission_id']].append(claim)
    verified=0
    seen_ids=set()
    total=0
    for item in manifest['shards']:
        file=source/'shards'/item['name']
        if hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Corrupt FCC source shard: '+item['name'])
        with gzip.open(file,'rt',encoding='utf-8') as handle:
            for line in handle:
                if not line.strip():continue
                row=json.loads(line);sid=str(row['submission_id'])
                total+=1
                if sid not in wanted:continue
                seen_ids.add(sid)
                body=str(row.get('text') or '')
                if hashlib.sha256(body.encode()).hexdigest()!=row['text_sha256']:
                    raise ValueError('Source text hash mismatch '+sid)
                if by_file[sid].get('source_sha256')!=row['text_sha256']:
                    raise ValueError('Model result from mismatching source version '+sid)
                for c in wanted[sid]:
                    offset=c['evidence_start']
                    original_quote=c['quote']
                    # Compare redacted quote against the same redaction of the
                    # literal stored text span; no model-fabricated citations.
                    span=body[offset:offset+len(c['raw_quote'])]
                    if span!=c['raw_quote'] or CONTACT.sub('[CONTACT REDACTED]',span[:320])!=original_quote:
                        raise ValueError('Evidence quote does not match original text for '+sid)
                    verified+=1
    if total!=manifest['records'] or seen_ids!=set(wanted):
        raise ValueError('Full-corpus source record or citation coverage mismatch')
    return verified


def cluster_claims(claims, max_groups=42):
    """Cluster EVERY accepted claim; no selected-example basis for counts."""
    n=len(claims)
    if not n:return [],{'method':'no_extracted_claims','groups':0}
    if n<12:
        labels=list(range(n))
        return labels,{'method':'each_claim_separate_until_12','groups':n}
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize
    text=[c['text_to_group'] for c in claims]
    vectorizer=TfidfVectorizer(stop_words='english',ngram_range=(1,2),
       max_features=12000,min_df=1 if n<30 else 2,
       sublinear_tf=True,token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z-]{2,}\b')
    matrix=vectorizer.fit_transform(text)
    if min(matrix.shape)<3:
        return [0]*n,{'method':'insufficient_vocabulary','groups':1}
    components=min(48,min(matrix.shape)-1)
    projected=normalize(TruncatedSVD(n_components=components,random_state=20261020).fit_transform(matrix))
    groups=min(max_groups,max(8,int(math.sqrt(n)/2.2)))
    groups=min(groups,n)
    model=MiniBatchKMeans(n_clusters=groups,random_state=20261020,
                          batch_size=min(512,max(64,n)),n_init=3,max_iter=160)
    labels=[int(i) for i in model.fit_predict(projected)]
    return labels,{'method':'tfidf_1_2gram+truncated_svd+minibatch_kmeans',
        'groups':len(set(labels)),'seed':20261020,
        'interpretation':'Lexical/latent claim groups needing semantic review, not verified distinct arguments'}


def build(data_dir=FILINGS, output=OUT, verify=True, max_groups=42, index_file=INDEX,
          role_file=ROLE_MAP, source=ROOT/'data/fcc_corpus'):
    records=corpus_index(index_file)
    roles=role_lookup(records,role_file)
    claims,stats,by_file=completed_claims(data_dir,records,roles)
    if verify:
        verified=verify_source_spans(claims,by_file,source)
        if verified!=len(claims):raise ValueError('Not all citations source-verified')
    labels,method=cluster_claims(claims,max_groups)
    groups=defaultdict(list)
    for c,label in zip(claims,labels):groups[label].append(c)
    org_by_id={r['id']:str(r.get('organization') or '') for r in records}
    # Every accepted machine claim is available for browsing, not just the
    # handful of examples used to illustrate each automatically found group.
    row_index={
      'version':'machine-claim-rows-v1',
      'publication_status':'EXPLORATORY_MODEL_ONLY',
      'source_filings':len(records),
      'complete_model_filings':len(by_file),
      'rows':[{
        'id':c['submission_id'],'group':'claim_group_'+str(label),
        'role':c['role'],'organization':org_by_id.get(c['submission_id'],''),
        'issue':c['issue_id'],'position':c['position'],
        'reason_family':c['reason_family'],'claim_kind':c['claim_kind'],
        'action':c['requested_action'],'argument':c['argument'],
        'quote':c['quote'],'source_url':c['source_url'],
        'start':c['evidence_start'],'ocr_candidate':c['ocr_candidate']
      } for c,label in zip(claims,labels)]
    }
    rows_output=Path(output).with_name('machine_claim_rows.json')
    rows_output.parent.mkdir(parents=True,exist_ok=True)
    rows_output.write_text(json.dumps(row_index,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    summarized=[]
    for number_group,group in groups.items():
        filing_ids={c['submission_id'] for c in group}
        unique_exact_texts={c['source_sha256'] for c in group}
        roles_present=defaultdict(set);issues_present=defaultdict(set)
        for c in group:
            roles_present[c['role']].add(c['submission_id'])
            issues_present[c['issue_id']].add(c['submission_id'])
        # Specific examples are for navigation only, not the cluster denominator.
        examples=sorted(group,key=lambda c:(-len(c['argument']),c['submission_id']))[:4]
        words=Counter()
        for c in group:
            for term in set(re.findall(r'[a-z]{4,}',c['text_to_group'].lower())):
                if term not in {'that','with','from','this','would','should','these','there',
                        'which','their','about','have','program','support','funding','rate',
                        'school','schools','commenter','commission','federal','policy'}:
                    words[term]+=1
        summarized.append({
            'id':f'claim_group_{number_group}',
            'working_label':', '.join(t for t,v in words.most_common(5)) or 'Unlabeled claims',
            'distinct_filings':len(filing_ids),
            'unique_source_texts':len(unique_exact_texts),
            'argument_rows':len(group),
            'role_filings':{k:len(v) for k,v in sorted(roles_present.items())},
            'issue_filings':{k:len(v) for k,v in sorted(issues_present.items())},
            'stance_claim_rows':dict(Counter(c['position'] for c in group)),
            'examples':[{k:x[k] for k in ('submission_id','issue_id','position',
                       'requested_action','argument','quote','source_url')} for x in examples]
        })
    summarized.sort(key=lambda r:(-r['distinct_filings'],r['id']))
    org_by_id={r['id']:str(r.get('organization') or '') for r in records}
    org_positions=defaultdict(lambda:defaultdict(lambda:defaultdict(set)))
    role_issue_positions=defaultdict(lambda:defaultdict(lambda:defaultdict(set)))
    role_filing_counts=defaultdict(set);position_issues=defaultdict(lambda:defaultdict(set))
    for c in claims:
        role_filing_counts[c['role']].add(c['submission_id'])
        position_issues[c['issue_id']][c['position']].add(c['submission_id'])
        role_issue_positions[c['role']][c['issue_id']][c['position']].add(c['submission_id'])
        org=org_by_id.get(c['submission_id'],'')
        if org:org_positions[org][c['issue_id']][c['position']].add(c['submission_id'])
    completed=len(by_file)
    result={
      'schema_version':'claim-landscape-v1',
      'generated_utc':datetime.now(timezone.utc).isoformat(),
      'coverage':{'corpus_records':len(records),'source_text_records':len(records)-1,
        'completed_machine_filings':completed,
        'remaining_or_incomplete_filings':len(records)-completed,
        'machine_claim_rows':len(claims),
        'filings_with_source_cited_claims':stats['complete_files_with_claims'],
        'full_source_quote_offset_verified':len(claims) if verify else 0,
        'malformed_claim_rows_excluded':stats['rejected_claim_shape'],
        'missing_argument_and_action_claims':stats['claims_without_action_or_argument']},
      'model_status':'UNVALIDATED_MACHINE_EXTRACTION_partial_until_complete',
      'counts_policy':'Each group count is DISTINCT filing IDs among completed machine-processed files, not raw claim sentences, person counts, or a corpus-wide prevalence estimate. Overlapping groups and issues are permitted.',
      'discovery':method,
      'role_filings_with_model_claims':{k:len(v) for k,v in sorted(role_filing_counts.items())},
      'issue_stance_filing_counts':{k:{position:len(ids) for position,ids in x.items()}
                                   for k,x in sorted(position_issues.items())},
      'clusters':summarized,
      'commenter_type_issue_stance':[
        {'role':role,'issue_id':issue,'position':stance,'distinct_filings':len(ids)}
        for role,issues in sorted(role_issue_positions.items())
        for issue,stances in sorted(issues.items()) for stance,ids in sorted(stances.items())
      ],
      'organization_issue_stance':[
        {'organization_label':name,'issue_id':issue,'position':stance,'distinct_filings':len(ids)}
        for name,issues in sorted(org_positions.items())
        for issue,stances in sorted(issues.items()) for stance,ids in sorted(stances.items())
      ],
      'warnings':['All completed model-extracted claims are grouped; no sampled passages are used as the prevalence denominator.',
         'The LLM may miss arguments, confuse quoted views with the filer’s stance, or misidentify roles. Source-exact citations do not validate semantic interpretation.',
         'Unprocessed filings are NEVER treated as not_addressed or neutral.',
         'Unsupervised claim groups are preliminary and can mix paraphrases or unrelated perspectives; group names are term-based discovery aids.',
         'OCR and cross-docket-source ambiguities remain; do not claim public-opinion representativeness.']
    }
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--filings',type=Path,default=FILINGS)
    p.add_argument('--output',type=Path,default=OUT)
    p.add_argument('--source',type=Path,default=ROOT/'data/fcc_corpus')
    p.add_argument('--no-source-verification',action='store_true')
    p.add_argument('--max-groups',type=int,default=42)
    a=p.parse_args()
    result=build(a.filings,a.output,not a.no_source_verification,a.max_groups,source=a.source)
    print(json.dumps({'coverage':result['coverage'],'claim_groups':len(result['clusters']),
                      'output':str(a.output)},indent=2))


if __name__=='__main__': main()
