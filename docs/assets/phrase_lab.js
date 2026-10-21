"use strict";
(async()=>{
const $=id=>document.getElementById(id),fmt=n=>Number(n||0).toLocaleString('en-US');
const nice=s=>String(s||'Unresolved').replaceAll('_',' ').replace(/\b\w/g,x=>x.toUpperCase());
const mk=(tag,cl,v)=>{const e=document.createElement(tag);if(cl)e.className=cl;if(v!==undefined)e.textContent=String(v);return e};
const link=(title,url)=>{const a=mk('a','',title);a.href=url;a.rel='noopener noreferrer';a.target='_blank';return a};
let meta,lookup=null,results=[],visible=50;
const parse=id=>[...new Set($(id).value.toLowerCase().split('|').map(x=>x.trim()).filter(x=>x.length>=3))].slice(0,20);
const match=(window,terms)=>terms.some(x=>window.includes(x));
const url=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(id);
function inspect(text,A,B){
  const width=1500,stride=750;
  let hasA=false,hasB=false,near=false,excerpt='',anyWindow='';
  // Treat each document exactly once; overlap reduces boundary sensitivity.
  // Full content is inspected, including long filings, never only the opening pages.
  for(let start=0;start<text.length;start+=stride){
    const snippet=text.slice(start,Math.min(start+width,text.length)),lower=snippet.toLowerCase();
    const a=match(lower,A),b=match(lower,B);
    hasA ||= a;hasB ||= b;
    if((a||b)&&!anyWindow)anyWindow=snippet;
    if(a&&b&&!near){near=true;excerpt=snippet;}
    if(start+width>=text.length)break;
  }
  return {hasA,hasB,near,excerpt:excerpt||anyWindow};
}
async function scanShard(name,visit){
  const r=await fetch('./data/full_text_shards/'+encodeURIComponent(name),{cache:'force-cache'});
  if(!r.ok||!r.body)throw Error('Source shard '+name+' unavailable ('+r.status+')');
  const reader=r.body.getReader(),first=await reader.read();
  if(first.done)throw Error('Empty source shard '+name);
  const src=new ReadableStream({
    start(c){c.enqueue(first.value);},
    async pull(c){const p=await reader.read();if(p.done)c.close();else c.enqueue(p.value)},
    cancel(x){reader.cancel(x)}
  });
  const gzip=first.value[0]===31&&first.value[1]===139;
  if(gzip&&typeof DecompressionStream!=='function')throw Error('Browser does not support gzip streaming');
  const decoded=(gzip?src.pipeThrough(new DecompressionStream('gzip')):src).getReader(),decoder=new TextDecoder();
  let buffer='',n=0;
  const consume=line=>{if(line.trim()){visit(JSON.parse(line));n++}};
  for(;;){
    const next=await decoded.read();if(next.done)break;
    buffer+=decoder.decode(next.value,{stream:true});
    let ix;while((ix=buffer.indexOf('\n'))>=0){consume(buffer.slice(0,ix));buffer=buffer.slice(ix+1)}
  }
  buffer+=decoder.decode();consume(buffer);return n;
}
try{
  const [manifest,index]=await Promise.all([
    fetch('./data/qa_index/manifest.json').then(r=>{if(!r.ok)throw Error('No source manifest');return r.json()}),
    fetch('./data/corpus_index.json').then(r=>{if(!r.ok)throw Error('No commenter index');return r.json()})
  ]);
  if(manifest.records!==3231||manifest.with_text!==3230||!Array.isArray(manifest.docs))throw Error('Source manifest coverage mismatch');
  meta=manifest;lookup=new Map(index.filings.map(x=>[String(x.id),x]));
  for(const role of [...new Set(index.filings.map(r=>r.role||'unresolved'))].sort()){const o=mk('option','',nice(role));o.value=role;$('ph-role').append(o)}
}catch(err){$('ph-status').textContent='Cannot verify corpus: '+err.message;$('ph-run').disabled=true;return}
const makeChart=(id,entries)=>{const box=$(id);box.replaceChildren();const max=Math.max(1,...entries.map(x=>x[1]));for(const [label,n] of entries){const row=mk('div','phrase-bar'),bar=mk('div','phrase-track'),fill=mk('div','phrase-fill');fill.style.width=100*n/max+'%';bar.append(fill);row.append(mk('span','',label),bar,mk('strong','',fmt(n)));box.append(row)}};
function render(){
 const sorted=[...results].sort((a,b)=>{
 const mode=$('ph-sort').value;
 if(mode==='name')return String(a.filer).localeCompare(String(b.filer));
 if(mode==='old')return String(a.date).localeCompare(String(b.date));
 return String(b.date).localeCompare(String(a.date));
 });
 const holder=$('ph-results');holder.replaceChildren();
 for(const r of sorted.slice(0,visible)){
   const row=mk('article','phrase-result'),heading=mk('div','');
   heading.append(link(r.filer||'Filing '+r.id,'./corpus.html?id='+encodeURIComponent(r.id)));
   heading.append(mk('span','ask-small',' · '+r.date+' · '+nice(r.role)+' · '+(r.near?'Same passage':'Different passages or only one concept')+(r.ocr?' · OCR candidate':'')));
   const excerpt=mk('blockquote','',r.excerpt);
   const links=mk('div','');links.append(link('Original FCC record ↗',url(r.id)));
   row.append(heading,excerpt,links);holder.append(row);
 }
 $('ph-displayed').textContent=fmt(Math.min(visible,results.length))+' of '+fmt(results.length)+' filings displayed';
 $('ph-more').hidden=visible>=results.length;
}
function publish(raw,stats,read){
 results=raw;visible=50;
 $('ph-scanned').textContent=fmt(read);
 $('ph-matches').textContent=fmt(raw.length);
 $('ph-both').textContent=fmt(stats.both);
 $('ph-near').textContent=fmt(stats.near);
 const roles=new Map(),dates=new Map();
 for(const r of raw){
  roles.set(nice(r.role),(roles.get(nice(r.role))||0)+1);
  if(r.date){const d=r.date.slice(0,10);dates.set(d,(dates.get(d)||0)+1);}
 }
 makeChart('ph-roles',[...roles].sort((a,b)=>b[1]-a[1]).slice(0,15));
 makeChart('ph-dates',[...dates].sort((a,b)=>b[1]-a[1]).slice(0,15));
 $('ph-insights').hidden=false;$('ph-export').disabled=false;render();
}
$('ph-run').onclick=async()=>{
 const A=parse('ph-a'),B=parse('ph-b'),mode=$('ph-mode').value,role=$('ph-role').value;
 if(!A.length||!B.length){$('ph-status').textContent='Provide two sets of concrete phrases, each at least three characters long.';return}
 $('ph-run').disabled=true;$('ph-export').disabled=true;$('ph-insights').hidden=true;results=[];
 try{
  const docs=meta.docs,byShard=new Map(),ids=new Set();
  for(const row of docs){ids.add(String(row.id));byShard.set(row.shard,(byShard.get(row.shard)||0)+1)}
  if(ids.size!==meta.records||byShard.size!==12)throw Error('Incomplete source manifest');
  let read=0,both=0,near=0;const rows=[];
  let ix=0;
  for(const [shard,expected] of [...byShard].sort(([a],[b])=>a.localeCompare(b))){
   $('ph-status').textContent='Scanning '+(++ix)+'/12 source shards · '+fmt(read)+' source filings checked…';
   const size=await scanShard(shard,r=>{
    const id=String(r.submission_id||'');
    if(!ids.delete(id))throw Error('Unexpected or duplicated filing ID '+id);
    const p=inspect(String(r.text||''),A,B);
    const m=lookup.get(id)||{};
    if(role && (m.role||'unresolved')!==role)return;
    // Counts refer to the same selected commenter population as the results.
    // Every source file is still scanned and reconciled irrespective of filter.
    if(p.hasA&&p.hasB)both++;
    if(p.near)near++;
    if(!(mode==='near'?p.near:mode==='both'?(p.hasA&&p.hasB):(p.hasA||p.hasB)))return;
    rows.push({id,date:String(r.date_submission||m.date||''),filer:String(r.filer_raw||m.organization||''),
      role:m.role||'unresolved',ocr:Boolean(m.ocr),near:p.near,excerpt:p.excerpt});
   });
   if(size!==expected)throw Error('Source shard '+shard+' has '+size+' records, expected '+expected);
   read+=size;
  }
  if(read!==meta.records||ids.size)throw Error('Missing source filing records; search aborted');
  publish(rows,{both,near},read);
  $('ph-status').textContent='Verified complete scan: '+fmt(read)+' source filings · '+fmt(rows.length)+' matched selected rule and category. The two-concept matches are not policy positions.';
 }catch(err){$('ph-status').textContent='INCOMPLETE SCAN: '+err.message+' No partial findings were published.';$('ph-insights').hidden=true;results=[]}
 finally{$('ph-run').disabled=false}
};
$('ph-sort').onchange=render;
$('ph-more').onclick=()=>{visible+=50;render()};
$('ph-reset').onclick=()=>{results=[];$('ph-insights').hidden=true;$('ph-export').disabled=true;$('ph-status').textContent='Displayed results cleared. Input phrases retained.'};
$('ph-export').onclick=()=>{
 const q=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replaceAll('"','""')+'"';
 const lines=['filing_id,date,provisional_role,ocr_candidate,same_passage,source_excerpt,fcc_url',...results.map(r=>[r.id,r.date,r.role,r.ocr?1:0,r.near?1:0,r.excerpt,url(r.id)].map(q).join(','))];
 const u=URL.createObjectURL(new Blob([lines.join('\n')],{type:'text/csv;charset=utf-8'})),a=mk('a');a.href=u;a.download='erate_source_phrase_evidence.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);
};
})();