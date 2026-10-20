"""Interactive local research dashboard. Run: streamlit run app.py -- --corpus ~/Downloads/fcc_complete_corpus"""
import argparse, json, sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from erate.engine import read_combined, filer_key

st.set_page_config(page_title='E-Rate Comment Observatory',page_icon='📡',layout='wide')

@st.cache_data(show_spinner=False)
def load(csv_path,summary_path):
    df=pd.read_csv(csv_path, dtype={'submission_id':str, 'filer_key':str},keep_default_na=False)
    summary=json.loads(Path(summary_path).read_text())
    if 'text_chars' not in df.columns:df['text_chars']=0
    if 'document_count' not in df.columns:df['document_count']=0
    df['text_chars']=pd.to_numeric(df['text_chars'],errors='coerce').fillna(0).astype(int)
    df['document_count']=pd.to_numeric(df['document_count'],errors='coerce').fillna(0).astype(int)
    df['date']=pd.to_datetime(df['date_submission'],errors='coerce',utc=True)
    return df,summary

cli=argparse.ArgumentParser(add_help=False)
cli.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
cli.add_argument('--snapshot-id',default=None,help='Immutable research snapshot run ID')
cli.add_argument('--view',choices=['baseline','augmented'],default='baseline')
args,_=cli.parse_known_args([x for x in sys.argv[1:] if x != "--"])
corpus=args.corpus.expanduser()
analysis=corpus/'analysis_observatory'
snapshot=None
if args.snapshot_id:
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',args.snapshot_id):
        st.error('Invalid snapshot ID')
        st.stop()
    snapshot=analysis/f'research_snapshot_{args.snapshot_id}'
    inventory_path=snapshot/'research_inventory.csv'
    summary_path=snapshot/'snapshot_summary.json'
    topic_dir=snapshot/f'themes_{args.view}'
else:
    inventory_path=analysis/'filing_inventory.csv'
    summary_path=analysis/'summary.json'
    topic_dir=analysis
if not inventory_path.is_file():
    st.error(f'Analysis outputs not found: {inventory_path}')
    st.stop()
df,summary=load(str(inventory_path),str(summary_path))
if snapshot:
    col='baseline' if args.view=='baseline' else 'augmented'
    df['text_chars']=pd.to_numeric(df[f'{col}_chars'],errors='coerce').fillna(0).astype(int)
    df['normalized_text_sha256']=df[f'{col}_sha256']
    df['filer_key']=df['filer_raw'].map(filer_key)
    df['exact_duplicate_cluster_id']=''
    dup_hashes=df.loc[df.normalized_text_sha256!='','normalized_text_sha256'].value_counts()
    ids={k:f'exact_{i+1:05}' for i,k in enumerate(sorted(dup_hashes[dup_hashes>1].index))}
    df['exact_duplicate_cluster_id']=df['normalized_text_sha256'].map(ids).fillna('')
    df['quality_flags']=df['quality_flags'].fillna('')

st.title('FCC E-Rate Comment Observatory')
st.caption('WC Dockets 26-133, 13-184, 21-93, 21-455 • FCC 26-41 • Local research build')
if snapshot:
    st.warning(f"Snapshot {args.snapshot_id} · {args.view} text view. OCR candidates are NOT human-verified transcripts. Exploratory comparisons only; do not publish stance percentages.",icon='⚠️')
st.info('Counts below describe ECFS filings, not representative public opinion. Identity matching uses exact-normalized filer strings; stakeholder types, policy positions and themes remain unclassified until validated.',icon='ℹ️')
with st.sidebar:
    st.header('Explore')
    options=sorted(df['submission_type'].unique().tolist())
    types=st.multiselect('Submission type', options,default=options)
    statuses=st.multiselect('Collection status',sorted(df['status'].unique().tolist()),default=sorted(df['status'].unique().tolist()))
    quality=st.selectbox('Text-quality filter',['All','Flagged rows only','Unflagged rows only'])
    search=st.text_input('Filer name or submission ID')
    show_agency=st.checkbox('Include agency-record candidates',value=True)
    if snapshot:
        st.caption(f'Text source: {args.view}; OCR candidates included only in augmented view')
    st.caption('Agency candidates are identified by submission type and need manual verification.')
