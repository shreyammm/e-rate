'use strict';
(function(){
  const $=id=>document.getElementById(id);
  const status=$('llm-status'),target=$('llm-issues');
  let dataset=null;
  const nice=s=>String(s||'').replaceAll('_',' ');
  const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;};
  function metric(number,caption){const e=node('article');e.append(node('strong','',number.toLocaleString()),node('span','',caption));return e;}
  function evidenceCard(c){const wrap=node('div','llm-evidence');
    wrap.append(node('span','llm-small',`${nice(c.position)} — ${c.argument}`));
    wrap.append(node('blockquote','',`“${c.evidence_quote}”`));
    if(/^https:\/\/www\.fcc\.gov\//.test(c.source_url)){
      const a=node('a','','FCC filing '+c.submission_id+' ↗');a.href=c.source_url;a.rel='noopener noreferrer';a.target='_blank';wrap.append(a);
      wrap.append(document.createTextNode(' · '));
      const full=node('a','','Read entire text ↗');
      full.href='./corpus.html?id='+encodeURIComponent(c.submission_id);
      wrap.append(full);
    }
    return wrap;
  }
  function render(){if(!dataset)return;
    const query=$('llm-query').value.trim().toLowerCase();
    const cat=$('llm-category').value;const stance=$('llm-stance').value;
    const results=dataset.provisions.filter(p=>(cat==='all'||p.category===cat)&&
      (stance==='all'||(p.positions?.[stance]||0)>0)&&
      (!query||[p.label,p.category,JSON.stringify(p.claim_reason_counts),JSON.stringify(p.filings_by_inferred_role)].join(' ').toLowerCase().includes(query)));
    $('llm-visible').textContent=`${results.length} of ${dataset.provisions.length} draft FCC issue categories`;
    target.replaceChildren();
    for(const p of results){const card=node('article','llm-issue');card.append(node('h3','',p.label),
      node('p','llm-small',`${p.filings_mentioning||0} completed filings discussed this provision · ${p.claim_count||0} cited argument rows`));
      const val=p.positions||{},total=Object.values(val).reduce((a,b)=>a+Number(b||0),0);
      if(total){const bar=node('div','llm-breakdown');for(const [key,klass] of [['support','support'],['oppose','oppose']]){
        const x=node('span',klass);x.style.width=`${100*(Number(val[key]||0))/total}%`;bar.append(x);
      }const others=node('span','other');others.style.width=`${100*(total-Number(val.support||0)-Number(val.oppose||0))/total}%`;bar.append(others);card.append(bar);
        for(const k of ['support','oppose','conditional_or_amend','alternative_proposal','discussion_no_position','unclear','conflicting_or_multiple'])if(val[k]){
          const row=node('div','llm-row');row.append(node('span','',nice(k)),node('strong','',val[k]));card.append(row);
        }
      }
      const notes=Object.entries(p.claim_reason_counts||{}).sort((a,b)=>b[1]-a[1]).slice(0,3);
      if(notes.length)card.append(node('p','llm-small','Frequent reasons: '+notes.map(x=>`${nice(x[0])} (${x[1]} claims)`).join(', ')));
      if(p.examples?.length){const details=document.createElement('details');details.append(node('summary','','Read machine-selected FCC evidence'));for(const ex of p.examples.slice(0,5))details.append(evidenceCard(ex));card.append(details);}
      target.append(card);
    }
  }
  function renderQuality(d){
    const q=$('llm-quality');q.replaceChildren();
    const entries=[
      ['Full-text model reading', d.machine_evidence_quality?.semantic_scope_full_text_filings],
      ['Prioritized windows in long filings', d.machine_evidence_quality?.semantic_scope_prioritized_windows_filings],
      ['Filings with model-rejected or unmatched evidence', d.machine_evidence_quality?.filings_with_rejected_quotes_or_codes],
      ['Rejected evidence/claim rows',d.machine_evidence_quality?.invalid_claim_rows_rejected],
      ['Filings with uncertain claims',d.machine_evidence_quality?.filings_with_uncertain_claims],
      ['OCR-candidate filings completed',d.machine_evidence_quality?.ocr_candidate_filings],
      ['Filings with conflicting extracted positions',d.machine_evidence_quality?.filings_with_conflicting_claims],
      ['Filings without grounded policy claims',d.machine_evidence_quality?.filings_without_grounded_positions],
      ['Suggested source-linked human checks',d.suggested_human_audit_count]
    ];
    for(const [name,n] of entries){
      const line=node('div','llm-row');
      line.append(node('span','',name),node('strong','',n==null?'Not yet available':n.toLocaleString()));
      q.append(line);
    }
  }
  function showRoleMatrix(){
    const p=dataset.provisions.find(x=>x.provision_id===$('llm-role-proposal').value);
    const root=$('llm-role-positions');root.replaceChildren();
    if(!p)return;
    const entries=Object.entries(p.inferred_role_by_position||{})
      .map(([role,count])=>({role,total:Object.values(count).reduce((a,b)=>a+Number(b||0),0),count}))
      .sort((a,b)=>b.total-a.total);
    if(!entries.length){root.append(node('p','','No source-grounded positions completed for this provision yet.'));return;}
    const table=node('table');const head=node('thead');const tr=node('tr');
    for(const label of ['Inferred stakeholder role','Support','Oppose','Conditional','Alternative','Other / conflicting','Total filed positions'])
      tr.append(node('th','',label));
    head.append(tr);table.append(head);
    const body=node('tbody');
    for(const r of entries){
      const row=node('tr');
      const other=r.total-(r.count.support||0)-(r.count.oppose||0)-
        (r.count.conditional_or_amend||0)-(r.count.alternative_proposal||0);
      for(const v of [nice(r.role),r.count.support||0,r.count.oppose||0,
          r.count.conditional_or_amend||0,r.count.alternative_proposal||0,other,r.total])
        row.append(node('td','',v));
      body.append(row);
    }
    table.append(body);root.append(table);
  }
  async function renderAuditQueue() {
    const root=$('llm-review');root.replaceChildren();
    try{
      let response=await fetch(dataset.model==='gpt-oss:20b' ? './data/llm_kaggle_audit_queue.json' : dataset.model==='ibm/granite4.2:8b'
        ? './data/llm_mac_audit_queue.json' : './data/llm_audit_queue.json',{cache:'no-store'});
      if(!response.ok && dataset.model==='ibm/granite4.2:8b')
        response=await fetch('./data/llm_audit_queue.json',{cache:'no-store'});
      if(!response.ok)throw Error('not yet available');
      const queue=await response.json();
      if(queue.publication_status!=='MACHINE_GENERATED_REVIEW_SUGGESTIONS_ONLY')
        throw Error('unexpected audit status');
      root.append(node('p','llm-small',
        queue.selected+' suggested checks among '+queue.completed_filings+' fully analyzed filings. Unreviewed, not independent verification.'));
      for(const item of (queue.items||[]).slice(0,25)){
        const block=node('div','llm-evidence');
        block.append(node('strong','','Filing '+item.submission_id));
        block.append(node('p','llm-small',(item.review_reasons||[]).map(nice).join(' · ')));
        if(item.sample_quote)block.append(node('blockquote','',item.sample_quote));
        const link=node('a','','Read full source text ↗');
        link.href='./corpus.html?id='+encodeURIComponent(item.submission_id);
        block.append(link);
        root.append(block);
      }
    }catch(err){
      root.append(node('p','llm-small','Suggested reviews will appear after the first successful analysis batches.'));
    }
  }
  function renderPairs(d){
    const labels=Object.fromEntries(d.provisions.map(x=>[x.provision_id,x.label]));
    const root=$('llm-cooccurrence');root.replaceChildren();
    const pairs=(d.issue_cooccurrences||[]).slice(0,12);
    if(!pairs.length){root.append(node('p','','Issue co-occurrence will appear as filings finish processing.'));return;}
    for(const p of pairs){
      const line=node('div','llm-row');
      line.append(node('span','',(labels[p.provision_a]||p.provision_a)+' + '+
          (labels[p.provision_b]||p.provision_b)),
        node('strong','',Number(p.filings).toLocaleString()+' filings'));
      root.append(line);
    }
  }
  // Prefer more capable locally computed Granite 4.2 8B annotations when
  // published, falling back to the unattended free 1B/legacy preview.
  async function preferredAnalysis(){
    for(const p of ['./data/llm_kaggle_exploratory.json','./data/llm_mac_exploratory.json','./data/llm_exploratory.json']){
      try {
        const r=await fetch(p,{cache:'no-store'});
        if(!r.ok)continue;
        const d=await r.json();
        if(d.publication_status==='EXPLORATORY_UNVALIDATED_MACHINE_CLASSIFICATIONS'
           && d.completed_filings>0)return d;
      } catch (_) { /* Next published output may be usable. */ }
    }
    throw Error('No published machine-coded filings yet');
  }
  preferredAnalysis().then(d=>{
    if(d.publication_status!=='EXPLORATORY_UNVALIDATED_MACHINE_CLASSIFICATIONS')throw Error('unexpected status');
    dataset=d;status.textContent=`Exploratory machine coding · ${d.model} · updated ${new Date(d.generated_utc).toLocaleString()}. NOT human-validated.`;
    $('llm-stats').append(metric(d.indexed_filings,'Indexed filings in the available corpus'),
      metric(d.filings_with_text,'Readable filings available'),
      metric(d.completed_filings,'Fully processed by the model'),
      metric(d.distinct_normalized_texts_among_completed,'Unique exact-normalized texts processed'));
    const reason=$('llm-reasons');const top=Object.entries(d.argument_reason_counts||{}).sort((a,b)=>b[1]-a[1]).slice(0,10);
    if(!top.length)reason.append(node('p','','No claim estimates yet. The scheduled batches will update this section.'));
    for(const [r,n] of top){const line=node('div','llm-row');line.append(node('span','',nice(r)),node('strong','',n+' argument rows'));reason.append(line);}
    renderQuality(d);renderPairs(d);renderAuditQueue();
    const roleSelect=$('llm-role-proposal');
    const ordered=[...d.provisions].sort((a,b)=>Number(b.filings_mentioning)-Number(a.filings_mentioning));
    for(const p of ordered){const opt=node('option','',p.label);opt.value=p.provision_id;roleSelect.append(opt);}
    roleSelect.addEventListener('change',showRoleMatrix);
    if(ordered.length)showRoleMatrix();
    const select=$('llm-category');for(const cat of [...new Set(d.provisions.map(p=>p.category))].sort()){
      const op=node('option','',nice(cat));op.value=cat;select.append(op);
    }
    for(const id of ['llm-query','llm-category','llm-stance'])$(id).addEventListener('input',render);
    render();
  }).catch(()=>{status.textContent='The corpus is published, but the first complete LLM results are not yet available. No machine-derived findings will be shown before successfully processed filings exist.';
    $('llm-stats').append(metric(0,'Processed filings (nothing inferred yet)'));
    target.append(node('p','','Source texts are available in the full corpus reader. The free Granite workflow is processing comments in resumable batches.'));});
})();

