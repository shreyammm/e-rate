'use strict';
/* Kaggle Research Studio.
   Data: ALL published Kaggle machine_claim_rows, full claim landscape, original
   filing metadata, model summary, and the risk-enriched human audit queue.
   No silent sampling for counts; excerpt cards/pagination are navigation only.
   No machine "support for sunsetting" tally is published without polarity audit.
*/
(function(root){
 const STOP=new Set('a an the of for from to in at as by about is was were be been and or but with within which who whom what when where why how that this those these there their its it we our i my you your they them do does did doing will would could should have has had can are any many some all every comments comment commenter commenters filing filings fcc erate e rate show tell explain describe compare what whether were concerns concerns policy program issue question position argument arguments'.split(' '));
 const ALIASES={
  'screen':['screen','screens','screen time','screen-time','screentime','device use','device time','digital media','time online'],
  'fund':['fund','funding','subsidy','subsidies','discount','e-rate','erate','reimburse','support'],
  'cut':['cut','cuts','reduce','reduction','sunset','eliminate','elimination','terminate','narrow','withdraw','defund'],
  'privacy':['privacy','surveillance','monitoring','browsing history','data collection','tracking','student records'],
  'child':['child','children','minors','students','youth','online safety','child safety'],
  'rural':['rural','remote','tribal','underserved','frontier','small districts'],
  'library':['library','libraries','librarian'],
  'consultant':['consultant','consultants','registration','fees','filing agent'],
  'afford':['affordable','affordability','cost','costs','financial','expense','budget'],
  'filter':['filter','filtering','cipa','web blocking','technology protection'],
  'broadband':['broadband','connectivity','internet','network','bandwidth'],
  'parent':['parent','parents','guardian','opt out','parental'],
  'cyber':['cybersecurity','cyber','security','ransomware'],
  'audit':['audit','oversight','fraud','integrity','compliance'],
  'teacher':['teacher','teachers','educator','classroom','instruction']
 };
 const phraseNormalize=t=>String(t||'').toLowerCase().replace(/[’']/g,'').replace(/[^a-z0-9 ]+/g,' ').replace(/\s+/g,' ').trim();
 const tokens=t=>(phraseNormalize(t).match(/[a-z0-9]{3,}/g)||[]).filter(w=>!STOP.has(w));
 const unique=xs=>[...new Set(xs)];
 const countIds=xs=>new Set(xs.map(r=>String(r.id||''))).size;
 const n=x=>Number(x||0).toLocaleString('en-US');
 const fcc=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(String(id));
 const corpus=id=>'./corpus.html?id='+encodeURIComponent(String(id));
 const friendly=s=>String(s||'Not classified').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
 const stanceRisk=r=>r.issue==='erate_sunset' && ['support','oppose','conflicting_or_multiple'].includes(r.position);
 const riskLabel=r=>stanceRisk(r)?'Polarity not validated':friendly(r.position||'unclear')+' (machine)';
 const quoteLinkSafe=u=>/^https:\/\/www\.fcc\.gov\/ecfs\/filing\/\d+$/.test(String(u||'')); 
 function questionConcepts(question){
   const q=phraseNormalize(question),matched=new Set();
   for(const [key,variants] of Object.entries(ALIASES))if(variants.some(v=>q.includes(phraseNormalize(v))))matched.add(key);
   const unexpanded=tokens(question).filter(w=>!Object.entries(ALIASES).some(([key,vs])=>matched.has(key)&&vs.some(v=>phraseNormalize(v).split(' ').includes(w))));
   return {concepts:[...matched],terms:unique(unexpanded)};
 }
 function searchAll(rows,question){
   const {concepts,terms}=questionConcepts(question);
   const patterns=concepts.map(c=>ALIASES[c].map(phraseNormalize));
   let candidates=[];
   for(const r of rows){
     const issue=phraseNormalize(r.issue),base=phraseNormalize([r.argument,r.action,r.quote,r.organization,r.reason_family,r.claim_kind,r.role,issue].join(' '));
     let hits=0,score=0;
     for(const variants of patterns)if(variants.some(v=>base.includes(v))){hits++;score+=3;}
     for(const t of terms)if(base.includes(t)){hits++;score+=1.8;}
     if(r.argument)for(const t of terms)if(phraseNormalize(r.argument).includes(t))score+=1;
     if(r.action)for(const t of terms)if(phraseNormalize(r.action).includes(t))score+=.4;
     if(concepts.includes('cut')&&issue==='erate sunset')score+=.5;
     if(hits) candidates.push({row:r,score,hits});
   }
   candidates.sort((a,b)=>b.score-a.score||String(a.row.id).localeCompare(String(b.row.id)));
   const distinct=new Set(candidates.map(x=>x.row.id));
   const allMatched=candidates.map(x=>x.row);
   const matchedReason={};
   for(const r of allMatched) matchedReason[r.reason_family]=(matchedReason[r.reason_family]||0)+1;
   return {question,rowsSearched:rows.length,matched:allMatched,ranked:candidates,
      filings:distinct.size,reasonCounts:matchedReason,queryConcepts:concepts,freeTerms:terms};
 }
 function issueStats(rows,issue,role){
   const selected=rows.filter(r=>r.issue===issue&&(!role||r.role===role));
   const reasons={},actions={},roles={};
   for(const r of selected){
     reasons[r.reason_family]=(reasons[r.reason_family]||0)+1;
     const a=String(r.action||'').trim();
     if(a)actions[a]=(actions[a]||new Set()).add(r.id);
     if(!roles[r.role])roles[r.role]=new Set();roles[r.role].add(r.id);
   }
   return {claims:selected.length,filings:countIds(selected),rows:selected,reasons,
     actions:Object.entries(actions).map(([label,ids])=>({label,value:ids.size})).sort((a,b)=>b.value-a.value),
     roles:Object.entries(roles).map(([label,ids])=>({label,value:ids.size})).sort((a,b)=>b.value-a.value)};
 }
 const formatCsvCell=s=>'"'+String(s??'').replace(/^[=+\-@\t\r]/,"'$&").replace(/"/g,'""')+'"';
 function safeCsv(headers,rows){
   return [headers.map(formatCsvCell).join(','),...rows.map(r=>headers.map(h=>formatCsvCell(r[h])).join(','))].join('\r\n');
 }
 const API={tokens,questionConcepts,searchAll,issueStats,stanceRisk,riskLabel,safeCsv,ALiASES:ALIASES};
 if(typeof module!=='undefined'&&module.exports)module.exports=API;
 if(root)root.KaggleResearchCore=API;
 if(!root.document)return;
 const $=id=>document.getElementById(id);
 if(!$('kr-status'))return;
 const el=(tag,cls,text)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=String(text);return x};
 const link=(title,url)=>{const a=el('a','',title);a.href=url;if(url.startsWith('https:')){a.target='_blank';a.rel='noopener noreferrer'}return a};
 const empty=id=>{const x=$(id);if(x)x.replaceChildren();return x};
 const state={rows:[],landscape:null,summary:null,quality:null,meta:new Map(),audit:[],issues:[],roleNames:[],
    selectedGroup:'',ledgerFiltered:[],ledgerPage:0,ledgerFocusRows:null,auditFiltered:[],auditPage:0,auditState:{},queryResult:null};
 const ISSUE_UNSAFE=new Set(['erate_sunset']);
 const writeCount=(id,text)=>{$(id).textContent=text};
 const roleName=s=>friendly(s||'unresolved');
 function pill(t,risk=false){return el('span','kr-pill'+(risk?' kr-risk':''),t)}
 function option(select,value,label){const o=el('option','',label);o.value=value;select.append(o);}
 function stat(v,label){const c=el('div','kr-kpi');c.append(el('strong','',n(v)),el('span','',label));return c}
 function setStatus(s,error=false){$('kr-status').textContent=s;$('kr-status').classList.toggle('kr-error',error);}
 function download(filename,contents,type){
   const blob=new Blob([contents],{type:type||'text/csv;charset=utf-8;'});
   const href=URL.createObjectURL(blob),a=el('a');a.href=href;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),2000);
 }
 function getAuditState(){
   try{return JSON.parse(localStorage.getItem('fcc-kaggle-audit-v1')||'{}')||{}}catch(_){return {}}
 }
 function setAuditState(){try{localStorage.setItem('fcc-kaggle-audit-v1',JSON.stringify(state.auditState))}catch(_){}}
 function strongQuote(r){
   const card=el('article','kr-evidence');
   const header=el('div','');
   header.append(link(r.organization||state.meta.get(String(r.id))?.organization||('FCC filing '+r.id),fcc(r.id)),document.createTextNode(' · '+r.id+' · '+roleName(r.role)));
   card.append(header);
   const tags=el('div','');
   tags.append(pill(friendly(r.issue)),pill(riskLabel(r),stanceRisk(r)));
   if(r.reason_family)tags.append(pill(friendly(r.reason_family)));
   if(r.ocr_candidate||state.meta.get(String(r.id))?.ocr)tags.append(pill('OCR candidate',true));
   card.append(tags);
   if(r.action)card.append(el('h4','','Requested action: '+r.action));
   if(r.argument)card.append(el('p','','Machine argument: '+r.argument));
   if(r.quote)card.append(el('blockquote','',r.quote));
   const footer=el('div','');
   footer.append(link('Original FCC filing ↗',fcc(r.id)),link('Full extracted comment ↗',corpus(r.id)));
   footer.append(el('span','kr-muted','Source text offset '+n(r.start??0)));
   card.append(footer);
   return card;
 }
 function bars(container,pairs,maxItems=10){
   container.replaceChildren();
   const sorted=pairs.map(([label,val])=>({label,value:val})).sort((a,b)=>b.value-a.value).slice(0,maxItems);
   if(!sorted.length){container.append(el('p','kr-muted','No classified evidence in the selected group.'));return}
   const max=sorted[0].value||1;
   for(const item of sorted){const r=el('div','kr-bar');const label=el('span','',friendly(item.label));const track=el('div','kr-bar-track');const fill=el('div','kr-bar-fill');fill.style.width=Math.max(1,100*item.value/max)+'%';track.append(fill);r.append(label,track,el('b','',n(item.value)));container.append(r);}
 }
 function fromCounts(o){return Object.entries(o||{}).map(([k,v])=>[k,Number(v)]);}
 function initStats(){
   const area=empty('kr-kpis');
   const c=state.landscape.coverage,q=state.summary.machine_evidence_quality||{};
   [[c.completed_machine_filings,'Readable filings processed'],
    [c.machine_claim_rows,'Source-linked claim rows'],
    [c.filings_with_source_cited_claims,'Filings with machine claims'],
    [state.landscape.clusters.length,'Exploratory argument groups'],
    [q.semantic_scope_prioritized_windows_filings,'Selective-text long filings'],
    [q.filings_without_grounded_positions,'No extracted position']].forEach(([v,t])=>area.append(stat(v,t)));
   const quality=empty('kr-quality');
   [[q.semantic_scope_full_text_filings,'Full-text model reading'],
    [q.semantic_scope_prioritized_windows_filings,'Prioritized-window readings'],
    [q.filings_with_conflicting_claims,'Filings with mixed-coded claims'],
    [q.filings_with_uncertain_claims,'Filings with model uncertainty'],
    [q.ocr_candidate_filings,'Unreviewed OCR candidates'],
    [state.audit.length,'Human-audit candidates']].forEach(([v,t])=>quality.append(stat(v,t)));
 }
 function updateLedgerFilters(){
   const q=$('kr-ledger-q').value.trim().toLowerCase(),issue=$('kr-ledger-issue').value,
   reason=$('kr-ledger-reason').value,role=$('kr-ledger-role').value,
   stance=$('kr-ledger-stance').value,group=$('kr-ledger-group').value,
   quality=$('kr-ledger-quality').value,sort=$('kr-ledger-sort').value;
   const selected=state.rows.filter(r=>(!state.ledgerFocusRows||state.ledgerFocusRows.has(r))&&(!issue||r.issue===issue)&&(!reason||r.reason_family===reason)&&
     (!role||r.role===role)&&(!stance||r.position===stance)&&(!group||r.group===group)&&
     (!quality||(quality==='sunset'?stanceRisk(r):(r.ocr_candidate||state.meta.get(String(r.id))?.ocr)))&&
     (!q||[r.id,r.organization,r.issue,r.position,r.reason_family,r.claim_kind,r.group,r.action,r.argument,r.quote].join(' ').toLowerCase().includes(q)));
   if(sort==='issue')selected.sort((a,b)=>a.issue.localeCompare(b.issue)||a.id.localeCompare(b.id));
   else if(sort==='filer')selected.sort((a,b)=>(a.organization||'').localeCompare(b.organization||'')||a.id.localeCompare(b.id));
   else selected.sort((a,b)=>String(a.id).localeCompare(String(b.id))||Number(a.start||0)-Number(b.start||0));
   state.ledgerFiltered=selected;
   showLedger();
 }
 function showLedger(){
   const filtered=state.ledgerFiltered,per=30,pages=Math.max(1,Math.ceil(filtered.length/per));
   state.ledgerPage=Math.min(pages-1,state.ledgerPage);
   const box=empty('kr-ledger-results');
   for(const r of filtered.slice(state.ledgerPage*per,(state.ledgerPage+1)*per))box.append(strongQuote(r));
   writeCount('kr-ledger-count',(state.ledgerFocusRows?'Question-related evidence · ':'')+n(filtered.length)+' source-linked claim rows across '+n(countIds(filtered))+
     ' distinct filings; all '+n(state.rows.length)+' model rows examined. Page displays only 30 for readability.');
   writeCount('kr-page','Page '+(state.ledgerPage+1)+' of '+pages);
   $('kr-prev').disabled=state.ledgerPage===0;
   $('kr-next').disabled=state.ledgerPage>=pages-1;
 }
 function ledgerLink(label,filters){
   const button=el('button','kr-action-button',label);
   button.onclick=()=>{
     for(const [id,value] of Object.entries(filters))if($(id))$(id).value=value;
     state.ledgerPage=0;updateLedgerFilters();$('ledger').scrollIntoView({behavior:'smooth',block:'start'});
   };
   return button;
 }
 function clusterLabel(g){
   const ex=g.examples?.find(x=>x.argument&&x.argument.length>28);
   return ex?String(ex.argument).replace(/[\n\r]+/g,' ').slice(0,110):friendly(g.working_label);
 }
 function renderClusters(){
   const query=$('kr-cluster-query').value.trim().toLowerCase(),issue=$('kr-cluster-issue').value,sort=$('kr-cluster-sort').value;
   const arr=state.landscape.clusters.filter(g=>(!issue||(g.issue_filings||{})[issue])&&
     (!query||[g.working_label,clusterLabel(g),...(g.examples||[]).map(e=>e.argument+' '+e.requested_action)].join(' ').toLowerCase().includes(query)));
   const by=sort==='unique'?'unique_source_texts':sort==='claims'?'argument_rows':'distinct_filings';
   arr.sort((a,b)=>b[by]-a[by]||a.id.localeCompare(b.id));
   writeCount('kr-cluster-count',arr.length+' of '+state.landscape.clusters.length+' exploratory claim groups; multi-label filing counts may overlap.');
   const list=empty('kr-cluster-list');
   for(const g of arr){
     const btn=el('button','kr-cluster-item');btn.type='button';btn.setAttribute('aria-pressed',String(g.id===state.selectedGroup));
     btn.append(el('strong','',clusterLabel(g)),el('small','',n(g.distinct_filings)+' filings · '+n(g.argument_rows)+' claim rows'));
     btn.append(pill('Working terms: '+g.working_label));
     btn.onclick=()=>{state.selectedGroup=g.id;renderClusters();renderGroup(g);};list.append(btn);
   }
   if(arr.length&&!arr.some(g=>g.id===state.selectedGroup)){state.selectedGroup=arr[0].id;renderGroup(arr[0]);for(const b of list.querySelectorAll('button'))b.setAttribute('aria-pressed',String(b.textContent.includes(clusterLabel(arr[0]))));}
   if(!arr.length)empty('kr-cluster-detail').append(el('p','','No groups match. Broaden the filters.'));
 }
 function renderGroup(g){
   const area=empty('kr-cluster-detail');area.append(el('p','kr-eyebrow','Exploratory group '+g.id),el('h3','',clusterLabel(g)),
     el('p','kr-muted','Machine-discovered working terms: '+g.working_label));
   const stats=el('div','kr-kpis');
   [[g.distinct_filings,'Distinct filings'],[g.unique_source_texts,'Distinct normalized texts'],[g.argument_rows,'Extracted claim rows']].forEach(([v,t])=>stats.append(stat(v,t)));
   area.append(stats);
   const inGroup=state.rows.filter(r=>r.group===g.id);
   const topReasons={};for(const r of inGroup)topReasons[r.reason_family]=(topReasons[r.reason_family]||0)+1;
   area.append(el('h3','','Reason language in this group'));
   const chart=el('div','kr-bars');bars(chart,fromCounts(topReasons),8);area.append(chart);
   area.append(ledgerLink('Inspect all '+n(inGroup.length)+' source claims →',{'kr-ledger-group':g.id,'kr-ledger-q':''}));
   area.append(el('p','kr-muted','Below are illustrative examples; the full evidence ledger contains every extracted claim in this group.'));
   for(const r of inGroup.slice(0,3))area.append(strongQuote(r));
 }
 function issueConnections(){
   const all=state.summary.issue_cooccurrences||[],max=all[0]?.filings||1;
   const target=empty('kr-issue-links');
   for(const e of all.slice(0,12)){
     const wrap=el('div','kr-bar'),label=el('span','',issueName(e.provision_a)+' + '+issueName(e.provision_b));
     const track=el('div','kr-bar-track'),fill=el('div','kr-bar-fill');
     fill.style.width=100*e.filings/max+'%';track.append(fill);wrap.append(label,track,el('b','',n(e.filings)));
     target.append(wrap);
   }
 }
 function issueName(id){return state.issues.find(x=>x.provision_id===id)?.label||friendly(id);}
 function groupPeople(){
   const group=$('kr-person-group').value,term=$('kr-org-query').value.toLowerCase().trim(),issue=$('kr-org-issue').value;
   let selected=state.rows.filter(r=>(!issue||r.issue===issue)&&(!term||
    [r.id,r.organization,r.role,r.action,r.argument].join(' ').toLowerCase().includes(term)));
   const map=new Map();
   for(const r of selected){const key=group==='organization'?(r.organization?.trim()||'Unspecified organization'):roleName(r.role);
     if(!map.has(key))map.set(key,{label:key,ids:new Set(),rows:0,issues:new Map(),reasons:new Map(),examples:[]});
     const x=map.get(key);x.ids.add(r.id);x.rows++;
     if(!x.issues.has(r.issue))x.issues.set(r.issue,new Set());x.issues.get(r.issue).add(r.id);
     x.reasons.set(r.reason_family,(x.reasons.get(r.reason_family)||0)+1);
     if(x.examples.length<1)x.examples.push(r);
   }
   const entries=[...map.values()].sort((a,b)=>b.ids.size-a.ids.size||a.label.localeCompare(b.label));
   writeCount('kr-org-count',n(entries.length)+' '+(group==='organization'?'organization labels':'commenter categories')+
     ' among '+n(countIds(selected))+' filings with extracted claims. Not a verified count of independent people.');
   const box=empty('kr-people-results');const cards=el('div','kr-cards');
   for(const entry of entries.slice(0,group==='organization'?60:100)){
     const card=el('article','kr-card');card.append(el('h3','',entry.label),el('p','kr-muted',n(entry.ids.size)+' distinct filings · '+n(entry.rows)+' claim rows'));
     const primary=[...entry.issues.entries()].map(([k,v])=>({k,v:v.size})).sort((a,b)=>b.v-a.v).slice(0,4);
     card.append(el('p','',primary.map(x=>issueName(x.k)+' ('+n(x.v)+' filings)').join(' · ')));
     const example=entry.examples[0];if(example){
       card.append(el('p','kr-muted','Example: '+(example.argument||example.action||'No argument text').slice(0,145)));
       card.append(link('Inspect filing ↗',fcc(example.id)));}
     const btn=el('button','kr-action-button','View all matching claims');
     btn.onclick=()=>{
       $('kr-ledger-q').value=group==='organization'&&entry.label!=='Unspecified organization'?entry.label:'';
       $('kr-ledger-role').value=group==='role'?(selected.find(r=>roleName(r.role)===entry.label)?.role||''):'';
       $('kr-ledger-issue').value=issue;
       state.ledgerPage=0;updateLedgerFilters();$('ledger').scrollIntoView({behavior:'smooth'});
     };card.append(btn);cards.append(card);
   }
   box.append(cards);
   if(entries.length>60&&group==='organization')box.append(el('p','kr-muted','Showing first 60 organizations. Use the filter to locate others; all claims remain searchable below.'));
 }
 function issuePanel(){
   const issue=$('kr-issue-select').value,role=$('kr-issue-role').value;
   const stats=issueStats(state.rows,issue,role),p=state.issues.find(x=>x.provision_id===issue);
   const box=empty('kr-issue-summary'),hdr=el('div','');
   hdr.append(el('h3','',issueName(issue)),el('p','kr-muted',n(stats.filings)+' distinct filings · '+n(stats.claims)+' claim rows. One filing may have several different views.'));
   if(ISSUE_UNSAFE.has(issue)){
     hdr.append(el('p','kr-notice','Support/oppose totals withheld: the Kaggle model is known to have reversed the direction of some “sunset E-Rate” claims. Requested actions and source evidence remain browseable below.'));
   }else{
     hdr.append(el('p','kr-muted','Machine-coded stances are provisional and not human-validated; mixed positions should be read in context.'));
     const by=new Map();for(const r of stats.rows){
       if(!by.has(r.position))by.set(r.position,new Set());by.get(r.position).add(r.id);
     }
     const counts=el('div','kr-bars');bars(counts,[...by].map(([k,v])=>[k,v.size]),9);hdr.append(counts);
   }
   box.append(hdr);
   bars($('kr-issue-reasons'),fromCounts(stats.reasons).map(([k,v])=>[k,v]),12);
   const actionBox=empty('kr-issue-actions');
   if(!stats.actions.length)actionBox.append(el('p','kr-muted','No grounded requested actions extracted.'));
   for(const action of stats.actions.slice(0,12)){const p=el('p','');p.append(el('strong','',n(action.value)+' filings: '),document.createTextNode(action.label));actionBox.append(p);}
   const evidence=empty('kr-issue-evidence');evidence.append(el('h3','','Inspect arguments and disagreements'));
   evidence.append(ledgerLink('Browse every claim about '+issueName(issue),{'kr-ledger-issue':issue,'kr-ledger-q':''}));
   const picked=unique(stats.rows.map(r=>r.id)).slice(0,6);
   for(const id of picked){const r=stats.rows.find(v=>v.id===id);evidence.append(strongQuote(r));}
   if(stats.rows.length>picked.length)evidence.append(el('p','kr-muted','Source cards above are examples, not the denominator. Use the full ledger for all '+n(stats.claims)+' issue claims.'));
 }
 function questionPanel(){
   const q=$('kr-question').value.trim(),area=empty('kr-answer');
   if(!q){writeCount('kr-answer-status','Enter a substantive question.');return;}
   const result=searchAll(state.rows,q);state.queryResult=result;
   const matches=result.matched;writeCount('kr-answer-status',
     'Evaluated all '+n(result.rowsSearched)+' Kaggle claims; found '+n(matches.length)+' concept/term matches across '+n(result.filings)+' filings. This is a retrieval view, not a verified semantic census or a new LLM answer.');
   if(!matches.length){area.append(el('p','kr-notice','No Kaggle claim matched this wording. This does not prove the argument is absent. Search all original documents, or broaden the question.'));area.append(link('Search the entire source corpus ↗','./ask.html?q='+encodeURIComponent(q)));return;}
   const overview=el('div','kr-panel');overview.append(el('h3','','Question-specific evidence map'));
   overview.append(el('p','',n(matches.length)+' potentially related machine-extracted claims · '+n(result.filings)+' distinct source filings. Every claim was checked for query-term/concept matches. These are retrieval matches, not endorsers or verified positions.'));
   const specs=el('div','');
   for(const c of result.queryConcepts)specs.append(pill(c));
   for(const t of result.freeTerms.slice(0,12))specs.append(pill(t));
   overview.append(specs);
   const reasons=Object.entries(result.reasonCounts).sort((a,b)=>b[1]-a[1]);
   overview.append(el('h4','','Common model-coded reasoning among matching claims'));
   const chart=el('div','kr-bars');bars(chart,reasons,8);overview.append(chart);
   const actions=new Map(),roles=new Map(),issues=new Map();
   for(const r of matches){
     if(r.action){if(!actions.has(r.action))actions.set(r.action,new Set());actions.get(r.action).add(r.id);}
     if(!roles.has(r.role))roles.set(r.role,new Set());roles.get(r.role).add(r.id);
     if(!issues.has(r.issue))issues.set(r.issue,new Set());issues.get(r.issue).add(r.id);
   }
   const comparisons=el('div','kr-split');
   const left=el('div','kr-panel');left.append(el('h3','','Requested policy actions'));
   for(const [action,ids] of [...actions].sort((a,b)=>b[1].size-a[1].size).slice(0,10))
     left.append(el('p','',n(ids.size)+' filings · '+action));
   const right=el('div','kr-panel');right.append(el('h3','','Who raised related arguments?'));
   const rchart=el('div','kr-bars');bars(rchart,[...roles].map(([k,v])=>[roleName(k),v.size]),10);right.append(rchart);
   comparisons.append(left,right);overview.append(comparisons);
   overview.append(el('p','kr-muted','IMPORTANT: The same filing can discuss opposing policy choices; text/concept matches do not establish endorsement. Especially for E-Rate sunset, verify requested actions against the original source.'));
   const button=el('button','kr-action-button','Browse all '+n(matches.length)+' related claim rows');
   button.onclick=()=>{state.ledgerFocusRows=new Set(matches);for(const id of ['kr-ledger-q','kr-ledger-issue','kr-ledger-reason','kr-ledger-role','kr-ledger-stance','kr-ledger-group','kr-ledger-quality'])$(id).value='';state.ledgerPage=0;updateLedgerFilters();$('ledger').scrollIntoView({behavior:'smooth'});};
   overview.append(button,document.createTextNode(' '),link('Also search ALL original filing texts ↗','./ask.html?q='+encodeURIComponent(q)));
   area.append(overview);
   const title=el('h3','','Evidence examples from the complete candidate set');area.append(title);
   const seen=new Set();
   for(const item of result.ranked){
     if(seen.has(item.row.id))continue;
     seen.add(item.row.id);
     area.append(strongQuote(item.row));
     if(seen.size>=12)break;
   }
   area.append(el('p','kr-muted','Displayed evidence examples are limited for readability; counts and comparisons used ALL '+n(matches.length)+' matched claim rows. All rows remain accessible in the full ledger. This is not an AI-generated definitive answer.'));
 }
 function auditControls(){
   try{state.auditState=getAuditState()}catch(_){}
   const reasons=unique(state.audit.flatMap(a=>a.review_reasons||[])).sort();
   for(const x of reasons)option($('kr-audit-reason'),x,friendly(x));
   $('kr-audit-reason').onchange=()=>{state.auditPage=0;renderAudit();};
   $('kr-audit-status').onchange=()=>{state.auditPage=0;renderAudit();};
   $('kr-audit-prev').onclick=()=>{state.auditPage--;renderAudit();};
   $('kr-audit-next').onclick=()=>{state.auditPage++;renderAudit();};
   $('kr-audit-export').onclick=()=>{
     const fields=['submission_id','decision','reviewer_note','risk_reasons','fcc_url'];
     const recs=state.audit.map(a=>({submission_id:a.submission_id,
       decision:state.auditState[a.submission_id]?.decision||'unreviewed',
       reviewer_note:state.auditState[a.submission_id]?.note||'',
       risk_reasons:(a.review_reasons||[]).join('; '),fcc_url:fcc(a.submission_id)}));
     download('kaggle_fcc_review_decisions.csv',safeCsv(fields,recs));
   };
   renderAudit();
 }
 function renderAudit(){
   const reason=$('kr-audit-reason').value,filter=$('kr-audit-status').value;
   state.auditFiltered=state.audit.filter(a=>(!reason||a.review_reasons.includes(reason))&&
     (!filter||(state.auditState[a.submission_id]?.decision||'unreviewed')===filter));
   const per=12,pages=Math.max(1,Math.ceil(state.auditFiltered.length/per));state.auditPage=Math.min(state.auditPage,pages-1);
   const list=empty('kr-audit-list');
   for(const a of state.auditFiltered.slice(state.auditPage*per,(state.auditPage+1)*per)){
     const row=el('article','kr-evidence');
     row.append(el('h3','',a.submission_id),link('Read original FCC filing ↗',fcc(a.submission_id)),link('Read full extracted text ↗',corpus(a.submission_id)));
     row.append(el('p','kr-muted','Flags: '+(a.review_reasons||[]).map(friendly).join(' · ')+' · '+n(a.claim_count||0)+' machine claims'));
     if(a.sample_quote)row.append(el('blockquote','',a.sample_quote));
     const label=el('label','kr-muted','Reviewer assessment (stored locally on this browser only)');
     const select=el('select');['unreviewed','agree','incorrect','needs_review'].forEach(v=>option(select,v,friendly(v)));
     select.value=state.auditState[a.submission_id]?.decision||'unreviewed';
     select.onchange=()=>{state.auditState[a.submission_id]={...(state.auditState[a.submission_id]||{}),decision:select.value};setAuditState();};
     label.append(select);
     const note=el('textarea','');note.rows=2;note.style.width='100%';note.placeholder='Note evidence errors, incorrect stance interpretation, identity issues…';
     note.value=state.auditState[a.submission_id]?.note||'';
     note.onchange=()=>{state.auditState[a.submission_id]={...(state.auditState[a.submission_id]||{}),note:note.value};setAuditState();};
     row.append(label,note);list.append(row);
   }
   writeCount('kr-audit-count',state.auditFiltered.length+' selected of '+state.audit.length+' risk-enriched filing review candidates. This is not a randomized accuracy sample.');
   writeCount('kr-audit-page','Page '+(state.auditPage+1)+' of '+pages);
   $('kr-audit-prev').disabled=state.auditPage===0;$('kr-audit-next').disabled=state.auditPage===pages-1;
 }
 function renderFilingProfile(){
   const id=$('kr-filing-id').value.trim();
   const area=empty('kr-filing-profile'),record=state.meta.get(id);
   if(!/^\d+$/.test(id)||!record){
     writeCount('kr-filing-status','Filing ID not found in this 3,231-record research snapshot. Enter an original ECFS submission ID.');
     return;
   }
   const records=state.rows.filter(r=>String(r.id)===id),quality=state.quality?.filings?.[id],issues=new Map(),groups=new Map(),reasons={};
   writeCount('kr-filing-status',n(records.length)+' Kaggle source-linked claims found for '+id+'; full original record available.');
   for(const r of records){
     if(!issues.has(r.issue))issues.set(r.issue,[]);issues.get(r.issue).push(r);
     if(!groups.has(r.group))groups.set(r.group,0);groups.set(r.group,groups.get(r.group)+1);
     reasons[r.reason_family]=(reasons[r.reason_family]||0)+1;
   }
   const title=el('div','kr-panel');
   title.append(el('p','kr-eyebrow','Individual commenter profile'),el('h3','',record.organization||'Filing '+id));
   title.append(el('p','kr-muted','Filing '+id+' · '+(record.date||'Date unavailable')+' · '+
     roleName(records[0]?.role||record.role)+' · '+(record.ocr?'OCR candidate · ':'')+
     'Original source length '+n(record.chars)+' characters'));
   const links=el('p','');links.append(link('Read original FCC record ↗',fcc(id)),link(' Read full extracted comment ↗',corpus(id)),
     link(' View complete GPT-OSS extraction JSON ↗','https://github.com/shreyammm/e-rate/blob/main/data/llm_census_kaggle/filings/'+encodeURIComponent(id)+'.json'));
   title.append(links);
   if(quality){
     title.append(el('p','kr-muted','Semantic model coverage: '+friendly(quality.semantic_scope)+' · '+
       n(quality.source_windows_model_analyzed)+' of '+n(quality.source_windows_available)+
       ' original source windows read by GPT-OSS.'));
     for(const flag of quality.known_interpretation_risks||[])title.append(pill(friendly(flag),true));
   }
   const nums=el('div','kr-kpis');
   [[records.length,'Model claim records'],[issues.size,'Issue labels'],[groups.size,'Exploratory claim groups'],
    [record.duplicate_count||1,'Exact-text filing instances']].forEach(([v,t])=>nums.append(stat(v,t)));
   title.append(nums);
   if(records.some(stanceRisk))title.append(el('p','kr-notice','Some machine stance labels about sunsetting E-Rate are known to be reversed. Inspect requested actions and source quotations, not the support/oppose field.'));
   if(!records.length)title.append(el('p','kr-notice','No grounded claim was extracted for this filing. That is not evidence of a neutral position, agreement, or lack of arguments. Read the original full comment.'));
   area.append(title);
   if(records.length){
     const reasonsArea=el('div','kr-panel');reasonsArea.append(el('h3','','How the model categorized its reasoning'));
     const chart=el('div','kr-bars');bars(chart,fromCounts(reasons),12);reasonsArea.append(chart);area.append(reasonsArea);
     const issueArea=el('div','kr-panel');issueArea.append(el('h3','','Requested policy outcomes by issue'));
     for(const [issue,rs] of [...issues].sort((a,b)=>b[1].length-a[1].length)){
       const item=el('article','kr-evidence');item.append(el('h4','',issueName(issue)+' · '+rs.length+' machine claims'));
       const seen=new Set();
       for(const r of rs){if(!r.action||seen.has(r.action))continue;seen.add(r.action);
         item.append(el('p','',r.action+(stanceRisk(r)?' · sunset direction requires audit':'')));}
       const btn=el('button','kr-action-button','Inspect this issue across the corpus');
       btn.onclick=()=>{$('kr-issue-select').value=issue;$('kr-issue-role').value='';issuePanel();$('issues').scrollIntoView({behavior:'smooth'});};
       item.append(btn);issueArea.append(item);
     }
     area.append(issueArea);
     const all=el('div','kr-panel');all.append(el('h3','','Every extracted argument and source quotation'));
     for(const r of records)all.append(strongQuote(r));
     area.append(all);
     const peerGroups=new Set(groups.keys()),peers=new Map();
     for(const r of state.rows){
       if(r.id===id||!peerGroups.has(r.group))continue;
       if(!peers.has(r.id))peers.set(r.id,new Set());
       peers.get(r.id).add(r.group);
     }
     const nearest=[...peers].sort((a,b)=>b[1].size-a[1].size).slice(0,12);
     const similar=el('div','kr-panel');similar.append(el('h3','','Related claim families from other filings'));
     similar.append(el('p','kr-muted','Automatically related by shared exploratory machine-cluster memberships, not verified semantic agreement or identical policy positions.'));
     for(const [other,inter] of nearest){
       const info=state.meta.get(String(other)),line=el('p','');
       line.append(el('strong','',n(inter.size)+' shared claim groups · '),link(info?.organization||'FCC filing '+other,fcc(other)),el('span','kr-muted',' · '+other));
       similar.append(line);
     }
     area.append(similar);
   }
   const url=new URL(location.href);url.searchParams.set('id',id);
   if(window.history?.replaceState)history.replaceState(null,'',url.toString());
 }

 function qaSelection(){
   if(!state.quality?.filings)return [];
   const category=$('kr-qa-kind').value,term=$('kr-qa-query').value.trim().toLowerCase();
   return Object.values(state.quality.filings).filter(f=>{
     const valid=category==='all'||(category==='prioritized'&&f.semantic_scope!=='full_text')||
       (category==='no_claims'&&f.number_claims===0)||
       (category==='sunset'&&f.suspected_sunset_polarity_claim_indices?.length>0)||
       (category==='ocr'&&f.ocr_candidate);
     return valid&&(!term||(f.filer+' '+f.filing_id).toLowerCase().includes(term));
   }).sort((a,b)=>a.filing_id.localeCompare(b.filing_id));
 }
 function qaDisplay(){
   if(!state.quality?.filings)return;
   const selected=qaSelection(),per=25,pages=Math.max(1,Math.ceil(selected.length/per));
   state.qaPage=Math.min(state.qaPage||0,pages-1);
   writeCount('kr-qa-count',n(selected.length)+' source-linked Kaggle filings with this diagnostic; only 25 preview cards per page.');
   writeCount('kr-qa-page','Page '+(state.qaPage+1)+' of '+pages);
   const root=empty('kr-qa-results');
   for(const f of selected.slice(state.qaPage*per,(state.qaPage+1)*per)){
     const card=el('article','kr-evidence');
     card.append(link(f.filer||'FCC filing '+f.filing_id,f.original_source_url),
        el('p','kr-muted','Filing '+f.filing_id+' · '+roleName(f.verified_role_crosswalk)+
         ' · '+n(f.number_claims)+' model claims · '+n(f.source_windows_model_analyzed)+' / '+
         n(f.source_windows_available)+' text windows read.'));
     for(const flag of f.known_interpretation_risks||[])card.append(pill(friendly(flag),true));
     const profile=el('button','kr-action-button','View detailed filing profile');
     profile.onclick=()=>{$('kr-filing-id').value=f.filing_id;renderFilingProfile();$('filing').scrollIntoView({behavior:'smooth'});};
     card.append(profile,document.createTextNode(' '),link('Model JSON ↗',f.model_output_url));
     root.append(card);
   }
   $('kr-qa-prev').disabled=state.qaPage===0;
   $('kr-qa-next').disabled=state.qaPage===pages-1;
 }
 function initQualityExplorer(){
   for(const id of ['kr-qa-kind','kr-qa-query'])$(id).addEventListener(id==='kr-qa-query'?'input':'change',()=>{state.qaPage=0;qaDisplay();});
   $('kr-qa-prev').onclick=()=>{state.qaPage--;qaDisplay();};
   $('kr-qa-next').onclick=()=>{state.qaPage++;qaDisplay();};
   $('kr-qa-export').onclick=()=>{
     const records=qaSelection().map(f=>({
       filing_id:f.filing_id,filer:f.filer,semantic_scope:f.semantic_scope,
       model_read_windows:f.source_windows_model_analyzed,total_windows:f.source_windows_available,
       claims:f.number_claims,ocr_candidate:f.ocr_candidate,review_flags:f.known_interpretation_risks.join(';'),
       fcc_url:f.original_source_url
     }));
     download('kaggle_all_flagged_filings.csv',safeCsv(
       ['filing_id','filer','semantic_scope','model_read_windows','total_windows','claims','ocr_candidate','review_flags','fcc_url'],records));
   };
   qaDisplay();
 }
 function setupInputs(){
   for(const p of state.issues){
     option($('kr-issue-select'),p.provision_id,p.label);
     for(const id of ['kr-ledger-issue','kr-org-issue','kr-cluster-issue'])option($(id),p.provision_id,p.label);
   }
   if(state.issues.some(p=>p.provision_id==='screen_time_condition'))$('kr-issue-select').value='screen_time_condition';
   const reasons=unique(state.rows.map(r=>r.reason_family).filter(Boolean)).sort();
   const roles=unique(state.rows.map(r=>r.role).filter(Boolean)).sort();
   const stance=unique(state.rows.map(r=>r.position).filter(Boolean)).sort();
   for(const x of roles){option($('kr-ledger-role'),x,roleName(x));option($('kr-issue-role'),x,roleName(x));}
   for(const x of reasons)option($('kr-ledger-reason'),x,friendly(x));
   for(const x of stance)option($('kr-ledger-stance'),x,friendly(x)+' (unvalidated)');
   for(const g of state.landscape.clusters)option($('kr-ledger-group'),g.id,g.id+' · '+g.working_label);
   for(const id of ['kr-ledger-q','kr-ledger-issue','kr-ledger-reason','kr-ledger-role','kr-ledger-stance','kr-ledger-group','kr-ledger-quality','kr-ledger-sort'])
     $(id).addEventListener(id==='kr-ledger-q'?'input':'change',()=>{state.ledgerPage=0;updateLedgerFilters();});
   for(const id of ['kr-cluster-query','kr-cluster-issue','kr-cluster-sort'])
     $(id).addEventListener(id==='kr-cluster-query'?'input':'change',renderClusters);
   for(const id of ['kr-org-query','kr-org-issue','kr-person-group'])
     $(id).addEventListener(id==='kr-org-query'?'input':'change',groupPeople);
   $('kr-issue-select').onchange=issuePanel;$('kr-issue-role').onchange=issuePanel;
   $('kr-prev').onclick=()=>{state.ledgerPage--;showLedger();};
   $('kr-next').onclick=()=>{state.ledgerPage++;showLedger();};
   $('kr-ledger-clear').onclick=()=>{
     state.ledgerFocusRows=null;
     for(const id of ['kr-ledger-q','kr-ledger-issue','kr-ledger-reason','kr-ledger-role','kr-ledger-stance','kr-ledger-group','kr-ledger-quality'])
       $(id).value='';$('kr-ledger-sort').value='id';state.ledgerPage=0;updateLedgerFilters();
   };
   $('kr-ledger-csv').onclick=()=>{
     const cols=['id','organization','role','issue','position','reason_family','claim_kind','action','argument','quote','source_url','start','ocr_candidate','group'];
     download('kaggle_fcc_filtered_claims.csv',safeCsv(cols,state.ledgerFiltered));
   };
   $('kr-ask').onclick=questionPanel;
   $('kr-filing-open').onclick=renderFilingProfile;
   $('kr-filing-id').addEventListener('keydown',e=>{if(e.key==='Enter')renderFilingProfile();});
   $('kr-question').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();questionPanel();}});
   document.querySelectorAll('[data-kq]').forEach(x=>{x.onclick=()=>{$('kr-question').value=x.dataset.kq;questionPanel();};});
   const fid=new URLSearchParams(location.search).get('id');
   if(fid&&/^\d+$/.test(fid)){$('kr-filing-id').value=fid;renderFilingProfile();}
   const qp=new URLSearchParams(location.search).get('q');
   if(qp&&qp.length<2000){$('kr-question').value=qp;questionPanel();}
 }
 async function load(){
   try{
     const resources=[
       ['./data/kaggle/machine_claim_rows.json','claims'],
       ['./data/kaggle/claim_landscape.json','landscape'],
       ['./data/llm_kaggle_exploratory.json','summary'],
       ['./data/corpus_index.json','meta'],
       ['./data/llm_kaggle_audit_queue.json','audit']
     ];
     const results=await Promise.all(resources.map(async([url])=>{
       const response=await fetch(url,{cache:'default'});if(!response.ok)throw Error(url+' returned HTTP '+response.status);
       return response.json();
     }));
     const [claims,landscape,summary,meta,audit]=results;
     if(claims.publication_status!=='EXPLORATORY_MODEL_ONLY'||!Array.isArray(claims.rows)||
        claims.rows.length!==landscape.coverage.machine_claim_rows||
        landscape.coverage.completed_machine_filings!==3230||
        summary.completed_filings!==3230||
        !Array.isArray(meta.filings)||meta.filings.length!==3231)
       throw Error('Kaggle publication manifest mismatch; refusing incomplete findings');
     state.rows=claims.rows;state.landscape=landscape;state.summary=summary;
     state.meta=new Map(meta.filings.map(f=>[String(f.id),f]));state.issues=summary.provisions||[];
     state.audit=Array.isArray(audit.items)?audit.items:[];
     try{const qr=await fetch('./data/kaggle/filing_quality.json',{cache:'default'});if(qr.ok){const q=await qr.json();if(q.version==='kaggle-filing-quality-v1'&&Object.keys(q.filings||{}).length===3230)state.quality=q;}}catch(_){/* optional quality diagnostics do not disable the claim explorer */}
     // The row dataset provides organization text from source metadata;
     // do not replace affiliation-less people with inferred organizations.
     initStats();setupInputs();renderClusters();issueConnections();groupPeople();issuePanel();updateLedgerFilters();auditControls();
     if(state.quality)initQualityExplorer();else writeCount('kr-qa-count','Per-filing diagnostics are being regenerated; the other Kaggle evidence and audit features remain available.');
     setStatus('Loaded and checked '+n(state.rows.length)+' Kaggle claim rows across all '+n(summary.completed_filings)+' readable filings. The full evidence ledger is queryable below.');
   }catch(e){
     setStatus('Kaggle evidence failed to load or validate: '+e.message+'. No incomplete counts are being shown as complete.',true);
   }
 }
 load();
})(typeof window!=='undefined'?window:typeof globalThis!=='undefined'?globalThis:{});
