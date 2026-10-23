'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const lib=require('../docs/assets/kaggle_research.js');
const read=p=>JSON.parse(fs.readFileSync(path.join(__dirname,'..',p),'utf8'));
const rows=read('docs/data/kaggle/machine_claim_rows.json').rows;
const landscape=read('docs/data/kaggle/claim_landscape.json');
const kaggle=read('docs/data/llm_kaggle_exploratory.json');
test('Kaggle Studio consumes every imported claim, not a displayed subset',()=>{
 assert.equal(kaggle.completed_filings,3230);
 assert.equal(rows.length,14835);
 assert.equal(rows.length,landscape.coverage.machine_claim_rows);
 assert.equal(landscape.coverage.full_source_quote_offset_verified,rows.length);
 assert.equal(landscape.clusters.length,42);
});
test('known E-Rate-sunset polarity reversals must be quarantined',()=>{
 const example=rows.find(r=>r.id==='26110076906'&&r.issue==='erate_sunset');
 assert.ok(example,'known library filing must remain visible');
 assert.equal(example.position,'support');
 assert.match(example.action,/continu(e|ation)|maintain|preserv/i);
 assert.equal(lib.stanceRisk(example),true);
 assert.equal(lib.riskLabel(example),'Polarity not validated');
 assert.equal(lib.stanceRisk({...example,issue:'cipa_byod'}),false);
});
test('question analysis examines all claim rows and does not silently keep top 12',()=>{
 const mock=Array.from({length:57},(_,i)=>({
  id:String(100000+i),issue:'erate_eligibility_scope',role:'school_district',
  argument:'Federal aid helps underserved schools connect online',
  action:'Maintain broadband funding',quote:'Community broadband service is important',
  reason_family:'access_affordability_equity',claim_kind:'equity_access'
 }));
 const result=lib.searchAll(mock,'What do comments say about broadband funding for underserved schools?');
 assert.equal(result.rowsSearched,57);
 assert.equal(result.matched.length,57);
 assert.equal(result.filings,57);
});
test('source-derived role comparisons count filings separately from extracted claims',()=>{
 const source=[
  {id:'1',issue:'cipa_byod',role:'library',action:'preserve protection',reason_family:'child_safety'},
  {id:'1',issue:'cipa_byod',role:'library',action:'preserve protection',reason_family:'child_safety'},
  {id:'2',issue:'cipa_byod',role:'school',action:'improve filtering',reason_family:'child_safety'},
  {id:'3',issue:'screen_time_condition',role:'school',action:'limit devices',reason_family:'child_safety'},
 ];
 const p=lib.issueStats(source,'cipa_byod');
 assert.equal(p.claims,3);assert.equal(p.filings,2);
 assert.equal(p.roles.find(x=>x.label==='library').value,1);
 assert.equal(p.actions.find(x=>x.label==='preserve protection').value,1);
});
test('CSV protects spreadsheet formula injection',()=>{
 const out=lib.safeCsv(['argument','id'],[{argument:'=HYPERLINK("evil")',id:'12'}]);
 assert.ok(out.includes("'=HYPERLINK"));
});
test('Kaggle Studio has source links, full ledger, audit controls and method warnings',()=>{
 const html=fs.readFileSync(path.join(__dirname,'../docs/kaggle.html'),'utf8');
 for(const term of ['id="questions"','id="arguments"','id="people"','id="issues"','id="ledger"','id="audit"',
                   'id="kr-audit-export"','id="kr-ledger-csv"','./assets/kaggle_research.js',
                   'support and opposition','machine interpretation','not a human-validated survey']){
  // Case-insensitive for prose, exact IDs
  assert.ok(html.toLowerCase().includes(term.toLowerCase()),'missing '+term);
 }
 const audit=read('docs/data/llm_kaggle_audit_queue.json');
 assert.equal(audit.items.length,150);
});
