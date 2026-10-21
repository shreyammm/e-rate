#!/usr/bin/env python3
"""Publish a source-linked *provisional* FCC E-Rate research findings page.

Every number comes from a complete pass over the CURRENT set of successfully
model-processed records. It never expands sample excerpts into population counts.
"""
from __future__ import annotations
import html
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
LAND=ROOT/'docs/data/claim_landscape.json'
EXPLOR=ROOT/'docs/data/llm_exploratory.json'
TARGET=ROOT/'docs/findings.html'

def h(value):return html.escape(str(value or ''),quote=True)
def fmt(v):return f'{int(v):,}'
def get(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def safe_link(url,label):
    if isinstance(url,str) and url.startswith('https://www.fcc.gov/ecfs/filing/') and url.split('/')[-1].isdigit():
        return f'<a href="{h(url)}" target="_blank" rel="noopener noreferrer">{h(label)}</a>'
    return h(label)

def build(land=LAND,explor=EXPLOR,target=TARGET):
    a=get(land);b=get(explor)
    c=a['coverage']
    if c['corpus_records']!=3231 or c['completed_machine_filings']!=b['completed_filings']:
        raise ValueError('Census and LLM snapshots disagree; refusing to publish misleading report')
    model_done=int(c['completed_machine_filings'])
    readable=int(c['source_text_records'])
    n=int(c['corpus_records'])
    pct=100*model_done/readable
    scope=b.get('machine_evidence_quality',{})
    selective=int(scope.get('semantic_scope_prioritized_windows_filings',0))
    full_model=int(scope.get('semantic_scope_full_text_filings',model_done-selective))
    clusters=sorted(a.get('clusters',[]),key=lambda row:-row['distinct_filings'])
    author_types={
      'named_person_capacity_unstated':'Individual filer, occupational role not stated',
      'school_district_or_school':'Schools and districts',
      'educator_or_school_staff':'Educators and school staff',
      'library_or_library_system':'Libraries and library staff',
      'advocacy_nonprofit_or_trade_association':'Advocacy organizations and associations',
      'parent_guardian':'Self-identified parents and guardians',
      'government_or_tribal_organization':'Government and Tribal representatives',
      'unresolved':'Unresolved commenter capacity'
    }
    header=f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="description" content="Evidence-linked machine-assisted FCC E-Rate research findings with exact current coverage">
    <title>FCC E-Rate: research findings and argument evidence</title>
    <style>
    :root{{--ink:#172537;--muted:#526579;--line:#d9e1e9;--paper:#f7f9fb}}
    *{{box-sizing:border-box}}body{{margin:0;font:16px/1.65 system-ui,-apple-system,Arial;color:var(--ink);background:#fff}}
    header,main,footer{{max-width:1080px;margin:auto;padding:20px 24px}}
    header{{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;border-bottom:1px solid var(--line)}}
    a{{color:#174c75}}a:hover{{text-decoration:underline}}h1{{line-height:1.15;font-size:clamp(30px,4vw,50px);max-width:850px}}
    h2{{border-top:1px solid var(--line);padding-top:30px;margin-top:38px;line-height:1.2}}
    h3{{margin-bottom:2px}}small,.muted{{color:var(--muted)}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:12px}}
    .metric{{border:1px solid var(--line);padding:14px;border-radius:8px}}.metric strong{{display:block;font-size:26px}}
    .status{{background:#f2f5f7;border-left:4px solid #7890a2;padding:12px 16px;margin:20px 0}}
    .cluster{{border-bottom:1px solid var(--line);padding:12px 0 18px}}.cluster blockquote{{margin:6px 0;border-left:2px solid #b3c2cb;padding:8px 15px;background:var(--paper);font-size:14px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:18px}}
    table{{border-collapse:collapse;width:100%}}td,th{{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}}
    td.num{{text-align:right;font-variant-numeric:tabular-nums}}caption{{text-align:left;color:var(--muted)}}
    .key{{font-size:13px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}}li{{margin:.5em 0}}
    </style></head><body><header><strong>E-Rate Comment Observatory</strong>
    <nav><a href="./index.html">Data dashboard</a> · <a href="./llm.html#all-machine-claims">Every extracted claim</a> · <a href="./corpus.html">Full original texts</a> · <a href="./ask.html">Ask the corpus</a></nav></header><main>
    <p class="key">Source-cited computational policy analysis · machine-only interim findings</p>
    <h1>What are commenters arguing about E-Rate, and who is advancing each view?</h1>
    <p>Generated {h(b.get('generated_utc','unknown UTC'))} from current checked-in output. This report is a <strong>living, provisional analytical census</strong>—it is not a verified survey of Americans and does not extrapolate from a randomly chosen sample. As the ongoing complete-corpus model run finishes, the filing-level counts and argument families below will refresh.</p>
    <div class="metrics">
      <div class="metric"><strong>{fmt(n)}</strong><span>ECFS filing records indexed</span></div>
      <div class="metric"><strong>{fmt(readable)}</strong><span>Filings with readable text</span></div>
      <div class="metric"><strong>{fmt(model_done)}</strong><span>Completed machine analyses</span></div>
      <div class="metric"><strong>{fmt(c['machine_claim_rows'])}</strong><span>Exact-source-verified machine claims</span></div>
    </div>
    <p class="status"><strong>Coverage: {pct:.1f}%</strong> of readable filings have completed model classification; {fmt(readable-model_done)} remain. Of completed filings, {fmt(full_model)} have full-text model reading (or legacy full-pass classification) and {fmt(selective)} are explicitly marked for prioritized passage reading from very long documents. The other unread source record has no recoverable text. A word-search census is not equivalent to a semantic census.</p>
    <h2>1. Main perspectives in the emerging argument record</h2>
    <p>Each category below comes from grouping <em>all accepted source-cited machine claims from currently completed filings</em>, not from manually selected examples. A group is a provisional similarity cluster, not an authoritative definition of a single coherent argument. We give exact filing counts, commenter categories and example source passages for inspection. A filing counts only once per group; a filing can appear in multiple groups.</p>"""
    parts=[header]
    if not clusters:parts.append('<p>No source-cited claim clusters have completed yet.</p>')
    for g in clusters[:35]:
        roles=sorted(g.get('role_filings',{}).items(),key=lambda t:-t[1])
        rolelines=', '.join(f'{h(author_types.get(k,k.replace("_"," ")))}: {fmt(v)}' for k,v in roles[:6])
        strongest=str(g.get('working_label','Machine-discovered argument-language family')).replace('_',' ')
        parts.append(f"""<article class="cluster"><h3>{h(strongest)}</h3>
          <p><strong>{fmt(g['distinct_filings'])} distinct filings</strong> · {fmt(g['argument_rows'])} machine-extracted claims ·
          {fmt(g.get('unique_source_texts',0))} distinct original-source text hashes.</p>
          <p class="muted"><strong>Who is represented:</strong> {rolelines or 'No dependable role assignment'}</p>""")
        for ex in g.get('examples',[])[:2]:
            quote=ex.get('quote') or ''
            argument=ex.get('argument') or ex.get('requested_action') or 'No distinct reason extracted'
            parts.append(f"""<p><strong>Machine reading:</strong> {h(argument)} ·
               {safe_link(ex.get('source_url'), 'Original FCC filing '+str(ex.get('submission_id','')))}</p>
               <blockquote>{h(quote)}</blockquote>""")
        parts.append('</article>')
    parts.append("""<h2>2. Position coding across specific policy questions</h2>
      <p>The rows below refer to policy targets named by our <em>provisional</em> notice-driven codebook, plus novel issues. They are not a claim that the FCC posed exactly 29 mutually exclusive proposals. Machine stances may be wrong, particularly when a comment quotes language it opposes. Incomplete, negative and unclassified filings are not imputed as neutral or no position.</p>
      <table><thead><tr><th>Policy target</th><th>Support</th><th>Oppose</th><th>Conditional / alternative</th><th>Machine-coded filings with a position or mention</th></tr></thead><tbody>""")
    for x in sorted(b.get('provisions',[]),key=lambda y:-int(y.get('filings_mentioning',0)))[:30]:
        d=x.get('positions',{})
        mixed=sum(int(d.get(k,0)) for k in ('conditional_or_amend','alternative_proposal','conflicting_or_multiple'))
        mention=int(x.get('filings_mentioning',0))
        parts.append(f'<tr><td>{h(x.get("label",x.get("provision_id","")))}</td><td class="num">{fmt(d.get("support",0))}</td><td class="num">{fmt(d.get("oppose",0))}</td><td class="num">{fmt(mixed)}</td><td class="num">{fmt(mention)}</td></tr>')
    parts.append('</tbody></table>')
    parts.append("""<h2>3. What stakeholder comparisons do—and do not—tell us</h2>
    <p>Role labels combine preliminary metadata and text-based evidence, and do not establish the identity of distinct people. Quantification here is about <strong>filings</strong>, not representative public opinion, support from all schools, or the beliefs of an entire demographic group.</p>""")
    role_counts=sorted(a.get('role_filings_with_model_claims',{}).items(),key=lambda t:-t[1])
    parts.append('<table><thead><tr><th>Provisional commenter type</th><th>Completed filings with source-linked machine claims</th></tr></thead><tbody>')
    for key,val in role_counts:
        parts.append(f'<tr><td>{h(author_types.get(key,key.replace("_"," ")))}</td><td class="num">{fmt(val)}</td></tr>')
    parts.append('</tbody></table>')
    parts.append(f"""<h2>4. Trustworthiness and research limitations</h2>
    <p>Actual claims are retained at the <a href="./llm.html#all-machine-claims">individual filing level</a>.
    {fmt(c.get('full_source_quote_offset_verified',0))} published machine excerpts have been checked against the source-text file and their offsets.
    This proves that the <em>quotation exists</em>, not that the commenter endorsed it or that the model's interpretation is correct.</p>
    <ul>
    <li><strong>No sample extrapolation:</strong> all completed records were used to calculate these counts. Pending filings are excluded from stance totals and shown in the denominator.</li>
    <li><strong>Attribution:</strong> distinguishing a filer's views from FCC wording, copied campaigns, opposing arguments and cited attachments remains a major source of possible error.</li>
    <li><strong>Long-document flag:</strong> each source file was available for lexical scanning, but the deadline-specific model pass may select high-signal passages rather than read megabytes of quoted appendix material. These filings are explicitly labeled.</li>
    <li><strong>Repeated submissions:</strong> one filer may submit several documents; normalized text hashes allow one sensitivity check, but template similarity and verified entity counts require separate validation.</li>
    <li><strong>Semantic clusters:</strong> unsupervised clusters can combine differing stances or split paraphrases; they are discovery aids, not finalized substantive themes.</li>
    <li><strong>Self-selection:</strong> FCC commenters are not a probability sample of the public, so no filing-weighted percentage should be described as public-opinion support.</li>
    </ul>
    <p><strong>Completion standard:</strong> filing coverage, attribution accuracy, argument-family coherence, role validation and full source drill-through need to be documented before moving these figures into a final policy-analysis claim. The separate <a href="./llm.html">machine explorer</a> preserves the intermediate hypotheses and evidence.</p>
    </main><footer><small>Automatically regenerated from versioned GitHub source data, not editorially human-verified. <a href="https://github.com/shreyammm/e-rate">Research repository</a>.</small></footer></body></html>""")
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(''.join(parts),encoding='utf-8')
    return {'completed':model_done,'readable':readable,'argument_groups':len(clusters),'output':str(target)}

if __name__=='__main__':
    print(json.dumps(build(),indent=2))
