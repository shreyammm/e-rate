"""Reproducible human-coding starter with explicit evidence validation."""
from __future__ import annotations
import argparse, csv, json, random
from collections import defaultdict
from pathlib import Path
from erate.engine import read_csv, read_combined, write_csv

SCHEMA=['submission_id','issue_id','position','evidence_quote','stakeholder_type','stakeholder_evidence',
        'coder_id','coding_method','confidence','notes']
POSITIONS={'support','oppose','mixed_or_conditional','descriptive_only','unclear','not_addressed'}
STAKEHOLDERS={'unknown','parent_or_guardian','student','teacher_or_staff','school_or_district',
              'library_or_library_system','industry_vendor','consultant','advocacy_nonprofit',
              'government_agency','elected_official','individual_other','other_organization'}

def taxonomy():
    p=Path(__file__).resolve().parents[1]/'analysis_methods/issue_taxonomy.json'
    return json.loads(p.read_text(encoding='utf-8'))

def make_sample(corpus: Path, analysis: Path, n=120, seed=20261020):
    inventory,_=read_csv(analysis/'filing_inventory.csv')
    # Diverse review sample: exact duplicate family representatives, short texts and ordinary filings.
    eligible=[r for r in inventory if r['text_chars'].isdigit() and int(r['text_chars'])>100]
    rng=random.Random(seed)
    buckets=defaultdict(list)
    for r in eligible:
        if r['agency_record_candidate']=='1': cat='agency_candidate'
        elif r['exact_duplicate_cluster_id']:cat='exact_duplicate'
        elif int(r['text_chars'])>30000:cat='long'
        else:cat='other'
        buckets[cat].append(r)
    chosen=[];seen=set()
    quotas={'agency_candidate':min(8,n//10),'exact_duplicate':min(30,n//3),
            'long':min(15,n//6),'other':n}
    for cat in ['agency_candidate','exact_duplicate','long','other']:
        rng.shuffle(buckets[cat])
        for r in buckets[cat][:quotas[cat]]:
            if len(chosen)>=n:break
            if r['submission_id'] not in seen:
                chosen.append(r);seen.add(r['submission_id'])
    remainder=[r for r in eligible if r['submission_id'] not in seen]
    rng.shuffle(remainder)
    chosen.extend(remainder[:max(0,n-len(chosen))])
    chosen=chosen[:n]
    rows=[]
    for r in chosen:
        rows.append({'submission_id':r['submission_id'],'source_url':r['source_url'],
          'sampling_stratum':'agency_candidate' if r['agency_record_candidate']=='1' else
                              ('exact_duplicate' if r['exact_duplicate_cluster_id'] else
                               ('long' if int(r['text_chars'])>30000 else 'other')),
          'filer_raw':r['filer_raw'],'text_chars':r['text_chars'],
          'note':'Open source filing and locally saved combined text; create one annotation per addressed issue.'})
    write_csv(analysis/'manual_review_sample.csv',rows,list(rows[0]) if rows else
              ['submission_id','source_url','sampling_stratum','filer_raw','text_chars','note'])
    if not (analysis/'manual_annotations.csv').exists():
        write_csv(analysis/'manual_annotations.csv',[],SCHEMA)
    return len(chosen)

def validate(corpus: Path, analysis: Path):
    rows,_=read_csv(analysis/'manual_annotations.csv')
    allowed_issues={x['id'] for x in taxonomy()['issues']}
    valid=[];invalid=[];seen=set()
    for rowno,r in enumerate(rows,start=2):
        sid=r.get('submission_id','');issue=r.get('issue_id','');position=r.get('position','')
        why=[]
        if not sid.isdigit():why.append('invalid_submission_id')
        if issue not in allowed_issues:why.append('invalid_issue_id')
        if position not in POSITIONS:why.append('invalid_position')
        if r.get('stakeholder_type','unknown') not in STAKEHOLDERS:why.append('invalid_stakeholder_type')
        if not r.get('coder_id','').strip():why.append('missing_coder_id')
        if r.get('coding_method','') not in {'manual','model_proposal_reviewed','adjudicated'}:
            why.append('unrecognized_coding_method')
        text,path,count=read_combined(corpus,sid) if sid.isdigit() else ('','',0)
        if count!=1:why.append('missing_or_ambiguous_source_text')
        quote=r.get('evidence_quote','').strip()
        if position in {'support','oppose','mixed_or_conditional','descriptive_only'} and not quote:
            why.append('evidence_required')
        if quote and quote not in text:why.append('quote_not_verbatim_in_combined_text')
        key=(sid,issue,r.get('coder_id',''))
        if key in seen:why.append('duplicate_coder_issue_submission')
        seen.add(key)
        if why:invalid.append({'csv_line':rowno,'submission_id':sid,'issues':';'.join(why)})
        else:valid.append(r)
    write_csv(analysis/'annotation_validation_errors.csv',invalid,['csv_line','submission_id','issues'])
    write_csv(analysis/'validated_annotations.csv',valid,SCHEMA)
    return len(valid),len(invalid)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('action', choices=['sample','validate'])
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--analysis',type=Path,default=None)
    p.add_argument('--n',type=int,default=120)
    args=p.parse_args()
    analysis=args.analysis or (args.corpus/'analysis_observatory')
    if args.action=='sample':print('Sampled filings:',make_sample(args.corpus,analysis,args.n))
    else:print('Valid, invalid annotations:',validate(args.corpus,analysis))

if __name__=='__main__':main()
