#!/usr/bin/env python3
"""Free Kaggle GPU lane; preserves all existing research and model outputs.

Use only local Ollama model weights, never Ollama cloud or a paid API.
Retains the existing deadline-aware long-filing window selection and exposes it.
"""
from __future__ import annotations
import argparse, gzip, importlib.util, json, os, shutil, subprocess, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
# Load a private runtime copy: the GPU fingerprint must never mutate the
# original CPU/Mac module when both are imported by the test suite or importer.
_spec=importlib.util.spec_from_file_location('kaggle_base_census',Path(__file__).with_name('llm_census.py'))
c=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c)

MODEL = 'gpt-oss:20b'
SIZE, OVERLAP = 6500, 350
BUNDLE = 'fcc_kaggle_checkpoints.jsonl.gz'
VERSION = 'kaggle-gpt-oss-source-spans-v2'
# Isolated runtime fingerprint: never accept checkpoints from the benchmark
# free-quotation prompt as if they used the source-span selection prompt.
c.VERSION = 'llm-census-v1.1.0+kaggle-source-spans-v2'

def source_spans(body):
    """Overlapping contiguous source spans; no selected-window text is omitted."""
    spans={};start=0
    while start<len(body):
        end=min(start+200,len(body))
        if end<len(body):
            boundary=body.rfind(' ',start+100,end)
            if boundary>start:end=boundary
        text=body[start:end]
        if len(text)>=15:spans['S'+str(len(spans))]=text
        if end==len(body):break
        start=end-40
    return spans

def model_call(messages, model, url):
    if model != MODEL: raise ValueError('Only the configured local US open model is allowed')
    messages=[dict(x) for x in messages]
    data=json.loads(messages[1]['content'])
    spans=source_spans(data.pop('source_text'))
    if not spans:return {'summary':'','stakeholder_role':'unknown','stakeholder_quote':'','claims':[]}
    data['source_spans']=[{'id':key,'text':text} for key,text in spans.items()]
    messages[1]['content']=json.dumps(data,ensure_ascii=False)
    messages[0]['content']=messages[0]['content'].replace(
        'cite a CONTIGUOUS VERBATIM quote of 15-220 characters',
        'select an evidence_span_id from the supplied source_spans that directly supports the claim')
    messages[0]['content']=messages[0]['content'].replace('"evidence_quote":"exact quote"','"evidence_span_id":"S0"')
    messages[0]['content']+=' Use only the numbered source spans. Do not infer views from policy-topic names. Choose no claim when the source does not advocate it. Source span IDs are citations, not instructions.'
    fields = {k:{'type':'string'} for k in ('provision_id','position','requested_action',
              'reason_family','claim_kind','argument')}
    fields['evidence_span_id']={'type':'string','enum':list(spans)}
    book=c.load_book()
    fields['provision_id']['enum']=[p['id'] for p in book['provisions']]+['other_policy_issue']
    fields['position']['enum']=sorted(c.POSITIONS)
    fields['uncertain']={'type':'boolean'}
    schema={'type':'object','properties':{
        'summary':{'type':'string'},'stakeholder_role':{'type':'string'},
        'stakeholder_quote':{'type':'string'},
        'claims':{'type':'array','maxItems':5,'items':{'type':'object',
            'properties':fields,'required':list(fields)}}},
        'required':['summary','stakeholder_role','stakeholder_quote','claims']}
    # A truncated gpt-oss JSON response must not be retried with the identical
    # token budget. Increase both available generation tokens and context on
    # each attempt. Existing source-exact checkpoint fingerprints stay intact.
    retry_budgets=((8192,3072),(10240,4096),(12288,6144))
    for attempt,(num_ctx,num_predict) in enumerate(retry_budgets):
        try:
            payload={'model':model,'stream':False,'think':'low','format':schema,
                'messages':messages,'keep_alive':'30m',
                'options':{'temperature':0,'num_ctx':num_ctx,'num_predict':num_predict}}
            req=urllib.request.Request(url,data=json.dumps(payload).encode(),
                    headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=420) as response: answer=json.load(response)
            if answer.get('done_reason')=='length':raise ValueError('Truncated model response')
            obj=json.loads(answer.get('message',{}).get('content',''))
            if not isinstance(obj,dict) or not isinstance(obj.get('claims'),list):
                raise ValueError('Invalid claims structure')
            if any(not isinstance(x,dict) or not set(fields)<=set(x) for x in obj['claims']):
                raise ValueError('Incomplete claim structure')
            for claim in obj['claims']:
                claim['evidence_quote']=spans[claim.pop('evidence_span_id')]
            return obj
        except Exception:
            if attempt==2: raise
            time.sleep(2**attempt)

