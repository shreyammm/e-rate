'use strict';
// Node-native integration test against the full published ECFS source snapshot.
// Confirms every shard is consulted for each question; the browser UI may
// display only a bounded evidence selection, but retrieval does not stop early.
const assert=require('node:assert/strict');
const test=require('node:test');
const fs=require('node:fs');
const path=require('node:path');
const {Readable}=require('node:stream');
const api=require('../docs/assets/ask.js');
const ROOT=path.resolve(__dirname,'..');
const DATA=path.join(ROOT,'data','fcc_corpus','shards');
const INDEX=path.join(ROOT,'docs','data','qa_index','manifest.json');
const meta=JSON.parse(fs.readFileSync(INDEX,'utf8'));
function wireSource(base=DATA) {
 let loaded=[];
 global.fetch=async url=>{
   const name=decodeURIComponent(String(url).split('/').pop());
   loaded.push(name);
   const full=path.resolve(base,name);
   if(!full.startsWith(path.resolve(base)+path.sep))return new Response('Unexpected path',{status:400});
   if(!fs.existsSync(full))return new Response('Missing source shard',{status:404});
   return new Response(Readable.toWeb(fs.createReadStream(full)),{status:200});
 };
 return loaded;
}
test('a funding-screen-time question reads every filing and retrieves affirmative examples',async()=>{
 api.setTestMeta(meta);
 const reads=wireSource();
 const result=await api.fullScan('What commenters support reducing E-Rate funding due to screen time concerns?');
 assert.equal(result.scanned,3231);
 assert.equal(result.withText,3230);
 assert.equal(result.shards,12);
 assert.equal(reads.length,12);
 assert.equal(new Set(reads).size,12);
 const evidence=api.chooseEvidence(result);
 for(const id of ['26110080198','26110079250']){
   assert.ok(result.candidates.some(r=>r.id===id),id+' must be found among all filings');
   assert.ok(evidence.some(r=>r.id===id),id+' must appear among diverse evidence');
 }
 assert.ok(evidence.every(r=>r.quote&&r.quote.length>100));
});
test('a missing shard refuses a partial full-corpus search',async()=>{
 const tmp=require('node:fs').mkdtempSync(path.join(require('node:os').tmpdir(),'erate-shards-'));
 try{
   const docs=Array.from({length:12},(_,i)=>({
     id:String(10000000000+i),shard:'filings-'+String(i+1).padStart(4,'0')+'.jsonl.gz',
     has_text:true,filer:'Synthetic '+i,date:'2026-10-20'
   }));
   api.setTestMeta({docs,records:12,with_text:12});
   const zlib=require('node:zlib');
   for(let i=0;i<12;i++){
     if(i===6)continue; // One missing source invalidates the entire run.
     const d=docs[i];
     const payload=JSON.stringify({submission_id:d.id,text:'E-Rate screen time funding restrictions',filer_raw:d.filer})+'\n';
     fs.writeFileSync(path.join(tmp,d.shard),zlib.gzipSync(payload));
   }
   wireSource(tmp);
   await assert.rejects(()=>api.fullScan('Should E-Rate funding be conditioned on screen time limits?'),
     /Full corpus search failed to load|Incomplete source shard/);
 }finally{fs.rmSync(tmp,{recursive:true,force:true});api.setTestMeta(meta);}
});
