'use strict';
const assert=require('node:assert/strict');
const test=require('node:test');
const {run, citations, validSummary}=require('../docs/assets/ask_full_synthesis.js');
const items=Array.from({length:17},(_,i)=>{
  const id=String(26110070000+i);
  return {id,filer:'Filer '+i,passages:[{quote:'Comment '+id+' asks the FCC to clarify its E-Rate eligibility rule and reasons.'}]};
});
test('exhaustive synthesis submits every lexical candidate for model review, not just 12',async()=>{
  const submitted=new Set();
  let calls=0;
  const model={chat:{completions:{create:async({messages})=>{
    calls++;
    const prompt=messages[1].content;
    if(prompt.includes('Read ALL the following filing passages.')){
      for(const [,id] of prompt.matchAll(/\[FCC:(\d+)\]/g))submitted.add(id);
      const id=prompt.match(/\[FCC:(\d+)\]/)[1];
      return {choices:[{message:{content:'E-Rate policy argument '+('[FCC:'+id+']')}}]};
    }
    const id=prompt.match(/\[FCC:(\d+)\]/)?.[1]||items[0].id;
    return {choices:[{message:{content:'Synthesis with original filing evidence [FCC:'+id+']'}}]};
  }}}};
  const progress=[];
  const result=await run({question:'What arguments were raised about E-Rate?',candidates:items,engine:model,onProgress:x=>progress.push(x)});
  assert.equal(result.processed,17);
  assert.equal(result.allRetrieved,17);
  assert.equal(submitted.size,17);
  assert.equal(result.sourceIds.length,17);
  assert.ok(calls>5,'map and reduce must execute');
  assert.ok(progress.some(x=>x.phase==='merge'));
  assert.ok(result.citations.every(id=>result.sourceIds.includes(id)));
});
test('bad model citations never enter the synthesis tree',async()=>{
  const model={chat:{completions:{create:async()=>({choices:[{message:{content:'Unsupported [FCC:99999999]'}}]})}}};
  const result=await run({question:'Explain the filing',candidates:items.slice(0,1),engine:model});
  assert.ok(result.answer.includes('[FCC:'+items[0].id+']'));
  assert.ok(!result.answer.includes('99999999'));
});
test('cancelling halts additional model passes',async()=>{
  let stopped=false;
  const model={chat:{completions:{create:async({messages})=>{
    const id=messages[1].content.match(/\[FCC:(\d+)\]/)[1];
    return {choices:[{message:{content:'Supported [FCC:'+id+']'}}]};
  }}}};
  await assert.rejects(()=>run({question:'Test',candidates:items,engine:model,
    cancelled:()=>stopped,onProgress:p=>{if(p.phase==='read'&&p.done>=4)stopped=true;}}),
    /cancelled/);
});
test('citation validator checks IDs',()=>{
  assert.ok(validSummary('Document says X [FCC:123]',new Set(['123'])));
  assert.equal(validSummary('Document says X [FCC:124]',new Set(['123'])),false);
  assert.deepEqual(citations('See [FCC:123] and [FCC:456]'),['123','456']);
});
