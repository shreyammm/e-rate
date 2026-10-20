"""Exploratory text themes and two-dimensional projection, NOT position/sentiment labels.

Fit topic model on distinct nonempty texts to keep repeated campaign letters from
silently dominating themes; transform and report scores on all filing records.
"""
from __future__ import annotations
import argparse, json, hashlib, datetime
from collections import Counter
from pathlib import Path
import numpy as np
from sklearn.decomposition import NMF, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from erate.engine import read_csv, read_combined, write_csv

SEED=20261020

def analyze(corpus:Path,analysis:Path,n_topics=12,max_chars=50000):
    rows,_=read_csv(analysis/'filing_inventory.csv')
    eligible=[]
    for r in rows:
        if r['text_chars'].isdigit() and int(r['text_chars'])>=200 and r['agency_record_candidate']=='0':
            raw,_,matches=read_combined(corpus,r['submission_id'])
            if matches!=1:continue
            # Beginning + ending instead of just the beginning; log every truncation.
            truncated=len(raw)>max_chars
            body=(raw[:int(max_chars*.7)]+'\n'+raw[-int(max_chars*.3):]) if truncated else raw
            eligible.append((r,body,truncated))
    if len(eligible)<6:raise ValueError('Need six or more eligible documents for exploratory themes')
    # Avoid exact duplicates driving topic formation, without excluding their filings from scoring.
    fit_indices=[];seen=set()
    for idx,(r,text,truncated) in enumerate(eligible):
        h=r['normalized_text_sha256'] or r['submission_id']
        if h not in seen:
            fit_indices.append(idx); seen.add(h)
    corpus_fit=[eligible[i][1] for i in fit_indices]
    tfidf=TfidfVectorizer(stop_words='english',strip_accents='unicode',ngram_range=(1,2),
                          max_features=40000,min_df=2,max_df=.92,sublinear_tf=True)
    x_fit=tfidf.fit_transform(corpus_fit)
    k=min(n_topics, len(corpus_fit)-1, x_fit.shape[1]-1)
    if k<2:raise ValueError('Vocabulary too small for interpretable themes')
    model=NMF(n_components=k,init='nndsvda',random_state=SEED,max_iter=300,alpha_W=0.0001,
              alpha_H=0.0001,l1_ratio=0.0)
    fit_w=model.fit_transform(x_fit)
    x_all=tfidf.transform([item[1] for item in eligible])
    w=model.transform(x_all)
    denom=w.sum(axis=1,keepdims=True)
    strengths=np.divide(w,denom,out=np.zeros_like(w),where=denom>0)
    terms=tfidf.get_feature_names_out()
    topics=[]
    for j,row in enumerate(model.components_):
        most=np.argsort(row)[-10:][::-1]
        topics.append({'topic_id':f'T{j+1:02d}','top_terms':'; '.join(terms[most]),
          'description':'Unsupervised lexical topic (not a human-validated theme or stance)',
          'model':'TFIDF + NMF', 'filing_top_topic_count':int((np.argmax(w,axis=1)==j).sum())})
    # 2-D projection of TFIDF space, not an inferential or geographic map.
    svd=TruncatedSVD(n_components=2,random_state=SEED)
    coords=svd.fit_transform(x_all)
    assignments=[]
    for i,(r,text,truncated) in enumerate(eligible):
        j=int(np.argmax(strengths[i]))
        assignments.append({'submission_id':r['submission_id'],'topic_id':f'T{j+1:02d}',
          'topic_strength':round(float(strengths[i,j]),6),
          'map_x':round(float(coords[i,0]),7),'map_y':round(float(coords[i,1]),7),
          'truncated_for_model':int(truncated),
          'provisional_topic_terms':topics[j]['top_terms'],
          'source_url':r['source_url']})
    write_csv(analysis/'exploratory_topics.csv',topics,['topic_id','top_terms','description','model','filing_top_topic_count'])
    write_csv(analysis/'exploratory_topic_map.csv',assignments,['submission_id','topic_id','topic_strength','map_x','map_y','truncated_for_model','provisional_topic_terms','source_url'])
    desc={'version':'0.1.0','seed':SEED,'method':'TfidfVectorizer(1,2)-word stop words + NMF + 2D TruncatedSVD',
          'n_topics':k,'eligible_filings':len(eligible),'distinct_texts_used_for_fit':len(corpus_fit),
          'truncated_filings':sum(x[2] for x in eligible),'max_characters_input':max_chars,
          'exclusions':'agency_record_candidates; texts <200 characters; missing text',
          'duplicate_policy':'distinct normalized texts train model, all eligible filings are projected',
          'limitations':['Not sentiment or policy support/opposition','2D distances are exploratory not precise semantic distance',
             'First 70% and last 30% of exceptionally long texts; may omit arguments in the middle',
             'Boilerplate can influence topic terms','Short and flagged scan documents excluded',
             'Near-duplicate templates still overweight independent texts in topic model'],
          'quality_gate_warning':'Inspect flagged PDFs and rerun after OCR before publishing substantive theme prevalence.'}
    (analysis/'exploratory_topic_method.json').write_text(json.dumps(desc,indent=2)+'\n')
    return desc

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--analysis',type=Path)
    p.add_argument('--topics',type=int,default=12)
    p.add_argument('--max-chars',type=int,default=50000)
    args=p.parse_args()
    out=args.analysis or args.corpus/'analysis_observatory'
    print(json.dumps(analyze(args.corpus,out,args.topics,args.max_chars),indent=2))
if __name__=='__main__':main()
