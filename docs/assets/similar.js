"use strict";
(async()=>{
const $=id=>document.getElementById(id);
const fmt=n=>Number(n||0).toLocaleString('en-US');
const mk=(tag,cl,v)=>{const e=document.createElement(tag);if(cl)e.className=cl;if(v!==undefined)e.textContent=String(v);return e};
const link=(txt,url)=>{const a=mk('a','',txt);a.href=url;a.rel='noopener noreferrer';a.target='_blank';return a};
const fcc=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(id);
const nice=s=>String(s||'unresolved').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
let manifest,index,cache=new Map(),ranked=[],count=25,busy=false;
async function load(){
 if(manifest)return;
 const [m,i]=await Promise.all([
   fetch('./data/qa_index/manifest.json').then(r=>{if(!r.ok)throw Error('Missing QA source index');return r.json()}),
   fetch('./data/corpus_index.json').then(r=>{if(!r.ok)throw Error('Missing filing metadata');return r.json()})
 ]);
 if(m.records!==3231||m.with_text!==3230||m.docs.length!==m.records||!Array.isArray(m.buckets))
   throw Error('QA source index fails published population checks');
 manifest=m;index=new Map(i.filings.map(x=>[String(x.id),x]));
}
async function bucket(name){
 if(!cache.has(name))cache.set(name,fetch('./data/qa_index/'+encodeURIComponent(name)+'.json')
   .then(r=>{if(!r.ok)throw Error('Missing term index '+name);return r.json()}));
 return cache.get(name);
}
function render(){
 const holder=$('sim-results');holder.replaceChildren();
 for(const row of ranked.slice(0,count)){
   const d=row.doc,m=index.get(String(d.id))||{},card=mk('article','sim-card');
   const top=mk('div','sim-head');
   top.append(link(d.filer||'FCC filing '+d.id,'./corpus.html?id='+encodeURIComponent(d.id)));
   top.append(mk('strong','',Math.round(row.similarity*1000)/10+'% vocabulary similarity'));
   const meter=mk('div','sim-meter'),fill=mk('div');fill.style.width=(100*row.similarity)+'%';meter.append(fill);
   const desc=mk('p','sim-hint',String(d.date||'Undated')+' · '+nice(m.role)+' · '+(m.duplicate_count>1?'Exact-text family size '+m.duplicate_count+' · ':'')+'Indexed terms '+fmt(d.length));
   const links=mk('div','');links.append(link('Original FCC record ↗',fcc(d.id)));
   card.append(top,meter,desc,links);holder.append(card);
 }
 $('sim-more').hidden=count>=ranked.length;
}
function exportCSV(){
 const safe=s=>'"'+String(s??'').replace(/^[=+@\-\t\r]/,"'$&").replaceAll('"','""')+'"';
 const out=['filing_id,filer,date,provisional_role,lexical_cosine,exact_text_family_size,fcc_url',...ranked.map(r=>{
   const d=r.doc,m=index.get(String(d.id))||{};
   return [d.id,d.filer,d.date,m.role||'',r.similarity,m.duplicate_count||'',fcc(d.id)].map(safe).join(',');
 })];
 const u=URL.createObjectURL(new Blob([out.join('\n')],{type:'text/csv;charset=utf-8'})),a=mk('a');a.href=u;a.download='fcc_similar_filings.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);
}
async function search(){
 if(busy)return;const id=$('sim-id').value.trim();
 if(!/^\d{8,16}$/.test(id)){$('sim-status').textContent='Enter a numeric FCC filing ID.';return;}
 busy=true;$('sim-run').disabled=true;$('sim-export').disabled=true;
 try{
   await load();
   const seed=manifest.docs.findIndex(d=>String(d.id)===id);
   if(seed<0)throw Error('Filing ID is not part of this October 20 source snapshot');
   if(!manifest.docs[seed].has_text)throw Error('This filing has no extractable source text for comparison');
   const norms=new Float64Array(manifest.records),dots=new Float64Array(manifest.records);
   let termCount=0,seedTerms=0;
   const N=manifest.records;
   for(let k=0;k<manifest.buckets.length;k++){
     const name=manifest.buckets[k];
     $('sim-status').textContent='Comparing all documents · vocabulary group '+(k+1)+'/'+manifest.buckets.length+'…';
     const terms=await bucket(name);
     for(const postings of Object.values(terms)){
       const df=postings.length/2;
       if(!df||df>=N)continue;
       // Standard nonnegative inverse-document-frequency weight.
       const idf=Math.log(1+(N-df+0.5)/(df+0.5));
       let sWeight=0;
       for(let t=0;t<postings.length;t+=2){
         if(postings[t]===seed){sWeight=(1+Math.log(Math.max(1,postings[t+1])))*idf;break;}
       }
       if(sWeight)seedTerms++;
       for(let t=0;t<postings.length;t+=2){
         const doc=postings[t],tf=postings[t+1];
         if(!Number.isInteger(doc)||doc<0||doc>=N)throw Error('Corrupt term postings in '+name);
         const w=(1+Math.log(Math.max(1,tf)))*idf;
         norms[doc]+=w*w;
         if(sWeight)dots[doc]+=w*sWeight;
       }
       termCount++;
     }
   }
   if(!norms[seed])throw Error('No indexed vocabulary for seed filing');
   const denominator=Math.sqrt(norms[seed]);
   ranked=[];
   for(let i=0;i<N;i++){
     if(i===seed||!norms[i]||!dots[i])continue;
     const sim=Math.min(1,dots[i]/(denominator*Math.sqrt(norms[i])));
     if(sim>0)ranked.push({doc:manifest.docs[i],similarity:sim});
   }
   ranked.sort((a,b)=>b.similarity-a.similarity||a.doc.id.localeCompare(b.doc.id));
   count=25;$('sim-content').hidden=false;
   const d=manifest.docs[seed],m=index.get(id)||{};
   const seedHost=$('sim-seed');seedHost.replaceChildren();
   seedHost.append(link(d.filer||'Filing '+id,'./corpus.html?id='+encodeURIComponent(id)),
     mk('p','sim-hint','FCC '+id+' · '+d.date+' · '+nice(m.role)+' · '+fmt(d.length)+' indexed terms · '+fmt(seedTerms)+' indexed vocabulary items'));
   render();$('sim-export').disabled=ranked.length===0;
   $('sim-status').textContent='Compared '+fmt(N)+' filing records across '+fmt(termCount)+' indexed vocabulary terms. '+fmt(ranked.length)+' filings share at least one indexed term; sorted by TF-IDF cosine similarity.';
 }catch(err){$('sim-status').textContent='Similarity analysis unavailable: '+err.message;$('sim-content').hidden=true;}
 finally{busy=false;$('sim-run').disabled=false;}
}
$('sim-run').onclick=search;$('sim-id').addEventListener('keydown',e=>{if(e.key==='Enter')search()});
$('sim-more').onclick=()=>{count+=25;render()};$('sim-export').onclick=exportCSV;
const query=new URLSearchParams(location.search).get('id');if(query&&/^\d{8,16}$/.test(query))$('sim-id').value=query;
})();