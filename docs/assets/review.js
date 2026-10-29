'use strict';
(()=>{const $=id=>document.getElementById(id),key='erate_manual_adjudications_v1';
const fields=['filing','topic','stakeholder','identity','detected','presence','stance','quality','action','quote','note','reviewer','reviewdate'];
let records=[];try{const x=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(x))records=x.filter(r=>r&&fields.every(k=>typeof r[k]==='string'));}catch(e){}
const source=()=>{const id=$('filing').value.trim();$('source-link').href=/^[0-9]{8,20}$/.test(id)?'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(id):'https://www.fcc.gov/ecfs/';};
function update(){const counts=new Map();for(const r of records){const k=r.filing+'|'+r.topic;const x=counts.get(k)||new Set();x.add(r.presence+'|'+r.stance);counts.set(k,x)}
const conflicting=[...counts.values()].filter(x=>x.size>1).length;
$('totals').textContent=records.length+' saved reviewer decisions across '+counts.size+' filing/topic pairs. '+conflicting+' pairs contain differing decisions requiring adjudication.';
const body=$('records');body.replaceChildren();for(const r of records.slice(-35).reverse()){const tr=document.createElement('tr');for(const v of [r.filing,r.topic,r.presence,r.stance,r.reviewer]){const td=document.createElement('td');td.textContent=v;tr.append(td)}body.append(tr)}}
$('filing').addEventListener('input',source);$('reviewdate').value=new Date().toISOString().slice(0,10);
$('review-form').addEventListener('submit',e=>{e.preventDefault();const r=Object.fromEntries(fields.map(f=>[f,$(f).value.trim()]));if(r.presence==='absent'&&r.stance!=='not_determined'){ $('message').textContent='An absent argument cannot have a verified stance. Change the stance.';return }
if(r.presence!=='present'&&['support','oppose','conditional','mixed'].includes(r.stance)){ $('message').textContent='A stance requires an argument attributed to this commenter.';return }
if(r.stance!=='not_determined'&&!r.action){$('message').textContent='Specify the policy action for a position decision.';return}
if(r.presence==='present'&&!r.quote){$('message').textContent='A present argument requires an original-source excerpt.';return}
if(records.some(x=>x.filing===r.filing&&x.topic===r.topic&&x.reviewer===r.reviewer)){$('message').textContent='This reviewer already saved this filing and topic. Export before making a revised review.';return}
records.push(r);try{localStorage.setItem(key,JSON.stringify(records));$('message').textContent='Saved locally. Export CSV to preserve your review.';}catch(err){records.pop();$('message').textContent='Browser storage unavailable; nothing was saved.';}update()});
$('export').addEventListener('click',()=>{const esc=x=>'"'+String(x??'').replace(/"/g,'""')+'"';const csv=[fields.join(','),...records.map(r=>fields.map(k=>esc(r[k])).join(','))].join('\r\n');const link=document.createElement('a');const blob=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));link.href=blob;link.download='erate_manual_source_reviews.csv';link.click();setTimeout(()=>URL.revokeObjectURL(blob),1000)});
$('clear').addEventListener('click',()=>{if(!confirm('Delete all locally saved reviews? Export a CSV first.'))return;records=[];localStorage.removeItem(key);update()});update();source()})();