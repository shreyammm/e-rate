#!/usr/bin/env python3
"""Two-layer, automatically discovered FCC argument landscape.

All original comments are scanned for debate passages; unsupervised clusters are
initial discovery aids and NOT stance labels. As the independent open Granite
census completes, grounded LLM claims populate a separate stricter argument map.
No user labeling or training is needed. Does not change the original research.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gzip,hashlib,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/fcc_corpus'
FAST=ROOT/'data/llm_census_fast'
OUT=ROOT/'docs/data/argument_landscape.json'
VERSION='argument-landscape-v1'
SENTENCE=re.compile(r'(?<=[.!?])\s+|\n\s*\n|\n(?=[A-Z][A-Za-z ]{5,}:)')
POLICY=re.compile(r'\b(e[- ]?rate|school|students?|libraries|library|broadband|internet|wifi|screens?|technology|filter|connectivity|discount|digital|network|cipa|children|parents?|district|funding|consultant|safety)\b',re.I)
ADVOCACY=re.compile(r'\b(urge|oppose|recommend|must|should|support|concerns?|funding|essential|important|risk|unfair|harm|protect|would|request|need|benefit|privacy|safety|eliminat\w*|reduc\w*|retain|continu\w*|expand|restrict\w*|limit|access|require|prohibit|costs?|afford\w*)\b',re.I)
STANCE=re.compile(r'\b(urge|oppose|recommend|must|should|we ask|we support|we oppose|strongly|do not|would harm|will harm|prohibit|condition|restrict|maintain|preserve|eliminate|reduce|continue)\b',re.I)
NOTICE=re.compile(r'\b(the commission seeks comment|notice of proposed rulemaking|federal communications commission|wireline competition bureau|paragraph \d+|\bwc docket|\bib docket)\b',re.I)


def classify_filer(label):
    label=(label or '').lower()
    patterns=[('school_district',r'school|district|academy|superintendent|education|isd\b|k-12'),
              ('library',r'library|libraries'),('government',r'county|municipal|government|city of|state of|department|commission'),
              ('telecom_or_vendor',r'telecom|network|broadband|communications|fiber|provider|wireless|connect|technology|association of service'),
              ('nonprofit_or_advocacy',r'foundation|advocacy|coalition|institute|society|alliance|council|association|center for|center on'),
              ('parents_or_individuals',r'parent|moms|family|families|mr\.|mrs\.|ms\.')]
    for name,pattern in patterns:
        if re.search(pattern,label):return name
    return 'unverified_other'


def representative_sentences(text, max_candidates=5):
    # Every character of the text is considered; the selected passages are
    # *examples*, never substituted for full-text per-filing LLM processing.
    ranked=[]
    for piece in SENTENCE.split(text):
        part=' '.join(piece.split())
        if not 60<=len(part)<=1300:continue
        if not POLICY.search(part) or not ADVOCACY.search(part):continue
        score=(9 if STANCE.search(part) else 0)+len(set(m.group(0).lower() for m in POLICY.finditer(part)))*2
        score+=len(set(m.group(0).lower() for m in ADVOCACY.finditer(part)))
        if NOTICE.search(part):score-=14
        if len(part)>550:score-=2
        if score>1:ranked.append((score,part))
    ranked.sort(key=lambda row:(-row[0],row[1]))
    seen=set();result=[]
    for score,part in ranked:
        signature=re.sub(r'\W+','',part.lower())[:180]
        if signature in seen:continue
        seen.add(signature);result.append((score,part))
        if len(result)>=max_candidates:break
    return result


def corpus_candidates(source):
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    records=[];passages=[];by_id={};scanned=0;with_text=0
    for shard in manifest['shards']:
        fp=source/'shards'/shard['name']
        if hashlib.sha256(fp.read_bytes()).hexdigest()!=shard['sha256']:
            raise ValueError('Corrupt source shard: '+str(fp))
        with gzip.open(fp,'rt',encoding='utf-8') as handle:
            for line in handle:
                if not line.strip():continue
                r=json.loads(line);sid=str(r['submission_id']);body=str(r.get('text') or '')
                if body and hashlib.sha256(body.encode()).hexdigest()!=r.get('text_sha256'):
                    raise ValueError('Text checksum mismatch: '+sid)
                scanned+=1;with_text+=bool(body)
                filer=str(r.get('filer_raw') or '')
                data={'id':sid,'filer':filer,'category':classify_filer(filer),
                      'date':str(r.get('date_submission') or ''),'ocr':str(r.get('has_unreviewed_ocr','0'))=='1',
                      'source_url':str(r.get('source_url') or 'https://www.fcc.gov/ecfs/filing/'+sid)}
                records.append(data);by_id[sid]=data
                for quality,piece in representative_sentences(body):
                    passages.append({**data,'quote':piece,'candidate_score':quality})
    if scanned!=manifest['records'] or with_text!=manifest['records_with_text']:
        raise ValueError('Full-corpus coverage error')
    return records,passages,manifest,by_id


def lexical_map(passages,records,n_topics=16):
    # Latent topics are an *exploratory argument-language landscape*, not
    # validated support/opposition or conclusions about what comments endorse.
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
    vocab_stop=set(ENGLISH_STOP_WORDS)|{'fcc','rate','rates','program','comments','comment','federal','commission','notice','proposed','schools','school','students','student','education','educational','erate','funding'}
    texts=[p['quote'] for p in passages]
    v=TfidfVectorizer(stop_words=list(vocab_stop),min_df=3,max_df=.65,max_features=10000,
                      ngram_range=(1,2),sublinear_tf=True,token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z-]{2,}\b')
    if len(texts)<10:return []
    mat=v.fit_transform(texts)
    n=min(n_topics,min(mat.shape)-1)
    model=NMF(n_components=n,init='nndsvda',random_state=11,max_iter=85)
    scores=model.fit_transform(mat)
    terms=v.get_feature_names_out()
    weights=model.components_
    clusters=[]
    for j in range(n):
        ranked=sorted(range(len(terms)),key=lambda k:-weights[j,k])[:11]
        keywords=[str(terms[i]) for i in ranked]
        hits=[];unique_filings=set();filers=Counter();roles=Counter()
        top=sorted(range(len(passages)),key=lambda k:-scores[k,j])
        for idx in top:
            if scores[idx,j]<.045:break
            p=passages[idx];sid=p['id']
            if sid not in unique_filings:
                unique_filings.add(sid);filers[p['filer'] or '(No filer field)']+=1;roles[p['category']]+=1
            if len(hits)<9 and scores[idx,j]>.09 and sid not in {x['id'] for x in hits}:
                hits.append({key:p[key] for key in ('id','filer','category','date','quote','source_url','ocr')})
        if not hits:continue
        clusters.append({'id':'language_theme_'+str(j+1),'topic_terms':keywords,
            'working_label':', '.join(keywords[:3]),'filings_with_matching_language':len(unique_filings),
            'filer_fields':len(filers),'leading_filers':[{'name':key,'n':v} for key,v in filers.most_common(8)],
            'filing_categories':dict(roles),'evidence':hits})
    clusters.sort(key=lambda x:-x['filings_with_matching_language'])
    return clusters


def model_argument_map(by_id,fastdir):
    # Read only *completed* free-form LLM arguments with direct source citations.
    claims=[];done=set();scan=0
    # Prefer new fast annotations, while exposing older verified checkpoints
    # until the faster pipeline catches up. Never double count a filing.
    sources=[fastdir/'filings', ROOT/'data/llm_census/filings']
    for fp in [f for directory in sources for f in sorted(directory.glob('*.json'))]:
        try:r=json.loads(fp.read_text(encoding='utf-8'))
        except (OSError,ValueError):continue
        if r.get('status')!='complete':continue
        sid=str(r.get('submission_id') or '');original=by_id.get(sid)
        if sid in done:continue
        if not original:continue
        if r.get('source_sha256') is None:continue
        done.add(sid)
        for claim in r.get('claims',[]):
            quote=str(claim.get('evidence_quote') or '')
            argument=str(claim.get('argument') or '')
            if len(quote)<15 or not argument:continue
            claims.append({**original,'argument':argument,'quote':quote,
                          'position':claim.get('position'),'provision_id':claim.get('provision_id'),
                          'reason_family':claim.get('reason_family'),'requested_action':claim.get('requested_action')})
    if not claims:return {'completed_filings':len(done),'claims':0,'clusters':[]}
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import MiniBatchKMeans
    texts=[c['argument']+' '+str(c['requested_action'] or '') for c in claims]
    groups=min(20,max(2,int(len(claims)**.5)))
    if len(claims)<groups*2: groups=max(1,len(claims)//2)
    if groups<2:
        assigned=[0]*len(claims);terms=[]
    else:
        v=TfidfVectorizer(stop_words='english',max_features=5000,ngram_range=(1,2))
        matrix=v.fit_transform(texts)
        algo=MiniBatchKMeans(n_clusters=groups,n_init=3,random_state=15,batch_size=256,max_iter=120)
        assigned=algo.fit_predict(matrix).tolist()
        vocab=v.get_feature_names_out();centers=algo.cluster_centers_
        terms=[[str(vocab[j]) for j in centers[i].argsort()[-5:][::-1]] for i in range(groups)]
    categories=[]
    for group in sorted(set(assigned)):
        relevant=[c for i,c in enumerate(claims) if assigned[i]==group]
        roles=Counter(c['category'] for c in relevant)
        stances=Counter(c['position'] for c in relevant)
        ids=set(c['id'] for c in relevant)
        groups_by_filer=Counter(c['filer'] or '(No filer field)' for c in relevant)
        examples=[];seen=set()
        for c in relevant:
            if c['id'] in seen:continue
            seen.add(c['id']);examples.append({k:c.get(k) for k in ('id','filer','category','argument','quote','position','provision_id','requested_action','source_url')})
            if len(examples)>=8:break
        categories.append({'id':'llm_argument_'+str(group),'auto_label':', '.join(terms[group][:3]) if terms else 'Other explicitly cited arguments',
                           'claim_rows':len(relevant),'filings':len(ids),'stakeholders':dict(roles),
                           'positions':dict(stances),'top_filers':[{'name':name,'claims':n} for name,n in groups_by_filer.most_common(8)],
                           'examples':examples})
    categories.sort(key=lambda g:-g['filings'])
    return {'completed_filings':len(done),'claims':len(claims),'clusters':categories}


def build(source=SOURCE,fast=FAST,out=OUT,topics=16):
    records,passages,manifest,by_id=corpus_candidates(source)
    themes=lexical_map(passages,records,topics)
    results={'schema_version':VERSION,'generated_utc':datetime.now(timezone.utc).isoformat(),
        'source_archive_sha256':manifest['source_archive_sha256'],
        'source_filings_scanned':len(records),'readable_filings':manifest['records_with_text'],
        'extracted_argument_language_passages':len(passages),
        'language_themes':themes,
        'llm_argument_map':model_argument_map(by_id,fast),
        'limitations':['All filing texts were scanned. Language themes were discovered by unsupervised methods and must not be read as validated policy positions.',
         'LLM clusters include only fully processed, source-grounded machine claim excerpts; total coverage appears separately.',
         'Theme examples are illustrative and selected automatically, not a representative sample. Filings can occur in more than one theme.',
         'Filer type labels are lexical heuristics, not verified person/institution affiliations.',
         'Repeated filings, appended FCC boilerplate and provisional OCR can affect clustering; there is no manual training or user labeling.']}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(results,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return {'records_scanned':len(records),'theme_count':len(themes),'passages':len(passages),
            'llm_completed':results['llm_argument_map']['completed_filings'],'llm_argument_clusters':len(results['llm_argument_map']['clusters']),
            'output':str(out)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=SOURCE)
    p.add_argument('--fast',type=Path,default=FAST);p.add_argument('--out',type=Path,default=OUT)
    p.add_argument('--topics',type=int,default=16)
    args=p.parse_args();print(json.dumps(build(args.source,args.fast,args.out,args.topics),indent=2))