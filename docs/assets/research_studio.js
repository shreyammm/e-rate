"use strict";
(()=>{
 const $=id=>document.getElementById(id);
 $('studio-search').addEventListener('submit',ev=>{
   ev.preventDefault();
   const q=$('studio-query').value.trim();
   if(q.length<5)return;
   location.href='./ask.html?q='+encodeURIComponent(q);
 });
 document.querySelectorAll('[data-query]').forEach(btn=>btn.addEventListener('click',()=>{
   $('studio-query').value=btn.dataset.query;
   $('studio-query').focus();
 }));
 Promise.all([fetch('./data/exhaustive_census.json').then(r=>{if(!r.ok)throw Error('Census snapshot unavailable');return r.json()}),fetch('./data/argument_landscape.json').then(r=>{if(!r.ok)throw Error('Discovery data unavailable');return r.json()})]).then(([data,atlas])=>{
   const c=data.coverage||{};
   for(const [id,value] of [['studio-filings',c.filings],['studio-texts',c.filings_with_text],['studio-issues',data.argument_language_signals?.length],['studio-checks',atlas.language_themes?.length]])
     $(id).textContent=Number.isInteger(value)?value.toLocaleString('en-US'):'—';
   $('studio-status').textContent='Source: '+String(data.data_date||'published research snapshot')+' · Descriptive, not verified positions · '+String(data.source_basis||'FCC corpus');
 }).catch(err=>{$('studio-status').textContent='Census snapshot could not load: '+err.message});
})();