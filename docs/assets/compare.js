"use strict";
(async()=>{
const $=id=>document.getElementById(id),title=s=>String(s||"Unresolved").replace(/_/g," ").replace(/\b\w/g,x=>x.toUpperCase()),fmt=n=>Number(n).toLocaleString("en-US",{maximumFractionDigits:2});
let index;
try{const r=await fetch("./data/corpus_index.json");if(!r.ok)throw Error("HTTP "+r.status);index=await r.json();if(!Array.isArray(index.filings)||!Array.isArray(index.issue_keys))throw Error("Unexpected schema")}catch(e){$("compare-status").textContent="Data unavailable: "+e.message;return}
const all=index.filings,issues=index.issue_keys;let current=[],selection=null,visible=50,matrix=[];
for(const type of [...new Set(all.map(x=>x.type).filter(Boolean))].sort()){let o=document.createElement("option");o.value=type;o.textContent=type;$("compare-type").append(o)}
const has=(r,i)=>!!(Number(r.issues)&(1<<i)),weight=r=>$("compare-weight").value==="fraction"?1/Math.max(1,Number(r.duplicate_count)||1):1;
const sum=rows=>rows.reduce((s,r)=>s+weight(r),0);
const safe=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const base=()=>all.filter(r=>(!$("compare-type").value||r.type===$("compare-type").value)&&($("compare-ocr").value!=="none"||!r.ocr));
const val=(num,den,otherNum,otherDen)=>{
switch($("compare-metric").value){case "count":return num;case "share":return den?100*num/den:null;default:return den&&otherNum&&otherDen?(num/den)/(otherNum/otherDen):null}
};
const textValue=x=>x===null?"n/a":$("compare-metric").value==="count"?fmt(x):$("compare-metric").value==="share"?fmt(x)+"%":fmt(x)+"×";
function render(){
current=base();const total=sum(current),roles=[...new Set(current.map(r=>r.role||"unresolved"))].sort(),fullIssue=issues.map((_,i)=>sum(current.filter(r=>has(r,i))));
$("compare-status").textContent=fmt(current.length)+" of "+fmt(all.length)+" indexed filing records in the selected universe; weighted denominator "+fmt(total)+".";
$("compare-head").innerHTML="<tr><th scope='col'>Filer category</th>"+issues.map(i=>"<th scope='col'>"+safe(title(i))+"</th>").join("")+"</tr>";
matrix=[];
$("compare-body").replaceChildren();
for(const role of roles){
const group=current.filter(r=>(r.role||"unresolved")===role),den=sum(group),row=document.createElement("tr"),heading=document.createElement("td");heading.textContent=title(role)+" ("+fmt(den)+")";row.append(heading);
for(let i=0;i<issues.length;i++){
const matching=group.filter(r=>has(r,i)),n=sum(matching),outside=total-den,outsideMatching=fullIssue[i]-n,v=val(n,den,outsideMatching,outside);
matrix.push({role,issue:issues[i],n,den,v});const cell=document.createElement("td");cell.tabIndex=0;cell.setAttribute("role","button");cell.setAttribute("aria-label",title(role)+" and "+title(issues[i])+" "+textValue(v));
cell.textContent=textValue(v);const intensity=$("compare-metric").value==="lift"?Math.min(1,(v||0)/3):$("compare-metric").value==="share"?Math.min(1,(v||0)/100):Math.min(1,n/Math.max(1,fullIssue[i]));
cell.style.background="rgba(44,109,149,"+(0.05+0.65*intensity)+")";cell.style.color=intensity>0.65?"white":"#182c3b";
if(selection&&selection.role===role&&selection.issue===issues[i])cell.classList.add("selected");
cell.onclick=()=>{selection={role,issue:issues[i],index:i};visible=50;render()};cell.onkeydown=e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();cell.click()}};row.append(cell);
} $("compare-body").append(row);
}
const max=Math.max(1,...fullIssue);$("compare-issues").innerHTML=issues.map((x,i)=>"<div class='compare-row'><span>"+safe(title(x))+"</span><div class='compare-track'><div class='compare-fill' style='width:"+(100*fullIssue[i]/max)+"%'></div></div><strong>"+fmt(fullIssue[i])+"</strong></div>").join("");
const chosen=selection&&roles.includes(selection.role)?selection:null;
if(!chosen){$("compare-selection").textContent="Select an issue and commenter-category cell."; $("compare-detail").textContent="";$("compare-records").replaceChildren();$("compare-recordcount").textContent="";$("compare-more").disabled=true;return}
const cohort=current.filter(r=>(r.role||"unresolved")===chosen.role),matches=cohort.filter(r=>has(r,chosen.index)),others=current.filter(r=>(r.role||"unresolved")!==chosen.role),outsideHits=others.filter(r=>has(r,chosen.index));
const catRate=sum(cohort)?100*sum(matches)/sum(cohort):0,outRate=sum(others)?100*sum(outsideHits)/sum(others):0;
$("compare-selection").textContent=title(chosen.role)+" × "+title(chosen.issue);
$("compare-detail").innerHTML="<p><strong>"+fmt(matches.length)+"</strong> raw matched records out of "+fmt(cohort.length)+" category filings</p><p><strong>"+fmt(catRate)+"%</strong> weighted within-category mention rate</p><p><strong>"+fmt(outRate)+"%</strong> weighted mention rate in other categories</p><p><strong>"+(outRate?fmt(catRate/outRate)+"×":"n/a")+"</strong> relative prevalence</p><p class='compare-caption'>This comparison measures language occurrence, not a pro- or anti-E-Rate position.</p>";
$("compare-recordcount").textContent=fmt(matches.length)+" source filings. Displaying first "+fmt(Math.min(visible,matches.length))+".";
$("compare-records").innerHTML=matches.slice(0,visible).map(r=>"<li><a href='https://www.fcc.gov/ecfs/filing/"+encodeURIComponent(r.id)+"' target='_blank' rel='noopener noreferrer'>FCC filing "+safe(r.id)+"</a> — "+safe(r.date||"Undated")+" · "+safe(r.organization||"Organization not shown")+"</li>").join("");
$("compare-more").disabled=visible>=matches.length;
window.selectedRows=matches;
}
function download(filename,lines){const blob=new Blob([lines.join("\n")],{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
const csv=s=>'"'+String(s??"").replace(/^[=+@\-\t\r]/,"'$&").replaceAll('"','""')+'"';
$("compare-export").onclick=()=>download("erate_stakeholder_issue_matrix.csv",["role,issue,matched_weight,group_weight,metric_value,metric_name",...matrix.map(r=>[r.role,r.issue,r.n,r.den,r.v??"",$("compare-metric").value].map(csv).join(","))]);
$("compare-record-export").onclick=()=>download("erate_issue_category_sources.csv",["filing_id,date,category,organization,fcc_url",...(window.selectedRows||[]).map(r=>[r.id,r.date,r.role,r.organization,"https://www.fcc.gov/ecfs/filing/"+r.id].map(csv).join(","))]);
$("compare-more").onclick=()=>{visible+=50;render()};
["compare-type","compare-weight","compare-metric","compare-ocr"].forEach(id=>$(id).onchange=()=>{visible=50;render()});
render();
})();