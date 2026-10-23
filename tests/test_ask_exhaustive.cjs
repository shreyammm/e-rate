'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const api=require('../docs/assets/ask_exhaustive.js');
const long='Opening segment. '+('Long supporting argument about school networks. '.repeat(260))+
  ' Critical final conclusion: preserve E-Rate access for remote communities.';
const rows={
  'one':[ {submission_id:'1001',filer_raw:'Regional school district',text:long},
    {submission_id:'1002',filer_raw:'Advocacy group',text:'E-Rate funding must remain available to rural libraries.'}],
  'two':[ {submission_id:'1003',filer_raw:'ECFS link-only record',text:''}]
};
const manifest={records:3,with_text:2,corpus_source_sha256:'test-snapshot-v1',docs:[
  {id:'1001',shard:'one',has_text:true,length:long.length},
  {id:'1002',shard:'one',has_text:true,length:rows.one[1].text.length},
  {id:'1003',shard:'two',has_text:false,length:0}]};
function stream(shard,visit){return (async()=>{for(const r of rows[shard])await visit(r);})();}
function model(visits,reportClaims=false){
  return {chat:{completions:{create:async({messages})=>{
    const prompt=messages[1].content;
    if(prompt.includes('Exact source body characters')){
      visits.push(prompt);
      const quote='E-Rate funding must remain available to rural libraries.';
      if(reportClaims&&prompt.includes(quote))
        return {choices:[{message:{content:JSON.stringify({relevant:true,claims:[
          {quote,argument:'Keep E-Rate connectivity for rural libraries.',position:'support',
           reason:'Small rural libraries rely on the program.',requested_action:'Preserve eligibility'}]})}}]};
      return {choices:[{message:{content:'{"relevant":false,"claims":[]}'}}]};
    }
    return {choices:[{message:{content:'Filings discuss rural library eligibility [FCC:1002].'}}]};
  }}}};
}
test('EVERY readable source character reaches model, even without lexical matches',async()=>{
  const visits=[],store=api.inMemoryStore();
  const result=await api.run({question:'Comprehensively analyze the full record',meta:manifest,
    streamShard:stream,engine:model(visits),store});
  assert.equal(result.scanned,3);
  assert.equal(result.analyzedFilings,2);
  assert.equal(result.sourceWindows,visits.length);
  assert.ok(visits.length>3,'long comments require multiple full-text windows');
  const overlaps=visits.filter(x=>x.includes('ECFS filing: 1001'));
  const ranges=overlaps.map(x=>/characters (\d+) through (\d+):\n/.exec(x)).map(m=>[Number(m[1]),Number(m[2])]);
  assert.equal(ranges[0][0],0);
  assert.equal(ranges[ranges.length-1][1],long.length);
  for(let i=1;i<ranges.length;i++)assert.ok(ranges[i][0]<=ranges[i-1][1],'no source gap');
  assert.ok(visits.some(x=>x.includes('Critical final conclusion: preserve E-Rate')),'tail of long filing must be read');
  const resumed=[];
  const repeat=await api.run({question:'Comprehensively analyze the full record',meta:manifest,
    streamShard:stream,engine:model(resumed),store});
  assert.equal(resumed.length,0,'successful identical query windows load from checkpoints');
  assert.equal(repeat.cachedWindows,visits.length);
});
test('grounded synthesis uses claims extracted from any original filing, not ranked lexical excerpts',async()=>{
  const visits=[];
  const result=await api.run({question:'What do stakeholders think of rural library service?',meta:manifest,
    streamShard:stream,engine:model(visits,true),store:api.inMemoryStore()});
  assert.ok(result.claims>=1);
  assert.ok(result.cited.includes('1002'));
  assert.ok(result.answer.includes('[FCC:1002]'));
  const source=result.ledger.flatMap(v=>v.claims).find(v=>v.quote.includes('rural libraries'));
  assert.equal(source.evidence_start,0);
});
test('invalid original quotations are rejected rather than accepted as source claims',()=>{
  assert.throws(()=>api.validatePass({relevant:true,claims:[{
    quote:'This quotation does not exist in the source body',
    argument:'Fake argument'}]}, {start:0,text:'Another, unrelated sentence.'}),/Unverified/);
});
test('incomplete original shard aborts the run with no synthesized result',async()=>{
  await assert.rejects(()=>api.run({question:'Find every claim',meta:manifest,
    streamShard:async(s,visit)=>{if(s==='one')await visit(rows.one[0]);},
    engine:model([]),store:api.inMemoryStore()}),/Incomplete source shard/);
});
test('source-window cancel halts research and prevents a premature answer',async()=>{
  let cancelled=false;
  const partial=[];
  await assert.rejects(()=>api.run({question:'Every position?',meta:manifest,streamShard:stream,
    engine:model(partial),store:api.inMemoryStore(),cancelled:()=>cancelled,
    onProgress:x=>{if(x.phase==='source')cancelled=true;}}),/Cancelled/);
  assert.equal(partial.length,1);
});