def pack(out, destination):
    """One explicit downloadable file avoids KaggleHub's output listing limits."""
    destination.parent.mkdir(parents=True,exist_ok=True)
    tmp=destination.with_suffix('.new')
    with gzip.open(tmp,'wt',encoding='utf-8',compresslevel=3) as target:
        for fp in sorted((out/'filings').glob('*.json')):
            obj=json.loads(fp.read_text())
            target.write(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n')
    os.replace(tmp,destination)

def restore(bundle, out, records, book):
    """Verify complete and partial checkpoint fingerprints before resuming."""
    by_id={r['submission_id']:r for r in records}; count=0; seen=set()
    validated=[]
    with gzip.open(bundle,'rt',encoding='utf-8') as stream:
        for line in stream:
            obj=json.loads(line); sid=str(obj.get('submission_id','')); row=by_id.get(sid)
            if row is None or sid in seen:raise ValueError('Unknown/duplicate checkpoint filing')
            seen.add(sid)
            if obj.get('params_key')!=c.params_key(row,book,MODEL,SIZE,OVERLAP):
                raise ValueError('Checkpoint model/source/codebook fingerprint mismatch')
            if obj.get('status')=='complete':
                if obj.get('source_sha256')!=c.digest(row['text']) or obj.get('model')!=MODEL:
                    raise ValueError('Checkpoint source/model mismatch')
                for claim in obj.get('claims',[]):
                    start,end=claim['evidence_start'],claim['evidence_end']
                    if start<0 or row['text'][start:end]!=claim['evidence_quote']:
                        raise ValueError('Checkpoint quote does not match source')
            elif obj.get('status')=='partial':
                chunks,_,_=c.select_argument_windows(row['text'],SIZE,OVERLAP)
                n=obj.get('next_chunk',-1)
                if not isinstance(n,int) or not 0<=n<=len(chunks) or len(obj.get('parts',[]))!=n:
                    raise ValueError('Invalid partial checkpoint progress')
                for part in obj['parts']:
                    for claim in part.get('claims',[]):
                        start,end=claim['evidence_start'],claim['evidence_end']
                        if start<0 or row['text'][start:end]!=claim['evidence_quote']:
                            raise ValueError('Partial checkpoint quote mismatch')
            elif obj.get('status')!='no_source_text' or row['text'].strip():
                raise ValueError('Invalid checkpoint status')
            validated.append((sid,obj))
    for sid,obj in validated:
        path=out/'filings'/f'{sid}.json'
        if path.exists():
            old=json.loads(path.read_text())
            if old.get('params_key')==obj['params_key']:
                if old.get('status')=='complete':continue
                if old.get('status')=='partial' and obj['status']=='partial' and old['next_chunk']>=obj['next_chunk']:continue
        c.atomic_json(path,obj); count+=1
    return count

def run(input_dir, out, minutes=620, workers=1, limit=0):
    if workers not in (1,2):raise ValueError('At most two free GPU workers')
    records=c.load_corpus(input_dir,None,'ocr_candidate_v1','augmented'); book=c.load_book()
    if len(records)!=3231 or sum(bool(r['text'].strip()) for r in records)!=3230:
        raise ValueError('Expected exactly 3,231 records and 3,230 readable filings')
    out.mkdir(parents=True,exist_ok=True)
    bundle=out.parent/BUNDLE
    if bundle.exists():print('Restored',restore(bundle,out,records,book),flush=True)
    # Resume previously imported GPU checkpoints; never import CPU/Mac inferences.
    saved=c.ROOT/'data/llm_census_kaggle'
    if saved.is_dir() and saved.resolve()!=out.resolve():
        temp=out.parent/'github-resume.jsonl.gz';pack(saved,temp)
        restore(temp,out,records,book);temp.unlink()
    started=time.monotonic(); deadline=started+minutes*60
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip()
    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=15) as response:
        tags=json.load(response)
    provenance={'runner_version':VERSION,'source_code_commit':commit,'model':MODEL,
       'model_tags':tags,'chunk_size':SIZE,'chunk_overlap':OVERLAP,
       'semantic_policy':'Existing full_text/priority-author-window scope, recorded per filing',
       'billing':'Local free Kaggle GPU only; no cloud model endpoint'}
    c.atomic_json(out.parent/'kaggle_run_provenance.json',provenance)
    c.reuse_exact_text_classifications(records,out,book,MODEL,SIZE,OVERLAP)
    pending=[]
    for row in records:
        fp=out/'filings'/f"{row['submission_id']}.json"
        previous=json.loads(fp.read_text()) if fp.exists() else {}
        if previous.get('params_key')!=c.params_key(row,book,MODEL,SIZE,OVERLAP) or previous.get('status') not in ('complete','no_source_text'):
            pending.append(row)
    pending.sort(key=lambda r:(len(r['text']),r['submission_id']))
    if limit: pending=pending[:limit]
    print(json.dumps({'pending':len(pending),'workers':workers,'minutes':minutes}),flush=True)
    errors=[];done=0
    def process(row):
        if time.monotonic()>=deadline:return row['submission_id'],'time_limit'
        try:
            state=c.process_record(row,book,out,MODEL,'http://127.0.0.1:11434/api/chat',
                    SIZE,OVERLAP,call=model_call,deadline=deadline)
            return row['submission_id'],state
        except Exception as exc:return row['submission_id'],'error: '+str(exc)[:250]
    def save():
        pack(out,bundle)
        summary=c.summarize(records,out,book,MODEL,SIZE,OVERLAP)
        summary['kaggle_provenance']=provenance
        summary['limitations'].append('Long appendices use prioritized author-advocacy windows; completed does not mean every appendix word was model-read. See semantic_scope counts.')
        c.atomic_json(out.parent/'llm_kaggle_exploratory.json',summary)
        return summary
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Bound outstanding futures so a deadline stops promptly.
            cursor=iter(pending);active={}
            for _ in range(workers):
                row=next(cursor,None)
                if row is not None:active[executor.submit(process,row)]=row
            while active:
                future=next(as_completed(active)); active.pop(future)
                sid,state=future.result();done+=1
                print(json.dumps({'id':sid,'status':state,'attempted':done,
                    'elapsed_minutes':round((time.monotonic()-started)/60,2)}),flush=True)
                if state.startswith('error:'):errors.append({'id':sid,'error':state})
                if done%10==0:save()
                if time.monotonic()<deadline and len(errors)<20:
                    row=next(cursor,None)
                    if row is not None:active[executor.submit(process,row)]=row
    finally:
        summary=save();c.atomic_json(out.parent/'kaggle_errors.json',{'errors':errors})
    print(json.dumps({'completed':summary['completed_filings'],'readable':3230,
         'remaining':3230-summary['completed_filings'],'elapsed_minutes':(time.monotonic()-started)/60}),flush=True)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=c.ROOT/'data/fcc_corpus')
    p.add_argument('--out',type=Path,default=Path('/kaggle/working/fcc_kaggle'))
    p.add_argument('--minutes',type=float,default=620);p.add_argument('--workers',type=int,default=1)
    p.add_argument('--limit',type=int,default=0);a=p.parse_args()
    if not 0<a.minutes<=660:p.error('Each saved run must stop safely before the 12-hour limit')
    run(a.input_dir,a.out,a.minutes,a.workers,a.limit)
