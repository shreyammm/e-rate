'use strict';
// Integration coverage test: real 12-shard FCC source archive, mock inference.
// Asserts the entire original snapshot can pass through the exhaustive path.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const zlib=require('node:zlib');
const readline=require('node:readline');
const api=require('../docs/assets/ask_exhaustive.js');
const ROOT=path.join(__dirname,'..');
const meta=JSON.parse(fs.readFileSync(path.join(ROOT,'docs/data/qa_index/manifest.json'),'utf8'));
let modelPasses=0;
const model={chat:{completions:{create:async({messages})=>{
  assert.ok(messages[1].content.includes('Exact source body characters'));
  modelPasses++;
  return {choices:[{message:{content:'{"relevant":false,"claims":[]}'}}]};
}}}};
async function streamShard(name,visit){
  const filename=path.join(ROOT,'data/fcc_corpus/shards',name);
  assert.ok(fs.existsSync(filename),'Missing original shard '+name);
  const input=fs.createReadStream(filename).pipe(zlib.createGunzip());
  const lines=readline.createInterface({input,crlfDelay:Infinity});
  for await(const line of lines)if(line.trim())await visit(JSON.parse(line));
}
test('EVERY full-text window of ALL original FCC filings is analyzed',async()=>{
  const result=await api.run({question:'Describe every FCC argument about the E-Rate program',
    meta,streamShard,engine:model,store:api.inMemoryStore()});
  assert.equal(result.scanned,3231);
  assert.equal(result.analyzedFilings,3230);
  assert.equal(result.ledger.length,result.sourceWindows);
  assert.equal(modelPasses,result.sourceWindows);
  assert.equal(new Set(result.ledger.map(x=>x.id)).size,3230);
  assert.ok(result.sourceWindows>3230,'long filings must be examined in multiple full-text windows');
  assert.equal(result.claims,0,'the mock model intentionally extracts no semantic claims');
});
