'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const el=(tag,cls,value)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(value!==undefined)x.textContent=String(value);return x;};
  const n = value => Number(value||0).toLocaleString('en-US');
  const human = s=>String(s||'').replaceAll('_',' ');
  let data=null;
  function link(label,id){const a=el('a','',label+' ↗');a.href='./corpus.html?id='+encodeURIComponent(id);a.rel='noopener noreferrer';return a;}
  function results(){
    const box=$('landscape-list');if(!box||!data)return;
    const view=$('landscape-kind').value;
    const items=view==='llm'?data.llm_argument_map.clusters:data.language_themes;
    const query=$('landscape-query').value.trim().toLowerCase();
    const role=$('landscape-role').value;
    const filtered=items.filter(x=>{
      const label=x.working_label||x.auto_label;
      const all=[label,(x.topic_terms||[]).join(' '),JSON.stringify(x.leading_filers||x.top_filers),
         JSON.stringify(x.evidence||x.examples)].join(' ').toLowerCase();
      return (!query||all.includes(query))&&(!role||Number((x.filing_categories||x.stakeholders||{})[role]||0)>0);
    });
    box.replaceChildren();
    $('landscape-result-count').textContent=n(filtered.length)+' displayed clusters';
    if(view==='llm'&&!items.length){box.append(el('p','llm-small','No completed source-cited LLM argument clusters are available yet. Automatic Granite extraction runs separately, and this section will populate as its batches complete.'));return;}
    for(const c of filtered){
      const card=el('article','llm-issue');
      card.append(el('h3','',c.llm_synthesis?.label||c.working_label||c.auto_label));
      if(c.llm_synthesis?.argument_summary){
        card.append(el('p','',c.llm_synthesis.argument_summary));
        if(c.llm_synthesis.other_perspectives)
          card.append(el('p','llm-small','Different perspectives in selected examples: '+c.llm_synthesis.other_perspectives));
        card.append(el('p','llm-small','Automatically summarized by US IBM Granite from linked sample passages. This is not a corpus-wide stance estimate.'));
      }
      const filingN=view==='llm'?c.filings:c.filings_with_matching_language;
      card.append(el('p','llm-small',n(filingN)+' filing records with '+(view==='llm'?'LLM-extracted argument claims':'related argument-language patterns')+' · machine-organized; not validated positions'));
      const roles=Object.entries(c.filing_categories||c.stakeholders||{}).sort((a,b)=>b[1]-a[1]).slice(0,5);
      if(roles.length)card.append(el('p','llm-small','Tentative commenter types: '+roles.map(r=>human(r[0])+' ('+n(r[1])+')').join(' · ')));
      const stance=Object.entries(c.positions||{}).sort((a,b)=>b[1]-a[1]);
      if(view==='llm'&&stance.length)card.append(el('p','llm-small','Machine-coded positions: '+stance.map(x=>human(x[0])+' '+n(x[1])).join(' · ')));
      const filers=c.leading_filers||c.top_filers||[];
      if(filers.length)card.append(el('p','llm-small','Frequent filer fields: '+filers.slice(0,4).map(r=>r.name+' ('+n(r.n||r.claims||0)+')').join(' · ')));
      const examples=c.evidence||c.examples||[];
      const details=el('details');details.append(el('summary','','Read sourced passages ('+n(examples.length)+' examples)'));
      for(const e of examples){
        const item=el('div','llm-evidence');item.append(el('strong','',e.filer||'FCC filing '+e.id));
        if(e.argument)item.append(el('p','llm-small',e.argument));
        item.append(el('blockquote','',e.quote));item.append(link('Read complete comment',e.id));details.append(item);
      }
      card.append(details);box.append(card);
    }
    if(!filtered.length)box.append(el('p','llm-small','No clusters match those filters. Try another term or commenter type.'));
  }
  async function init(){
    const x=$('landscape-status');if(!x)return;
    try{
      const response=await fetch('./data/argument_landscape.json',{cache:'no-store'});
      if(!response.ok)throw Error('argument map not yet published');
      const d=await response.json();
      if(d.source_filings_scanned!==3231||d.readable_filings!==3230)throw Error('incomplete source coverage');
      data=d;
      x.textContent='Exploratory whole-corpus landscape · '+n(d.source_filings_scanned)+' filings scanned · '+n(d.extracted_argument_language_passages)+' argument-like passages · '+n(d.language_themes.length)+' preliminary themes.';
      $('landscape-llm-status').textContent=n(d.llm_argument_map.completed_filings)+' fully analyzed filings · '+n(d.llm_argument_map.claims)+' source-backed extracted claim rows · '+n(d.llm_argument_map.clusters.length)+' emerging AI argument groups.';
      for(const p of [d.language_themes,d.llm_argument_map.clusters]){
        for(const c of p){for(const name of Object.keys(c.filing_categories||c.stakeholders||{})){
          if(![...$('landscape-role').options].some(o=>o.value===name))$('landscape-role').append(new Option(human(name),name));
        }}
      }
      for(const id of ['landscape-kind','landscape-query','landscape-role'])$(id).addEventListener(id==='landscape-query'?'input':'change',results);
      results();
    }catch(e){x.textContent='Awaiting automatically generated argument landscape: '+e.message;}
  }
  document.addEventListener('DOMContentLoaded',init);
})();