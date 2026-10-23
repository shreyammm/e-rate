'use strict';
/* Additive Kaggle evidence explorer for Ask the Corpus.
   The source scan still covers all original filings. This additionally scans
   every precomputed GPT-OSS claim. It does not claim to be a new LLM answer. */
(function(){
 if(typeof document==='undefined')return;
 const $=id=>document.getElementById(id);
 if(!$('ask-kaggle-panel'))return;
 const el=(tag,cls,text)=>{const d=document.createElement(tag);if(cls)d.className=cls;if(text!==undefined)d.textContent=String(text);return d;};
 const N=x=>Number(x||0).toLocaleString('en-US');
 const fcc=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(String(id));
 let memo=null;
 async function claims(){
  if(!memo)memo=fetch('./data/kaggle/machine_claim_rows.json',{cache:'default'}).then(r=>{
    if(!r.ok)throw Error('Kaggle source index returned HTTP '+r.status);
    return r.json();
  }).then(d=>{
    if(d.publication_status!=='EXPLORATORY_MODEL_ONLY'||!Array.isArray(d.rows)||d.rows.length!==14835||
       d.complete_model_filings!==3230)throw Error('Kaggle claim publication is incomplete');
    return d.rows;
  });
  return memo;
 }
 async function show(question){
  const status=$('ask-kaggle-status'),box=$('ask-kaggle-results');box.replaceChildren();
  $('ask-kaggle-deep').href='./kaggle.html?q='+encodeURIComponent(question)+'#questions';
  status.textContent='Cross-referencing every precomputed GPT-OSS 20B argument against this research question…';
  try{
   const engine=window.KaggleResearchCore;
   if(!engine?.searchAll)throw Error('Kaggle research engine missing');
   const records=await claims(),found=engine.searchAll(records,question);
   status.textContent=N(found.rowsSearched)+' Kaggle claim rows examined · '+N(found.matched.length)+
     ' potentially related claim rows across '+N(found.filings)+
     ' distinct filings. Concept/term matches are not verified supporters, opponents, or exhaustive semantic recall.';
   if(!found.matched.length){
     box.append(el('p','ask-warning','No precomputed claims matched these terms. This does not mean no commenter advanced the argument. Inspect the source-only search results below.'));
     return;
   }
   const reasons=new Map(),actions=new Map();
   for(const r of found.matched){
     reasons.set(r.reason_family,(reasons.get(r.reason_family)||0)+1);
     if(r.action){
       if(!actions.has(r.action))actions.set(r.action,new Set());
       actions.get(r.action).add(r.id);
     }
   }
   const reasonsEl=el('p','ask-muted','Reason families among matched machine claims: '+
      [...reasons].sort((a,b)=>b[1]-a[1]).slice(0,6).map(([k,v])=>k.replaceAll('_',' ')+' ('+N(v)+' claim rows)').join(' · '));
   box.append(reasonsEl);
   const acts=el('div','');
   acts.append(el('h3','','Requested actions found in matched evidence'));
   for(const [a,ids] of [...actions].sort((x,y)=>y[1].size-x[1].size).slice(0,6))
     acts.append(el('p','ask-small',N(ids.size)+' distinct filings · '+a));
   box.append(acts);
   const evidence=el('div','');evidence.append(el('h3','','Source-backed Kaggle interpretations — examples'));
   const seen=new Set();
   for(const item of found.ranked){
     const r=item.row;
     if(seen.has(r.id))continue;seen.add(r.id);
     const card=el('article','ask-source');
     const head=el('div','ask-source-top');
     const link=el('a','',r.organization||'FCC filing '+r.id);
     link.href=fcc(r.id);link.target='_blank';link.rel='noopener noreferrer';
     head.append(link,el('span','',r.id+' · '+r.reason_family.replaceAll('_',' ')));
     card.append(head);
     if(r.issue==='erate_sunset'){
       card.append(el('p','ask-warning','Sunset support/oppose direction requires audit; this machine label is not reliable.'));
     }else card.append(el('p','ask-small','Provisional machine issue: '+r.issue.replaceAll('_',' ')+' · '+r.position.replaceAll('_',' ')));
     if(r.action)card.append(el('p','', 'Requested: '+r.action));
     card.append(el('p','',r.argument||'No argument text extracted.'));
     if(r.quote)card.append(el('blockquote','',r.quote));
     const entire=el('a','', 'Read complete extracted filing ↗');entire.href='./corpus.html?id='+encodeURIComponent(r.id);
     card.append(entire);evidence.append(card);
     if(seen.size>=8)break;
   }
   box.append(evidence);
   box.append(el('p','ask-muted','Source cards are previews only; every matched claim contributed to the coverage counts. Open Kaggle Research Studio to inspect and export the complete evidence set. GPT-OSS labels are unvalidated, and the original source-only search remains independently accessible below.'));
  }catch(e){
   status.textContent='Kaggle claim evidence unavailable: '+e.message+'. The original source-only search remains available.';
  }
 }
 window.addEventListener('erate:scan-complete',e=>{
   const question=$('ask-question')?.value?.trim();
   if(question)show(question);
 });
 const input=$('ask-question');
 if(input)input.addEventListener('input',()=>{
   const question=input.value.trim();
   $('ask-kaggle-deep').href='./kaggle.html'+(question?'?q='+encodeURIComponent(question):'')+'#questions';
 });
})();