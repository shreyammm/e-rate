async function preferredClaimFile(name) {
  for (const base of ['./data/kaggle/', './data/']) {
    try {
      const r=await fetch(base+name,{cache:'no-store'});
      if(!r.ok)continue;
      const d=await r.json();
      if((d.coverage?.completed_machine_filings || d.complete_model_filings)>0)
        return {ok:true,json:async()=>d};
    } catch (_) {}
  }
  throw Error('No completed claim data yet');
}
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
     const r=await preferredClaimFile('claim_landscape.json');
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

/* All-claim table, separate from the group illustration cards. */
(function(){
 const $=id=>document.getElementById(id);
 if(!$('claim-row-table'))return;
 const make=(tag,txt)=>{const n=document.createElement(tag);n.textContent=String(txt??'');return n;};
 let rows=[],filtered=[],page=0;
 const size=45;
 const issueNames={other_policy_issue:'Other / novel policy issue'};
 function refresh(){
  const query=$('claim-row-query').value.toLowerCase().trim();
  const group=$('claim-row-group').value,role=$('claim-row-role').value,position=$('claim-row-position').value;
  filtered=rows.filter(r=>(!group||r.group===group)&&(!role||r.role===role)&&
      (!position||r.position===position)&&(!query||
      [r.id,r.organization,r.issue,r.action,r.argument,r.quote].join(' ').toLowerCase().includes(query)));
  const maxPage=Math.max(1,Math.ceil(filtered.length/size));
  if(page>=maxPage)page=maxPage-1;
  const table=$('claim-row-table');table.replaceChildren();
  for(const row of filtered.slice(page*size,(page+1)*size)){
    const tr=make('tr','');
    const source=make('td','');source.style.padding='10px';source.style.verticalAlign='top';source.style.borderBottom='1px solid #d7e1e8';
    const link=make('a',row.id);
    const u=String(row.source_url||'');
    if(/^https:\/\/www\.fcc\.gov\/ecfs\/filing\/\d+$/.test(u)){
      link.href=u;link.rel='noopener noreferrer';link.target='_blank';
    }
    source.append(link);
    const roleCell=make('td',row.organization||row.role.replaceAll('_',' '));
    const stance=make('td',(issueNames[row.issue]||row.issue.replaceAll('_',' '))+' · '+row.position.replaceAll('_',' '));
    const argument=make('td','');
    if(row.action)argument.append(make('p','Requested: '+row.action));
    if(row.argument)argument.append(make('p','Argument: '+row.argument));
    if(!row.argument&&!row.action)argument.append(make('p','No grounded action/reason extracted.'));
    const quote=make('blockquote','“'+row.quote+'”');quote.style.fontSize='.82rem';quote.style.opacity='.82';
    argument.append(quote);
    for(const col of [roleCell,stance,argument]){col.style.padding='10px';col.style.borderBottom='1px solid #d7e1e8';col.style.verticalAlign='top';}
    tr.append(source,roleCell,stance,argument);table.append(tr);
  }
  $('claim-row-count').textContent=filtered.length.toLocaleString('en-US')+' individually source-cited machine claims matched; '
     +rows.length.toLocaleString('en-US')+' total extracted claim rows available. All counts cover only completed machine-processed filings.';
  $('claim-row-page').textContent='Page '+(page+1)+' / '+maxPage;
  $('claim-row-prev').disabled=page===0;$('claim-row-next').disabled=page+1>=maxPage;
 }
 (async()=>{
  try{
   const r=await preferredClaimFile('machine_claim_rows.json');
   if(!r.ok)throw new Error('The next automatic analysis update has not published claim rows yet');
   const j=await r.json();
   if(!Array.isArray(j.rows)||j.publication_status!=='EXPLORATORY_MODEL_ONLY')throw new Error('Invalid machine-claim file');
   rows=j.rows;
   const groups=[...new Set(rows.map(x=>x.group))].sort();
   const roles=[...new Set(rows.map(x=>x.role))].sort();
   for(const v of groups){const o=make('option',v.replaceAll('_',' '));o.value=v;$('claim-row-group').append(o);}
   for(const v of roles){const o=make('option',v.replaceAll('_',' '));o.value=v;$('claim-row-role').append(o);}
   for(const id of ['claim-row-query','claim-row-group','claim-row-role','claim-row-position']){
     $(id).addEventListener(id==='claim-row-query'?'input':'change',()=>{page=0;refresh();});
   }
   $('claim-row-prev').onclick=()=>{page--;refresh();};
   $('claim-row-next').onclick=()=>{page++;refresh();};
   refresh();
  }catch(e){$('claim-row-count').textContent='Source-linked claim table not yet available: '+e.message;}
 })();
})();

