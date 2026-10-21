"use strict";
(async function(){
const $=id=>document.getElementById(id);
const friendly=s=>String(s).replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
const escape=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const num=n=>Number(n).toLocaleString("en-US",{maximumFractionDigits:1});
let data,rows=[],issues=[],dateOnly="",pair=[],page=0;
const limit=35;
try{
 const response=await fetch("./data/corpus_index.json",{cache:"no-store"});
 if(!response.ok)throw Error("Index HTTP "+response.status);
 data=await response.json();
 if(!Array.isArray(data.filings)||!Array.isArray(data.issue_keys))throw Error("Unexpected index schema");
 issues=data.issue_keys; rows=data.filings;
 const options=(id,values)=>{for(const x of [...new Set(values.filter(Boolean))].sort()){const o=document.createElement("option");o.value=x;o.textContent=friendly(x);$(id).append(o)}};
 options("lab-role",rows.map(x=>x.role));options("lab-type",rows.map(x=>x.type));options("lab-issue",issues);
 $("lab-status").textContent=num(rows.length)+" indexed filing records loaded. Snapshot: "+escape(data.snapshot||"unknown");
}catch(e){$("lab-status").textContent="Could not load published index: "+e.message;return}
const has=(r,i)=>Boolean((Number(r.issues)||0)&(1<<i));
const weight=r=>$("lab-weight").value==="dedupe"?1/Math.max(1,Number(r.duplicate_count)||1):1;
const sum=a=>a.reduce((n,r)=>n+weight(r),0);
const percent=(a,b)=>b?num(a/b*100)+"%":"—";
const controls=["lab-role","lab-type","lab-issue","lab-ocr","lab-weight"];
const scoped=()=>rows.filter(r=>
 (!$("lab-role").value||r.role===$("lab-role").value)&&
 (!$("lab-type").value||r.type===$("lab-type").value)&&
 (!$("lab-issue").value||has(r,issues.indexOf($("lab-issue").value)))&&
 (!$("lab-ocr").value||Boolean(r.ocr)===($("lab-ocr").value==="yes")));
const inSelection=r=>(!dateOnly||r.date===dateOnly)&&(!pair.length||(has(r,pair[0])&&has(r,pair[1])));
function metricBars(id,entries,max,onclick){
 $(id).replaceChildren();
 for(const [label,value,caption,key] of entries){
  const line=document.createElement("div");line.className="lab-row";
  const name=document.createElement(onclick?"button":"span");name.textContent=label;
  if(onclick){name.className="lab-link";name.onclick=()=>onclick(key);name.type="button";}
  const track=document.createElement("div");track.className="lab-track";
  const fill=document.createElement("div");fill.className="lab-fill";fill.style.width=(max?100*value/max:0)+"%";track.append(fill);
  const n=document.createElement("span");n.textContent=caption??num(value);
  line.append(name,track,n);$(id).append(line);
 }
}
function redraw(){
 const base=scoped(),selected=base.filter(inSelection),denom=sum(base);
 $("lab-count").textContent=num(selected.length)+" source filings · weighted "+num(sum(selected))+"; "+num(base.length)+" match primary filters";
 const byDate=new Map();
 for(const r of base)if(r.date)byDate.set(r.date,(byDate.get(r.date)||0)+weight(r));
 const dates=[...byDate].sort(([a],[b])=>a.localeCompare(b));
 const peak=Math.max(1,...dates.map(x=>x[1]));$("lab-timeline").replaceChildren();
 for(const [day,v] of dates){
 const bar=document.createElement("button");bar.type="button";bar.className="lab-column"+(dateOnly===day?" active":"");
 bar.style.height=Math.max(2,100*v/peak)+"%";bar.title=day+": "+num(v)+" weighted filings";
 bar.setAttribute("aria-label",bar.title);bar.onclick=()=>{dateOnly=dateOnly===day?"":day;page=0;redraw()};
 $("lab-timeline").append(bar);
 }
 $("lab-timeline-label").textContent=(dateOnly?"Date selected: "+dateOnly+" (click again to clear). ":"Select any date to filter.")+" "+dates.length+" dates represented.";
 const issueIndex=issues.indexOf($("lab-issue").value);
 const roles=[...new Set(base.map(r=>r.role||"unresolved"))].map(role=>{
 const subset=base.filter(r=>(r.role||"unresolved")===role);
 const hits=issueIndex<0?sum(subset):sum(subset.filter(r=>has(r,issueIndex)));
 return {role,hits,total:sum(subset)}
 }).sort((a,b)=>b.hits-a.hits);
 metricBars("lab-roles",roles.map(x=>[friendly(x.role),x.hits,issueIndex<0?num(x.hits):percent(x.hits,x.total),x.role]),Math.max(1,...roles.map(x=>x.hits)),role=>{$("lab-role").value= $("lab-role").value===role?"":role;page=0;redraw()});
 const counts=[];
 for(let i=0;i<issues.length;i++)for(let j=i+1;j<issues.length;j++){
 const v=sum(base.filter(r=>has(r,i)&&has(r,j)));
 counts.push({i,j,v});
 }
 counts.sort((a,b)=>b.v-a.v);const top=counts.slice(0,12);
 metricBars("lab-pairs",top.map(x=>[friendly(issues[x.i])+" + "+friendly(issues[x.j]),x.v,num(x.v),x]),Math.max(1,...top.map(x=>x.v)),x=>{pair=pair[0]===x.i&&pair[1]===x.j?[]:[x.i,x.j];page=0;redraw()});
 if(pair.length){const p=document.createElement("p");p.className="lab-hint";p.textContent="Pair filter active: "+friendly(issues[pair[0]])+" + "+friendly(issues[pair[1]]);const b=document.createElement("button");b.textContent="Clear pair";b.onclick=()=>{pair=[];page=0;redraw()};p.append(" ",b);$("lab-pairs").prepend(p);}
 const copy=selected.filter(r=>Number(r.duplicate_count)>1);
 const sens=[
 ["All selected filing records",selected.length],
 ["Filings in repeated exact-text families",copy.length],
 ["Fractional text-family equivalent",selected.reduce((t,r)=>t+1/Math.max(1,Number(r.duplicate_count)||1),0)],
 ["OCR-candidate filings",selected.filter(r=>r.ocr).length],
 ["Records without a displayed organization",selected.filter(r=>!r.organization).length]
 ];
 metricBars("lab-sensitivity",sens.map(([a,b])=>[a,b,num(b)]),Math.max(1,selected.length));
 const q=$("lab-search").value.toLowerCase().trim();
 const result=selected.filter(r=>!q||String(r.id).includes(q)||String(r.organization||"").toLowerCase().includes(q));
 const pages=Math.max(1,Math.ceil(result.length/limit));page=Math.min(page,pages-1);
 $("lab-page-label").textContent=num(result.length)+" matches · page "+(page+1)+"/"+pages;
 $("lab-prev").disabled=page===0;$("lab-next").disabled=page>=pages-1;
 $("lab-table").innerHTML=result.slice(page*limit,(page+1)*limit).map(r=>'<tr><td>'+escape(r.date)+'</td><td>'+escape(r.id)+'</td><td>'+escape(r.organization||"Not displayed")+'</td><td>'+escape(friendly(r.role||"unresolved"))+'</td><td>'+escape(issues.filter((_,i)=>has(r,i)).map(friendly).join(", ")||"None detected")+'</td><td>'+escape(r.duplicate_count||1)+'</td><td><a target="_blank" rel="noopener noreferrer" href="https://www.fcc.gov/ecfs/search/search-filings/filing/'+encodeURIComponent(r.id)+'">FCC ↗</a></td></tr>').join("");
 window.labExport=()=>result;
}
controls.forEach(id=>$(id).addEventListener("change",()=>{page=0;redraw()}));
$("lab-search").addEventListener("input",()=>{page=0;redraw()});
$("lab-prev").onclick=()=>{page--;redraw()};$("lab-next").onclick=()=>{page++;redraw()};
$("lab-reset").onclick=()=>{for(const id of controls)$(id).value=id==="lab-weight"?"filings":"";$("lab-search").value="";dateOnly="";pair=[];page=0;redraw()};
$("lab-download").onclick=()=>{
const fields=["id","date","type","role","organization","ocr","issues","duplicate_count"];
const safe=x=>'"'+String(x??"").replace(/^[=+@\-\t\r]/,"'$&").replaceAll('"','""')+'"';
const lines=[fields.join(","),...window.labExport().map(r=>fields.map(k=>safe(r[k])).join(","))];
const url=URL.createObjectURL(new Blob([lines.join("\n")],{type:"text/csv;charset=utf-8"}));
const a=document.createElement("a");a.href=url;a.download="erate_patterns_index.csv";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
redraw();
})();