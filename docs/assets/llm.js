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
  fetch('./data/llm_exploratory.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('not yet present');return r.json();}).then(d=>{
    if(d.publication_status!=='EXPLORATORY_UNVALIDATED_MACHINE_CLASSIFICATIONS')throw Error('unexpected status');
    dataset=d;status.textContent=`Exploratory machine coding · ${d.model} · updated ${new Date(d.generated_utc).toLocaleString()}. NOT human-validated.`;
    $('llm-stats').append(metric(d.indexed_filings,'Indexed filings in the available corpus'),
      metric(d.filings_with_text,'Readable filings available'),
      metric(d.completed_filings,'Fully processed by the model'),
      metric(d.distinct_normalized_texts_among_completed,'Unique exact-normalized texts processed'));
    const reason=$('llm-reasons');const top=Object.entries(d.argument_reason_counts||{}).sort((a,b)=>b[1]-a[1]).slice(0,10);
    if(!top.length)reason.append(node('p','','No claim estimates yet. The scheduled batches will update this section.'));
    for(const [r,n] of top){const line=node('div','llm-row');line.append(node('span','',nice(r)),node('strong','',n+' argument rows'));reason.append(line);}
    const select=$('llm-category');for(const cat of [...new Set(d.provisions.map(p=>p.category))].sort()){
      const op=node('option','',nice(cat));op.value=cat;select.append(op);
    }
    for(const id of ['llm-query','llm-category','llm-stance'])$(id).addEventListener('input',render);
    render();
  }).catch(()=>{status.textContent='Awaiting the source-comment export and first successful scheduled LLM batch. No machine results have been generated or published yet.';
    $('llm-stats').append(metric(0,'Processed filings (nothing inferred yet)'));
    target.append(node('p','','Once corpus text is available in the repository, GitHub Actions can begin free resumable analysis.'));});
})();