filtered=df[df['submission_type'].isin(types)&df['status'].isin(statuses)].copy()
if not show_agency:filtered=filtered[filtered['agency_record_candidate'].astype(str)!='1']
if quality=='Flagged rows only':filtered=filtered[filtered['quality_flags']!='']
if quality=='Unflagged rows only':filtered=filtered[filtered['quality_flags']=='']
if search:filtered=filtered[filtered['filer_raw'].str.contains(search,case=False,regex=False)|filtered['submission_id'].str.contains(search,regex=False)]

c1,c2,c3,c4=st.columns(4)
c1.metric('Filings in view',f'{len(filtered):,}')
c2.metric('Exact-normalized filer strings',f"{filtered.loc[filtered.filer_key!='','filer_key'].nunique():,}")
c3.metric('Distinct nonempty texts',f"{filtered.loc[filtered.normalized_text_sha256!='','normalized_text_sha256'].nunique():,}")
c4.metric('QC flags on filings',f"{(filtered.quality_flags!='').sum():,}")

tabs=st.tabs(['Participation','Texts & repeated submissions','Theme explorer','Quality audit','Policy coding','Filing explorer','Methods'])
with tabs[0]:
    left,right=st.columns([3,2])
    with left:
        by_date=filtered.dropna(subset=['date']).groupby(filtered['date'].dt.date).size().reset_index(name='filings')
        if not by_date.empty:
            fig=px.bar(by_date,x='date',y='filings',title='Submission volume by day')
            fig.update_layout(margin=dict(t=45,b=20));st.plotly_chart(fig,use_container_width=True)
        else:st.write('No filing dates in the selected subset.')
    with right:
        by_type=filtered['submission_type'].value_counts().head(15).reset_index()
        by_type.columns=['type','filings']
        if not by_type.empty:st.plotly_chart(px.bar(by_type,x='filings',y='type',orientation='h',title='Submission types'),use_container_width=True)
    st.subheader('Who submits multiple filings?')
    st.caption('A filer key is a normalized spelling of the entire ECFS filer field; it is not a verified unique person. Do not infer coordination from frequency alone.')
    counts=filtered[filtered.filer_key!=''].groupby(['filer_key'],as_index=False).agg(filings=('submission_id','size'),display=('filer_raw','first'))
    counts=counts.sort_values('filings',ascending=False)
    if not counts.empty:
        top=counts.head(25).sort_values('filings')
        st.plotly_chart(px.bar(top,x='filings',y='display',orientation='h',title='Most frequent exact-normalized filer strings'),use_container_width=True)
    st.dataframe(counts[['display','filings']].head(100),hide_index=True,use_container_width=True)
with tabs[1]:
    st.subheader('Exact duplicate comment texts')
    st.caption('Whitespace- and Unicode-normalized text hash. Each filing remains separately counted; exact copies are not deleted.')
    cluster_count=filtered[filtered.exact_duplicate_cluster_id!=''].groupby('exact_duplicate_cluster_id').agg(filings=('submission_id','size'),example=('submission_id','first')).sort_values('filings',ascending=False).reset_index()
    st.dataframe(cluster_count.head(200),hide_index=True,use_container_width=True)
    p=(analysis/'near_duplicate_candidates.csv') if not snapshot else snapshot/'near_duplicate_candidates.csv'
    if p.is_file():
        st.subheader('Potential near-duplicate templates (needs human verification)')
        st.dataframe(pd.read_csv(p).head(500),hide_index=True,use_container_width=True)
        st.caption('MinHash LSH is approximate and non-exhaustive. Similar writing is not proof of campaign coordination.')
    else:st.caption('Optional: run `python3 -m erate.near_duplicates` to generate near-duplicate candidates.')
with tabs[2]:
    st.subheader('Exploratory map of recurring language')
    st.caption('NMF thematic topics and SVD text projection are descriptive, unsupervised starting points — not semantic proof of agreement, sentiment or policy position. Validate against original passages.')
    topicp=topic_dir/'exploratory_topic_map.csv'
    if topicp.is_file():
        mapping=pd.read_csv(topicp,dtype={'submission_id':str})
        topicsp=topic_dir/'exploratory_topics.csv'
        tdf=pd.read_csv(topicsp)
        st.dataframe(tdf,hide_index=True,use_container_width=True)
        joined=mapping.merge(filtered[['submission_id','filer_raw','submission_type','text_chars']],on='submission_id',how='inner')
        if not joined.empty:
            fig=px.scatter(joined,x='map_x',y='map_y',color='topic_id',hover_name='submission_id',
                hover_data=['filer_raw','topic_strength','text_chars'],title='Two-dimensional lexical projection (exploratory)',
                opacity=.65)
            fig.update_layout(xaxis_title='SVD 1',yaxis_title='SVD 2',height=580)
            st.plotly_chart(fig,use_container_width=True)
    else:
        st.info('Run `python3 -m erate.topics --corpus ~/Downloads/fcc_complete_corpus` to generate a provisional theme map.')
