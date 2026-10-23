'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const lib=require('../docs/assets/kaggle_synthesis.js');
test('every matching Kaggle claim is submitted to model without sample cutoff',async()=>{
 const rows=Array.from({length:33},(_,i)=>({
   id:String(26000000000+i),organization:'School district '+i,
   issue:'screen_time_condition',position:'oppose',reason_family:'child_safety',
   action:'Preserve flexibility for school device policies',
   argument:'One size fits all restrictions can inhibit legitimate instruction.',
   quote:'Avoid blanket daily screen time limits on school devices.',
   start:100+i
 }));
 const seen=new Set(),phases=[];
 let calls=0;
 const model={chat:{completions:{create:async({messages})=>{
   const input=messages[1].content;calls++;
   for(const match of input.matchAll(/Filer: School district (\d+)/g))seen.add(Number(match[1]));
   const id=input.match(/\[FCC:(\d+)\]/)?.[1];
   return {choices:[{message:{content:'Source-grounded comparison [FCC:'+id+']'}}]};
 }}}};
 const result=await lib.run({question:'How do commenters interpret federal screen time mandates?',claims:rows,engine:model,onProgress:p=>phases.push(p.phase)});
 assert.equal(result.processed_claims,33);
 assert.equal(seen.size,33);
 assert.ok(result.analyzed_map_batches>4);
 assert.ok(calls>result.analyzed_map_batches);
 assert.ok(phases.includes('map')&&phases.includes('merge'));
 assert.ok(result.source_ids.length===33);
 assert.ok(result.cited_ids.every(id=>result.source_ids.includes(id)));
});
test('hallucinated citations cannot enter returned Kaggle synthesis',async()=>{
 const model={chat:{completions:{create:async()=>({choices:[{message:{content:'Unsupported interpretation [FCC:99999999]'}}]})}}};
 await assert.rejects(()=>lib.run({question:'What was asked?',claims:[{
    id:'123456',organization:'One filing',issue:'mibs',position:'oppose',
    reason_family:'administrative_burden',action:'Streamline program forms',
    argument:'Too many forms impose burdens',quote:'All applicants submit several forms.'
 }],engine:model}),/citation validation/);
});
test('cancellation halts subsequent LLM work',async()=>{
 let cancelled=false,seen=0;
 const model={chat:{completions:{create:async({messages})=>{
   seen++;
   const id=messages[1].content.match(/\[FCC:(\d+)\]/)[1];
   return {choices:[{message:{content:'Source-linked statement [FCC:'+id+']'}}]};
 }}}};
 await assert.rejects(()=>lib.run({
  question:'What do commenters say?',claims:Array.from({length:9},(_,i)=>({
    id:String(1000+i),argument:'Broadband connectivity matters for schools',quote:'School connection',
    issue:'erate_eligibility_scope',position:'support',reason_family:'access_affordability_equity',action:'Maintain funding'
  })),engine:model,cancelled:()=>cancelled,
  onProgress:p=>{if(p.phase==='map'&&p.done>=1)cancelled=true;}
 }),/cancelled/);
 assert.equal(seen,1);
});
test('source citation verifier never accepts outside FCC IDs',()=>{
 assert.ok(lib.citationsValid('Valid [FCC:123]',new Set(['123'])));
 assert.equal(lib.citationsValid('Invalid [FCC:124]',new Set(['123'])),false);
 assert.equal(lib.citationsValid('No source',new Set(['123'])),false);
});
