'use strict';
const $=id=>document.getElementById(id);
const number=n=>Number(n||0).toLocaleString('en-US');
const roleNames={unresolved:'No indicated institutional affiliation',school:'School/district/education',nonprofit:'Advocacy/association',library:'Library',government:'Government/Tribal body',business:'Other business',telecom:'Telecom/network organization',consultant:'Consultant/service firm'};
const statusNames={support:'Support',oppose:'Oppose',conditional:'Conditional/amend',alternative:'Alternative'};
const issueKeyMap={sunset_or_narrow:'erate_sunset',cipa_filtering:'cipa_social_media',screen_limits:'screen_time_condition',competitive_bidding:'administrative_forms',consultant_rules:'consultant_registration',radiofrequency:'erate_eligibility_scope',discount_matrix:'discount_matrix',special_construction:'special_construction',parent_opt_out:'parent_opt_out'};
const argumentCategories=[
['Legal authority','statutory|authority|section 254|statute|legal|cipa'],
['Access and affordability','afford|access|connectivity|infrastructure|cost|rural|tribal|funding|expense|subscription'],
['Implementation burden','burden|unworkable|administrative|paperwork|compliance|procurement|district operation|one-size|disrupt'],
['Child safety / learning','child|screen|development|student|learning|educational|edtech|parent'],
['Privacy / expression','privacy|surveillance|free.expression|censor|monitoring'],
['Oversight / incentives','consultant|integrity|fraud|incentive|compensation|registration|disclosure'],
['Market and competition','competition|provider|construction|build|competitive']
];
let summary,provisions={},allRecords=[],publishedIndex=false,filteredRecords=[],page=0,exampleLookup={};
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n;}
function aLink(label,url){const a=el('a','',label);a.href=url;a.rel='noopener noreferrer';a.target='_blank';return a;}
function fcc(sid){return 'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(String(sid));}
function clear(x){x.replaceChildren();}
function chart(target,arr,max,click){
 const box=$(target);clear(box);
 for(const r of arr){
  const line=el('div','bar-row'),label=el('span','bar-label');
  if(click){const b=el('button','',r.label);b.type='button';b.onclick=()=>click(r);label.append(b);}else label.textContent=r.label;
  const track=el('div','bar-track');const bar=el('div','bar-fill'+(target==='role-chart'?' role':''));
  bar.style.width=(max?Math.max(.2,r.n/max*100):0)+'%';track.append(bar);
  line.append(label,track,el('span','bar-value',number(r.n)));box.append(line);
 }
}
function openTab(name){
 const tab=Object.prototype.hasOwnProperty.call({overview:1,positions:1,arguments:1,commenters:1,explorer:1,methods:1},name)?name:'overview';
 document.querySelectorAll('.view').forEach(s=>s.hidden=s.id!==tab);
 document.querySelectorAll('.tabs button').forEach(b=>{if(b.dataset.view===tab)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
 if(location.hash!==('#'+tab))history.replaceState(null,'','#'+tab);
 if(tab==='explorer')renderExplorer();
}
function indexFallback(){
 const unique=new Map();
 for(const e of summary.examples){if(!unique.has(e.filing)){unique.set(e.filing,{id:e.filing,date:'',type:'',role:'unresolved',organization:e.name,issues:0,ocr:false,agency_candidate:false});}}
 allRecords=[...unique.values()];publishedIndex=false;
 $('explorer-loaded').textContent='Preview: '+number(allRecords.length)+' illustrative filings; full public index has not been generated';
}
function initMetrics(){
 const metrics=[
 [summary.indexed_filings,'ECFS filing records'],
 [summary.text_filings,'Filings with extracted text'],
 [summary.ocr_candidate_attachments,'Candidate OCR attachments'],
 [summary.examples.length,'Initial source-checked position examples']
 ];
 clear($('metrics'));
 for(const [value,label] of metrics){const m=el('div','metric');m.append(el('span','value',number(value)),el('span','caption',label));$('metrics').append(m);}
 $('status').textContent='Research snapshot · issue mentions across all available text; source-reviewed examples are not representative stance estimates.';
 chart('issue-chart',summary.issues,Math.max(...summary.issues.map(x=>x.n)),r=>{ $('ex-issue').value=r.id;page=0;openTab('explorer');});
 chart('role-chart',summary.roles.map(r=>({label:r.label,n:r.filings,id:r.id})),Math.max(...summary.roles.map(x=>x.filings)),r=>{$('ex-role').value=r.id;page=0;openTab('explorer');});
 const quality=$('data-qualifications');quality.append(el('h2','','How to read these numbers'));
 const row=el('div','record-line');
 for(const [n,t] of [
 ['2,193','Filings mention sunset, elimination or narrowing (not necessarily supporting these outcomes)'],
 ['277','Filings share one exact filer-name entry (8.6% of records)'],
 ['80.3%','Share of extracted text characters from that same filer-name entry']
 ]){const col=el('div','');col.append(el('strong','',n),el('p','note',t));row.append(col);}
 quality.append(row,el('p','note','The strongest published claims require source review. We do not label all issue mentions as positions or assume that every filing represents an independent commenter.'));
}
function renderDirectionalEvidence(){
 const box=$('directional-evidence');if(!box)return;clear(box);
 const census=summary.full_census;
 const head=el('div','panel-head');
 head.append(el('h2','','Position classification: distinguish wording from endorsement'),
   el('span','','Complete retrieval census · no sample-derived rates'));
 box.append(head);
 if(!census){box.append(el('p','note','The full-corpus role and policy-check dataset could not be loaded.'));return;}
 const preservation=census.argument_language_signals.find(x=>x.id==='continuity_without_sunset');
 const sunset=census.provisions.find(x=>x.id==='erate_sunset');
 const vals=el('div','record-line');
 for(const [n,label] of [
  [preservation.filings_with_language,'Filings using continuity / preservation-related expressions'],
  [sunset.mentions,'Filings matching the broader sunset / elimination question']
 ]){
  const item=el('div','');
  item.append(el('strong','',number(n)),el('p','note',label));vals.append(item);
 }
 box.append(vals);
 box.append(el('p','note','Neither figure is a validated support/opposition tally. We screened every filing against the codebook, but exact-word matching can retrieve the FCC question or a quoted position that the filer rejects. The remaining task is to adjudicate the requested regulatory outcome in each relevant filing; unknown positions are not zeros.'));
}
function showCensusProposals(census){
 const t=$('census-proposals');if(!t)return;clear(t);
 const rows=[...census.provisions].sort((a,b)=>b.mentions-a.mentions);
 for(const r of rows){
  const tr=el('tr');const name=provisions[r.id]?.label||r.id.replaceAll('_',' ');
  tr.append(el('td','',name),el('td','num',number(r.mentions)),
   el('td','num',number(r.agency_type_candidates)),
   el('td','num',number(r.other_docket_signature)));
  t.append(tr);
 }
}
async function installFullTextRoles(){
 const [census,roles]=await Promise.all([
   loadJson('./data/exhaustive_census.json'),
   loadJson('./data/full_text_filer_roles.json')
 ]);
 if(census.coverage.filings!==allRecords.length||roles.expected_records!==allRecords.length||
   allRecords[0].id!==roles.expected_first_id||
   allRecords[allRecords.length-1].id!==roles.expected_last_id){
   throw Error('Full-text role index is inconsistent with publication corpus');
 }
 if(typeof DecompressionStream!=='function')throw Error('Browser does not support compressed role map');
 const compressed=Uint8Array.from(atob(roles.sequence),c=>c.charCodeAt(0));
 const inflated=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
 const codeString=await new Response(inflated).text();
 if(codeString.length!==allRecords.length)throw Error('Reconciled role count mismatch');
 const observed={};
 for(let i=0;i<codeString.length;i++){
   const code=codeString[i],name=roles.legend[code];
   if(!name)throw Error('Unknown role code');
   observed[code]=(observed[code]||0)+1;
   allRecords[i].role=name;
 }
 for(const [key,n] of Object.entries(roles.expected_code_counts)){
   if(observed[key]!==n)throw Error('Role count integrity check failed for '+key);
 }
 const computed=Object.fromEntries(census.roles.map(r=>[r.id,0]));
 for(const rec of allRecords)computed[rec.role]=(computed[rec.role]||0)+1;
 if(census.roles.some(r=>computed[r.id]!==r.filings))throw Error('Aggregate roles do not reconcile to all records');
 summary.roles=census.roles.map(r=>({
   id:r.id,label:r.label,filings:r.filings,distinct_filer_fields:r.distinct_filer_fields
 }));
 for(const r of summary.roles)roleNames[r.id]=r.label;
 summary.issue_role_matrix={};
 for(const [i,issue] of summary.issues.entries()){
   const counts={};
   for(const row of allRecords){
     if(Number(row.issues)&(1<<i))counts[row.role]=(counts[row.role]||0)+1;
   }
   const sum=Object.values(counts).reduce((a,b)=>a+b,0);
   if(sum!==issue.n)throw Error('Issue cross-tab mismatch '+issue.id);
   summary.issue_role_matrix[issue.id]=counts;
 }
 showCensusProposals(census);
 const argumentRows=(census.argument_language_signals||[]).map(a=>({
   label:a.label,n:a.filings_with_language,id:a.id
 })).sort((a,b)=>b.n-a.n);
 if(argumentRows.length)chart('argument-census-bars',argumentRows,argumentRows[0].n);
 return census;
}
function selectedExamples(){
 const pid=$('position-proposal').value,dir=$('position-direction').value;
 return summary.examples.filter(e=>(!pid||e.issue===pid)&&(!dir||e.position===dir));
}
function drawPositions(){
 const rows=selectedExamples();const counts={support:0,oppose:0,conditional:0,alternative:0};
 rows.forEach(e=>counts[e.position]++);
 clear($('position-summary'));
 for(const key of Object.keys(counts)){const m=el('div','small-metric');m.append(el('strong','',counts[key]),el('span','',statusNames[key]));$('position-summary').append(m);}
 const body=$('position-table');clear(body);
 if(!rows.length){const tr=el('tr');const td=el('td','','No reviewed examples for this selection. This does not imply no commenters took that position.');td.colSpan=4;tr.append(td);body.append(tr);return;}
 for(const row of rows){
  const tr=el('tr');
  const position=el('span','direction '+row.position,statusNames[row.position]);
  const p=el('td');p.append(position);const action=el('td','',row.reason);
  action.append(el('div','excerpt','“'+row.quote+'”'));
  const link=el('td');link.append(aLink(row.filing,fcc(row.filing)));
  tr.append(el('td','',row.name),p,action,link);body.append(tr);
 }
}
function drawAlignment(){
 const used=['erate_sunset','screen_time_condition','parent_opt_out','consultant_registration','consultant_percent_fees','special_construction','cipa_social_media','cipa_monitoring_privacy','discount_matrix'];
 const short={erate_sunset:'Limit / sunset E-Rate',screen_time_condition:'Screen funding conditions',parent_opt_out:'Parental opt-out mandate',consultant_registration:'Consultant registration',consultant_percent_fees:'Percentage-fee ban',special_construction:'Limit construction',cipa_social_media:'Broaden CIPA social-media scope',cipa_monitoring_privacy:'CIPA monitoring/privacy',discount_matrix:'Change rural discounts'};
 const organizations=[...new Set(summary.examples.map(e=>e.name))].sort();
 const wrapper=$('alignment');clear(wrapper);const t=el('table','alignment'),thead=el('thead'),head=el('tr');
 head.append(el('th','','Organization'));
 for(const id of used)head.append(el('th','',short[id]));
 thead.append(head);t.append(thead);const tb=el('tbody');
 for(const org of organizations){
  const tr=el('tr');tr.append(el('td','',org));
  for(const id of used){
   const e=summary.examples.find(x=>x.name===org&&x.issue===id);
   const code=e?{support:'S',oppose:'O',conditional:'C',alternative:'A'}[e.position]:'—';
   const td=el('td',e?code.toLowerCase():'u',code);
   td.title=e?statusNames[e.position]+' — '+e.reason:'Not reviewed or not coded';
   tr.append(td);
  }
  tb.append(tr);
 }
 t.append(tb);wrapper.append(t);
 wrapper.append(el('p','note','S = support · O = oppose · C = conditional · A = alternative · — = not coded. Examples are first-pass and not independently adjudicated.'));
}
function reasonFamily(e){
 const s=(e.reason+' '+e.quote).toLowerCase();
 for(const [label,pattern] of argumentCategories){
  if(new RegExp(pattern,'i').test(s))return label;
 }
 return 'Other or multiple reasons';
}
function drawArguments(){
 const counts=new Map();for(const e of summary.examples){const family=reasonFamily(e);counts.set(family,(counts.get(family)||0)+1);}
 const arr=[...counts].map(([label,n])=>({label,n})).sort((a,b)=>b.n-a.n);
 chart('argument-chart',arr,Math.max(...arr.map(x=>x.n)));
 const filter=$('argument-filter');clear(filter);
 const all=el('option','','All reason categories');all.value='';filter.append(all);
 for(const r of arr){const option=el('option','',r.label);option.value=r.label;filter.append(option);}
 renderArgumentTable();
}
function renderArgumentTable(){
 const filter=$('argument-filter').value;const body=$('argument-table');clear(body);
 for(const row of summary.examples.filter(e=>!filter||reasonFamily(e)===filter)){
  const tr=el('tr'),issue=provisions[row.issue]?.label||row.issue,source=el('td');source.append(aLink(row.filing,fcc(row.filing)));
  const evidence=el('td','',row.reason);evidence.append(el('div','excerpt','“'+row.quote+'”'));
  tr.append(el('td','',row.name),el('td','',issue),evidence,source);body.append(tr);
 }
}
function drawRoles(){
 const table=$('role-table');clear(table);
 for(const r of summary.roles){
  const tr=el('tr'),share=(100*r.filings/summary.indexed_filings).toFixed(1)+'%';
  tr.append(el('td','',r.label),el('td','num',number(r.filings)),
     el('td','num',number(r.distinct_filer_fields)),el('td','num',share));table.append(tr);
 }
 const con=$('concentration');clear(con);
 con.append(el('h2','','Repeated submissions and text concentration'));
 con.append(el('p','','The largest exact filer-field string appears on 277 of 3,231 submissions, accounting for 80.3% of all extracted characters. This makes text-volume weighting especially misleading. It does not establish that these records are improper.'));
 con.append(el('p','','At least 565 filings contain one identifiable preserve-E-Rate template phrase; a related anti-sunset phrase appears in 637 filings. These are overlapping phrase matches, not independently validated template families. Exact full-text duplicate hashing found 73 filings in 17 clusters after OCR.'));
}
function drawIssueRoleComparison(){
 const id=$('role-issue').value;
 const counts=summary.issue_role_matrix?.[id]||{};
 const data=summary.roles.map(r=>({
   id:r.id,label:r.label,
   n:counts[r.id]||0,den:r.filings,
   percentage:r.filings?100*(counts[r.id]||0)/r.filings:0
 })).sort((a,b)=>b.percentage-a.percentage);
 const target=$('role-issue-chart');clear(target);
 for(const r of data){
   const line=el('div','bar-row'),outer=el('div','bar-track'),fill=el('div','bar-fill');
   fill.style.width=r.percentage+'%';outer.append(fill);
   line.append(el('span','bar-label',r.label),outer,
     el('span','bar-value',r.percentage.toFixed(1)+'%'));
   line.title=number(r.n)+' of '+number(r.den)+' records in this filer category mention the issue';
   target.append(line);
 }
}
function renderExplorer(){
 const query=$('ex-query').value.trim().toLocaleLowerCase();
 const issue=$('ex-issue').value,role=$('ex-role').value,type=$('ex-type').value,ocr=$('ex-ocr').value;
 let idx=-1;if(issue)idx=summary.issues.findIndex(r=>r.id===issue);
 const keys=summary.issues.map(x=>x.id);
 filteredRecords=allRecords.filter(r=>{
  if(query && !(r.id.toLowerCase().includes(query)||String(r.organization||'').toLowerCase().includes(query)))return false;
  if(role&&r.role!==role)return false;
  if(type&&r.type!==type)return false;
  if(ocr&&r.ocr!==(ocr==='yes'))return false;
  if(issue){
    if(!publishedIndex)return summary.examples.some(e=>e.filing===r.id&&(
       e.issue===issueKeyMap[issue]|| (issue==='cipa_filtering'&&e.issue.startsWith('cipa_')) ||
       (issue==='consultant_rules'&&e.issue.startsWith('consultant_'))));
    if(idx<0||!((Number(r.issues)||0)&(1<<idx)))return false;
  }
  return true;
 });
 const pages=Math.max(1,Math.ceil(filteredRecords.length/35));
 if(page>=pages)page=pages-1;if(page<0)page=0;
 $('ex-count').textContent=number(filteredRecords.length)+' '+(publishedIndex?'matching filing records':'illustrative records only');
 $('ex-page').textContent='Page '+(page+1)+' of '+pages;
 $('ex-prev').disabled=page===0;$('ex-next').disabled=page>=pages-1;
 const body=$('ex-table');clear(body);
 const subset=filteredRecords.slice(page*35,(page+1)*35);
 if(!subset.length){const tr=el('tr'),td=el('td','','No matching indexed filings.');td.colSpan=6;tr.append(td);body.append(tr);return;}
 for(const rec of subset){
   const tr=el('tr'),issues=el('td');
   const names=publishedIndex?keys.filter((k,i)=>Number(rec.issues)&(1<<i)).map(k=>summary.issues.find(x=>x.id===k)?.label||k):['Reviewed example'];
   for(const n of names.slice(0,5))issues.append(el('span','pill',n));
   if(names.length>5)issues.append(el('span','pill','+'+(names.length-5)));
   const source=el('td');source.append(aLink('FCC ↗',fcc(rec.id)));
   source.append(document.createTextNode(' · '));
   source.append(aLink('Full text ↗','./corpus.html?id='+encodeURIComponent(rec.id)));
   tr.append(el('td','',rec.id),el('td','',rec.date||'—'),
    el('td','',rec.organization||'Not republished'),
    el('td','',roleNames[rec.role]||rec.role),
    issues,source);body.append(tr);
 }
}
function setFilters(){
 const p=$('position-proposal');p.append(new Option('All reviewed proposals',''));
 for(const prov of Object.values(provisions))p.append(new Option(prov.label,prov.id));
 p.addEventListener('change',drawPositions);$('position-direction').addEventListener('change',drawPositions);
 const issue=$('ex-issue');
 for(const v of summary.issues)issue.append(new Option(v.label,v.id));
 const role=$('ex-role');for(const r of summary.roles)role.append(new Option(r.label,r.id));
 const compare=$('role-issue');
 for(const issue of summary.issues)compare.append(new Option(issue.label,issue.id));
 compare.value='sunset_or_narrow';
 compare.addEventListener('change',drawIssueRoleComparison);
 for(const v of [...new Set(allRecords.map(r=>r.type).filter(Boolean))].sort())$('ex-type').append(new Option(v,v));
 for(const id of ['ex-query','ex-issue','ex-role','ex-type','ex-ocr'])$(id).addEventListener(id==='ex-query'?'input':'change',()=>{page=0;renderExplorer();});
 $('ex-prev').onclick=()=>{page=Math.max(0,page-1);renderExplorer();};
 $('ex-next').onclick=()=>{page+=1;renderExplorer();};
 $('argument-filter').addEventListener('change',renderArgumentTable);
}
async function loadJson(path){const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw new Error(path+' returned '+r.status);return r.json();}
async function main(){
 try{
  const [data,book]=await Promise.all([loadJson('./data/research_dashboard.json'),loadJson('./data/provisions.json')]);
  summary=data;provisions=Object.fromEntries((book.provisions||[]).map(p=>[p.id,p]));
  const ids=Object.fromEntries(summary.examples.map(e=>[e.id,e]));exampleLookup=ids;
  try{
    const index=await loadJson('./data/corpus_index.json');
    if(!Array.isArray(index.filings)||index.filings.length!==summary.indexed_filings)throw new Error('partial publication');
    if(JSON.stringify(index.issue_keys)!==JSON.stringify(summary.issues.map(i=>i.id)))throw new Error('incompatible issue index');
    allRecords=index.filings;publishedIndex=true;
    try{
      const fullCensus=await installFullTextRoles();
      $('explorer-loaded').textContent=number(allRecords.length)+' filings indexed · full-text-derived provisional commenter categories';
      summary.full_census=fullCensus;
    }catch(e){
      console.warn('Unable to reconcile latest role counts:',e);
      $('explorer-loaded').textContent='Full filing index available; legacy name-field roles (full-text role update unavailable)';
    }
    $('explorer-loaded').textContent=number(allRecords.length)+' source-linked filing records indexed';
  }catch(e){indexFallback();}
  initMetrics();setFilters();renderDirectionalEvidence();drawPositions();drawAlignment();drawArguments();drawRoles();drawIssueRoleComparison();
  document.querySelectorAll('.tabs button').forEach(b=>b.addEventListener('click',()=>openTab(b.dataset.view)));
  window.addEventListener('hashchange',()=>openTab(location.hash.slice(1)));
  openTab(location.hash.slice(1)||'overview');
 }catch(e){$('status').textContent='Unable to load research data; please check the published files. '+e.message;}
}
document.addEventListener('DOMContentLoaded',main);