with tabs[3]:
    st.subheader('Independent data-quality checks')
    st.caption('Collection status is NOT a pass/fail indicator for text readability.')
    docp=analysis/'document_audit.csv'
    if docp.is_file():
        docs=pd.read_csv(docp,dtype={'submission_id':str},keep_default_na=False)
        flagged=docs[docs.quality_flags!='']
        x,y=st.columns(2)
        x.metric('Attachments flagged',len(flagged))
        y.metric('PDFs with ≤100 extracted characters',len(docs[docs.quality_flags.str.contains('pdf_text_100_chars_or_fewer',regex=False)]))
        st.dataframe(flagged[['submission_id','document_number','filename','text_chars_actual','quality_flags','source_url']].head(1000),hide_index=True,use_container_width=True, column_config={'source_url':st.column_config.LinkColumn('FCC attachment')})
    st.write('Review queue is saved at `analysis_observatory/review_queue.csv`; PDF-specific triage at `pdf_ocr_review_queue.csv` after running the OCR triage script.')
with tabs[4]:
    st.subheader('Issue-specific positions and evidence')
    taxonomy=json.loads((Path(__file__).parent/'analysis_methods/issue_taxonomy.json').read_text())
    st.warning('Policy positions and stakeholder classifications have **not** been automatically assigned. The provisional taxonomy is not a findings table.',icon='⚠️')
    for issue in taxonomy['issues']:
        with st.expander(issue['label']):st.write(issue['question'])
    path=analysis/'validated_annotations.csv'  # Only human evidence-validated labels, independent of snapshot
    if path.is_file():
        ann=pd.read_csv(path,keep_default_na=False,dtype={'submission_id':str})
        if not ann.empty:
            st.subheader('Evidence-validated annotations')
            st.dataframe(ann,hide_index=True,use_container_width=True)
        else:st.write('No validated annotations yet.')
    st.caption('See analysis_methods/methodology.md for the coding and validation protocol.')
with tabs[5]:
    st.subheader('Trace any filing to the primary record')
    st.dataframe(filtered[['submission_id','filer_raw','submission_type','date_submission','text_chars','exact_duplicate_cluster_id','quality_flags','source_url']].head(1000),hide_index=True,use_container_width=True,column_config={'source_url':st.column_config.LinkColumn('Original filing')})
    ids=filtered['submission_id'].tolist()
    if ids:
        sid=st.selectbox('Inspect filing content',ids,format_func=lambda x: x+' — '+str(df.loc[df.submission_id==x,'filer_raw'].iloc[0])[:65])
        selected=df.loc[df.submission_id==sid].iloc[0]
        st.markdown(f"[Open original FCC filing]({selected['source_url']})")
        if snapshot:
            root=snapshot/('baseline_text' if args.view=='baseline' else 'ocr_augmented_text')
            p=root/f'{sid}.txt'
            if p.is_file():
                st.text_area('Versioned analysis text (read-only)',p.read_text(encoding='utf-8')[:120000],height=350)
            else:st.warning('No substantive text in this versioned view.')
        else:
            raw,rel,n=read_combined(corpus,sid)
            if n==1:st.text_area('Extracted text (read-only)',raw[:120000],height=350)
            else:st.warning('No single combined-text file found for this filing.')
with tabs[6]:
    st.subheader('Research method and limitations')
    st.markdown('''- **Population:** ECFS filings indexed in the collected docket snapshot, including agency documents until verified and separated.
- **Identity:** normalized exact filer strings, not verified people or organizations.
- **Duplicates:** exact text hashing distinguishes filing counts from distinct texts. Near-duplicate detection is optional and non-exhaustive.
- **Positions:** none assigned until an auditable issue taxonomy, evidence excerpts, human-coded benchmark and validation exist.
- **Quality:** scanned/empty PDFs need visual and OCR review. `complete` means collection status, not necessarily reliable extracted text.
- **Interpretation:** these are self-selected comments, not statistically representative samples of public opinion.
- **Privacy:** generated individual-level tables stay local by default and are ignored by Git.''')
    st.json(summary)
