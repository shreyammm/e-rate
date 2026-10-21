'use strict';
(function(){
 const $=id=>document.getElementById(id);
 if(!$('claim-coverage'))return;
 const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=String(value);if(cls)e.className=cls;return e;};
 const n=n=>Number(n||0).toLocaleString('en-US');
 let data=null;
 const makeLink=(url,label)=>{
   const a=text('a',label);
   const u=String(url||'');
   if(/^https:\/\/www\.fcc\.gov\/ecfs\/filing\/\d+$/.test(u)){
      a.href=u;a.target='_blank';a.rel='noopener noreferrer';
   }
   return a;
 };
 function metrics(){
   const box=$('claim-coverage');box.replaceChildren();
   const c=data.coverage;
   for(const [value,label] of [
     [c.completed_machine_filings,n(c.corpus_records)+' indexed filings analyzed semantically'],
     [c.machine_claim_rows,'Source-cited machine argument rows'],
     [c.filings_with_source_cited_claims,'Filings with at least one machine claim'],
     [c.remaining_or_incomplete_filings,'Not yet completed (never counted as neutral)']
   ]){
     const p=document.createElement('article');
     p.append(text('strong',n(value)),text('span',label,'llm-small'));
     box.append(p);
   }
 }
 function render(){
   const target=$('claim-groups');target.replaceChildren();
   const query=$('claim-search').value.trim().toLowerCase();
   const position=$('claim-position').value;
   const groups=data.clusters.filter(g=>{
     if(query && !(g.working_label+' '+g.examples.map(e=>e.argument+' '+e.requested_action).join(' ')).toLowerCase().includes(query))return false;
     if(position && !(g.stance_claim_rows||{})[position])return false;
     return true;
   });
   $('claim-result-count').textContent=groups.length+' argument-language groups found among '
      +n(data.coverage.completed_machine_filings)+' completed filings. This is incomplete and not an all-comment prevalence estimate.';
   for(const g of groups){
     const article=document.createElement('article');article.className='llm-issue';
     article.append(text('h3',g.working_label));
     const desc=text('p',n(g.distinct_filings)+' distinct filings · '+n(g.argument_rows)+' extracted claim rows · '
        +n(g.unique_source_texts)+' distinct source texts','llm-small');
     article.append(desc);
     const labels=Object.entries(g.role_filings||{}).sort((a,b)=>b[1]-a[1]).slice(0,6);
     if(labels.length){const role=text('p','Commenter categories (filings): '+labels.map(([k,v])=>k.replaceAll('_',' ')+' '+n(v)).join(' · '),'llm-small');article.append(role);}
     const counts=Object.entries(g.stance_claim_rows||{}).map(([k,v])=>k.replaceAll('_',' ')+': '+n(v));
     if(counts.length)article.append(text('p','Machine-coded claim directions: '+counts.join(' · '),'llm-small'));
     const details=document.createElement('details');
     details.append(text('summary','Source-linked argument examples (illustrative only)'));
     for(const row of g.examples){
       const wrap=document.createElement('div');wrap.className='llm-evidence';
       wrap.append(makeLink(row.source_url,'FCC filing '+row.submission_id+' ↗'));
       if(row.argument)wrap.append(text('p',row.argument,'llm-small'));
       else if(row.requested_action)wrap.append(text('p','Requested action: '+row.requested_action,'llm-small'));
       if(row.quote)wrap.append(text('blockquote','“'+row.quote+'”'));
       details.append(wrap);
     }
     article.append(details);target.append(article);
   }
 }
 (async()=>{
   try{
     const r=await fetch('./data/claim_landscape.json',{cache:'no-store'});
     if(!r.ok)throw new Error('Claim map has not finished its first refresh');
     data=await r.json();
     if(!data?.coverage?.completed_machine_filings || !Array.isArray(data.clusters))
       throw new Error('No completed claim data yet');
     metrics();
     $('claim-search').addEventListener('input',render);
     $('claim-position').addEventListener('change',render);
     render();
   }catch(e){
     $('claim-coverage').replaceChildren(text('p','The full-corpus argument extractor is still running. '+e.message+'; the existing full-text corpus and argument-language explorer remain available.','llm-small'));
     $('claim-result-count').textContent='No model-wide argument percentages are available until the required records are processed.';
   }
 })();
})();