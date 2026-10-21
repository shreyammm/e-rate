"use strict";
(async()=>{
const $=id=>document.getElementById(id);
const n=x=>Number(x||0).toLocaleString("en-US",{maximumFractionDigits:1});
const el=(tag,cls,text)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=String(text);return x};
const friendly=s=>String(s||"Unknown").replace(/_/g," ").replace(/\b\w/g,c=>c.toUpperCase());
const link=(text,url)=>{const a=el("a","",text);a.href=url;a.rel="noopener noreferrer";a.target="_blank";return a};
const source=id=>"https://www.fcc.gov/ecfs/filing/"+encodeURIComponent(String(id));
const search=q=>"./ask.html?q="+encodeURIComponent(q);
const makeQuestion=t=>"What positions and competing reasoning do FCC commenters express about "+t+"? Cite original filings.";
const csv=s=>'"'+String(s??"").replace(/^[=+@\-\t\r]/,"'$&").replaceAll('"','""')+'"';
const exportCsv=(name,lines)=>{const u=URL.createObjectURL(new Blob([lines.join("\n")],{type:"text/csv;charset=utf-8"}));const a=el("a");a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
let clusters=[],reasons=[],byRole,roles=[],selectedCluster=null,selectedReason=null;
try{
 const [landscape,census,cross]=await Promise.all([
  fetch("./data/argument_landscape.json").then(r=>{if(!r.ok)throw Error("Language discovery data unavailable");return r.json()}),
  fetch("./data/exhaustive_census.json").then(r=>{if(!r.ok)throw Error("Source-wide reason counts unavailable");return r.json()}),
  fetch("./data/argument_language_by_role.json").then(r=>{if(!r.ok)throw Error("Stakeholder language matrix unavailable");return r.json()})
 ]);
 if(landscape.source_filings_scanned!==3231||landscape.readable_filings!==3230||census.coverage.filings!==3231||
    !Array.isArray(landscape.language_themes)||!Array.isArray(census.argument_language_signals)||!Array.isArray(cross.role_ids))
    throw Error("Inconsistent public source census");
 if(cross.role_ids.length!==census.roles.length||cross.role_ids.some((id,i)=>id!==census.roles[i].id))
    throw Error("Stakeholder role data are not aligned");
 clusters=landscape.language_themes.map(t=>{
  const quotes=(t.evidence||[]).map(e=>String(e.quote||"").replace(/\s+/g," ").trim().toLowerCase()).filter(Boolean);
  const distinct=new Set(quotes).size;
  const dominant=Math.max(0,...Object.values(t.filing_categories||{}).map(Number));
  const total=Object.values(t.filing_categories||{}).reduce((a,b)=>a+Number(b||0),0);
  return {...t,quoteDistinct:distinct,sampleSize:quotes.length,repeatRisk:quotes.length>=3&&distinct/quotes.length<=.5,
    concentration:total?dominant/total:0,concentrationRisk:total>=25&&dominant/total>=.9};
 });
 reasons=census.argument_language_signals;byRole=cross;roles=census.roles;
 for(const reason of reasons)if(!Array.isArray(cross.counts_by_argument[reason.id])||cross.counts_by_argument[reason.id].length!==roles.length)
   throw Error("Incomplete argument-language category matrix: "+reason.id);
 $("at-filings").textContent=n(census.coverage.filings);$("at-read").textContent=n(census.coverage.filings_with_text);
 $("at-clusters").textContent=n(clusters.length);$("at-families").textContent=n(reasons.length);
 $("at-status").textContent="October 20, 2026 text snapshot · "+n(landscape.extracted_argument_language_passages)+" automatically extracted language passages · counts describe text matches, not verified positions.";
}catch(err){$("at-status").textContent="Atlas data failed validation: "+err.message;return}
const queryText=t=>(t.topic_terms||[]).slice(0,5).join(", ");
const headline=t=>(t.topic_terms||[]).slice(0,3).join(" · ")||t.id;
const familyLabel=x=>x.label;
function matchesFilter(t){
 const term=$("at-cluster-query").value.toLowerCase().trim();
 if(term&&!([t.id,t.working_label,...(t.topic_terms||[])].join(" ").toLowerCase().includes(term)))return false;
 const f=$("at-cluster-filter").value;
 if(f==="standard"&&(t.repeatRisk||t.concentrationRisk))return false;
 if(f==="repeat"&&!t.repeatRisk)return false;
 if(f==="skew"&&!t.concentrationRisk)return false;
 return true;
}
function renderClusters(){
 let filtered=clusters.filter(matchesFilter);
 const sort=$("at-cluster-order").value;
 filtered.sort((a,b)=>sort==="distinct"?b.quoteDistinct-a.quoteDistinct||b.filings_with_matching_language-a.filings_with_matching_language:
 sort==="alphabetical"?headline(a).localeCompare(headline(b)):
 b.filings_with_matching_language-a.filings_with_matching_language);
 $("at-cluster-count").textContent=n(filtered.length)+" discovered clusters shown. Counts can overlap and do not measure independent arguments.";
 const host=$("at-clusters-list");host.replaceChildren();
 for(const c of filtered){
  const item=el("button","atlas-cluster");item.type="button";item.setAttribute("aria-pressed",String(selectedCluster?.id===c.id));
  item.append(el("h3","",headline(c)));
  item.append(el("div","atlas-count",n(c.filings_with_matching_language)),
       el("p","", "filings with matching cluster language · "+n(c.quoteDistinct)+" distinct excerpts in "+n(c.sampleSize)+" illustrative samples"));
  if(c.repeatRisk)item.append(el("span","atlas-stamp","High repeated-text signal"));
  if(c.concentrationRisk)item.append(el("span","atlas-stamp","Concentrated source category"));
  item.onclick=()=>{selectedCluster=c;renderClusters();renderEvidence()};
  host.append(item);
 }
 if(!filtered.length)host.append(el("p","atlas-intro","No discovered clusters match these search filters."));
}
function renderEvidence(){
 const c=selectedCluster;if(!c)return;
 $("at-selected-title").textContent="Working cluster: "+headline(c);
 $("at-selected-meta").textContent=n(c.filings_with_matching_language)+" filing-language matches in unsupervised discovery. "+n(c.sampleSize)+" automatically selected source excerpts ("+n(c.quoteDistinct)+" distinct excerpt strings). Neither count establishes endorsed arguments or distinct people.";
 const terms=$("at-selected-terms");terms.replaceChildren();
 for(const term of (c.topic_terms||[]).slice(0,12))terms.append(el("span","atlas-stamp",term));
 const issues=$("at-selected-issues");issues.replaceChildren();
 if(c.repeatRisk)issues.append(el("p","atlas-risk","Repeated identical or near-identical excerpts dominate this small evidence sample. Inspect template families; do not call each sample an independent argument."));
 if(c.concentrationRisk)issues.append(el("p","atlas-risk","A single heuristically assigned filing category represents at least 90% of this cluster's matches. This can reflect concentrated or cross-docket material; inspect source texts before interpreting it."));
 const sample=$("at-selected-evidence");sample.replaceChildren();
 for(const e of c.evidence||[]){
  const article=el("article"),title=el("div");
  title.append(link(e.filer||"FCC filing "+e.id,source(e.id)));
  title.append(el("span","atlas-sub"," · "+String(e.date||"").slice(0,10)+" · "+friendly(e.category||"unresolved")+(e.ocr?" · OCR candidate":"")));
  article.append(title,el("blockquote","",e.quote));
  const links=el("div","atlas-linkrow");
  links.append(link("Read full extracted filing ↗","./corpus.html?id="+encodeURIComponent(e.id)),
    link("Find similar filings ↗","./similar.html?id="+encodeURIComponent(e.id)));
  article.append(links);sample.append(article);
 }
 const actions=$("at-selected-actions");actions.replaceChildren();
 const q=makeQuestion(queryText(c));
 actions.append(link("Ask full corpus about this language ↗",search(q)));
 const d=el("button","","Download selected excerpts CSV");d.type="button";d.onclick=()=>exportCsv("erate_discovered_cluster_evidence.csv",[
  "cluster_id,working_terms,filing_id,date,source_category,ocr,quote,fcc_url",
  ...(c.evidence||[]).map(e=>[c.id,queryText(c),e.id,e.date,e.category,e.ocr?1:0,e.quote,source(e.id)].map(csv).join(","))
 ]);actions.append(d);
}
function reasonSort(a,b){
 const mode=$("at-reason-order").value;
 if(mode==="alpha")return a.label.localeCompare(b.label);
 if(mode==="cross")return b.cross_docket_signature-a.cross_docket_signature||b.filings_with_language-a.filings_with_language;
 return b.filings_with_language-a.filings_with_language;
}
function renderReasons(){
 const term=$("at-reason-query").value.toLowerCase().trim();
 const items=reasons.filter(x=>x.label.toLowerCase().includes(term)).sort(reasonSort);
 const host=$("at-reason-bars");host.replaceChildren();
 const max=Math.max(1,...items.map(x=>x.filings_with_language));
 for(const r of items){
  const button=el("button","atlas-cluster");
  button.style.width="100%";button.style.minHeight="unset";button.style.marginBottom="7px";button.type="button";
  button.setAttribute("aria-pressed",String(selectedReason?.id===r.id));
  const head=el("div");head.style.display="flex";head.style.justifyContent="space-between";head.style.gap="10px";
  head.append(el("strong","",r.label),el("strong","",n(r.filings_with_language)+" filings"));
  const bar=el("span","atlas-meter"),fill=el("i");fill.style.width=(100*r.filings_with_language/max)+"%";bar.append(fill);
  button.append(head,bar);
  if(r.cross_docket_signature)button.append(el("span","atlas-sub",n(r.cross_docket_signature)+" matching filings carry a potential cross-docket-text signature; not necessarily unrelated."));
  button.onclick=()=>{selectedReason=r;renderReasons();renderRoles()};
  host.append(button);
 }
}
function renderRoles(){
 const r=selectedReason;if(!r)return;
 const c=byRole.counts_by_argument[r.id],total=roles.reduce((n,x)=>n+x.filings,0),sum=c.reduce((a,b)=>a+b,0);
 $("at-reason-selected").textContent="Selected: "+r.label+" — "+n(r.filings_with_language)+" matching filing records (language only); "+n(r.cross_docket_signature||0)+" potential cross-docket signatures. Compare category rates below, not raw totals alone.";
 const open=el("a","","Investigate this reasoning across all original filings ↗");open.href=search(makeQuestion(r.label));open.style.fontWeight="650";$("at-reason-selected").append(" ",open);
 const body=$("at-roles");body.replaceChildren();
 for(const [i,role] of roles.map((x,i)=>[i,x]).sort((a,b)=>c[b[0]]/Math.max(1,b[1].filings)-c[a[0]]/Math.max(1,a[1].filings))){
  const hits=c[i],base=role.filings,outside=total-base,outHits=sum-hits,p=base?hits/base:0,outRate=outside?outHits/outside:0,ratio=outRate?p/outRate:null;
  const tr=el("tr");
  const label=el("td","",role.label),matched=el("td","",n(hits)),den=el("td","",n(base)),share=el("td"),lift=el("td");
  share.append(el("strong","",n(100*p)+"%"));
  const track=el("span","atlas-meter");track.style.minWidth="70px";const fill=el("i");fill.style.width=(100*p)+"%";track.append(fill);share.append(track);
  lift.textContent=ratio===null?"n/a":n(ratio)+"×";tr.append(label,matched,den,share,lift);body.append(tr);
 }
}
function renderMap(){
 const box=$("at-map");box.replaceChildren();
 const svgNS="http://www.w3.org/2000/svg";
 const create=(name,attrs)=>{const x=document.createElementNS(svgNS,name);for(const [k,v] of Object.entries(attrs||{}))x.setAttribute(k,String(v));return x};
 const W=900,H=550,cx=W/2,cy=H/2;
 const excluded=new Set("the and are for with from need needs use using used this that should can could must will a an on to of in as e rate proposal support provide access".split(" "));
 const token=t=>new Set((t.topic_terms||[]).slice(0,9).join(" ").toLowerCase().match(/[a-z]{3,}/g)?.filter(w=>!excluded.has(w))||[]);
 const terms=clusters.map(token),edges=[];
 for(let i=0;i<clusters.length;i++)for(let j=i+1;j<clusters.length;j++){
  const overlap=[...terms[i]].filter(t=>terms[j].has(t)).length;
  const union=terms[i].size+terms[j].size-overlap;
  const score=union?overlap/union:0;
  if(overlap>=1&&score>=.075)edges.push({i,j,score,overlap});
 }
 const nodes=clusters.map((t,i)=>({x:cx+195*Math.cos(i*Math.PI*2/clusters.length),
    y:cy+195*Math.sin(i*Math.PI*2/clusters.length),r:11+12*Math.sqrt(t.filings_with_matching_language/Math.max(1,...clusters.map(x=>x.filings_with_matching_language)))}));
 for(let turn=0;turn<160;turn++){
   const change=nodes.map(()=>({x:0,y:0}));
   for(let i=0;i<nodes.length;i++){
     change[i].x+=(cx-nodes[i].x)*.006;
     change[i].y+=(cy-nodes[i].y)*.006;
     for(let j=i+1;j<nodes.length;j++){
       const dx=nodes[j].x-nodes[i].x,dy=nodes[j].y-nodes[i].y,d2=Math.max(100,dx*dx+dy*dy);
       const push=10500/d2,dist=Math.sqrt(d2);
       change[i].x-=push*dx/dist;change[i].y-=push*dy/dist;
       change[j].x+=push*dx/dist;change[j].y+=push*dy/dist;
     }
   }
   for(const e of edges){
     const a=nodes[e.i],b=nodes[e.j],dx=b.x-a.x,dy=b.y-a.y,dist=Math.max(1,Math.hypot(dx,dy));
     const force=(dist-135)*(.012+.032*e.score);
     change[e.i].x+=force*dx/dist;change[e.i].y+=force*dy/dist;
     change[e.j].x-=force*dx/dist;change[e.j].y-=force*dy/dist;
   }
   for(let i=0;i<nodes.length;i++){
     nodes[i].x=Math.max(70,Math.min(W-70,nodes[i].x+Math.max(-12,Math.min(12,change[i].x))));
     nodes[i].y=Math.max(55,Math.min(H-55,nodes[i].y+Math.max(-12,Math.min(12,change[i].y))));
   }
 }
 const svg=create("svg",{viewBox:"0 0 "+W+" "+H,width:"100%","aria-label":"Related language clusters connected by shared top vocabulary",role:"img"});
 svg.style.minWidth="640px";svg.style.display="block";
 const lines=create("g");
 for(const e of edges){
  const a=nodes[e.i],b=nodes[e.j],line=create("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,
    stroke:"#9ab6c6","stroke-opacity":Math.min(.88,.25+e.score*1.5),"stroke-width":Math.max(1,2.5*e.score+1)});
  const title=create("title");title.textContent=n(e.overlap)+" shared top-vocabulary words; Jaccard "+(100*e.score).toFixed(1)+"%. Not inferred agreement.";
  line.append(title);lines.append(line);
 }
 svg.append(lines);
 const dots=create("g");
 clusters.forEach((t,i)=>{
   const p=nodes[i],g=create("g",{tabindex:"0",role:"button","aria-label":"Inspect cluster "+headline(t)});g.style.cursor="pointer";
   const circle=create("circle",{cx:p.x,cy:p.y,r:p.r,fill:t.concentrationRisk||t.repeatRisk?"#996e3d":"#2d7196",stroke:"#fff","stroke-width":2});
   const caption=create("text",{x:p.x,y:p.y+p.r+14,"font-size":"10","font-weight":"600",fill:"#18384e","text-anchor":"middle"});
   caption.textContent=headline(t).slice(0,28);
   const tooltip=create("title");tooltip.textContent=headline(t)+"; "+n(t.filings_with_matching_language)+" matching filing texts. Select for source examples.";
   g.append(circle,caption,tooltip);
   const activate=()=>{
     selectedCluster=t;renderClusters();renderEvidence();
     $("at-selected-title").scrollIntoView({behavior:"smooth",block:"start"});
   };
   g.addEventListener("click",activate);g.addEventListener("keydown",ev=>{if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();activate()}});
   dots.append(g);
 });
 svg.append(dots);box.append(svg);
 $("at-map-status").textContent=n(clusters.length)+" discovered clusters; "+n(edges.length)+" links based on shared vocabulary. Node size tracks filing-language matches; amber nodes have repetition or source-concentration flags. This is not a co-filing or consensus network.";
}
const questions=[
 ["Protect connectivity or restrict screen use?","Which filers acknowledge screen-time concerns but reject limiting E-Rate funding, and which explicitly favor funding restrictions?",
  "What evidence supports E-Rate funding conditions tied to screen time, and what counterarguments do commenters offer?"],
 ["Federal conditions or local autonomy?","Where do commenters argue for national online-safety requirements versus school, library, parent, or teacher discretion?",
  "How do commenters compare federal screen-use requirements with local educational authority and parent choice?"],
 ["Program integrity or new compliance costs?","Do consultant-registration, fee, and reporting safeguards have benefits that commenters think outweigh their implementation burdens?",
  "What arguments favor or criticize tougher E-Rate consultant oversight, registration and administrative compliance?"],
 ["Continue funding or target assistance?","How do commenters compare universal program continuity with narrowing eligibility by geography, competition, or price?",
  "What arguments favor retaining broad E-Rate eligibility versus targeting funding by geography or local market competition?"],
 ["Filtering and safety or privacy and speech?","How are restrictions, CIPA monitoring, censorship, privacy, and children's online safety reconciled across filings?",
  "Where do FCC commenters disagree about CIPA filtering, monitoring students, privacy, and free expression?"],
 ["Measured learning outcomes or unequal access?","What outcomes do filers propose using to evaluate internet services, and how do they consider equity or school capacity?",
  "How do commenters evaluate E-Rate with student learning outcomes, and what access and equity concerns complicate that approach?"]
];
const tensionHost=$("at-tensions");
for(const [name,body,question] of questions){
 const card=el("article","atlas-tension");card.append(el("strong","",name),el("p","",body),link("Investigate all original filings ↗",search(question)));tensionHost.append(card);
}
["at-cluster-query","at-cluster-filter","at-cluster-order"].forEach(id=>$(id).addEventListener(id.includes("query")?"input":"change",renderClusters));
["at-reason-query","at-reason-order"].forEach(id=>$(id).addEventListener(id.includes("query")?"input":"change",renderReasons));
selectedCluster=clusters[0];selectedReason=reasons[0];renderClusters();renderEvidence();renderReasons();renderRoles();renderMap();
async function loadOpenDocumentTopics(){
 let response;
 try{response=await fetch("./data/open_topics.json",{cache:"no-store"});}catch(_){return;}
 if(!response.ok)return; // Dataset appears only after the separate corpus-only workflow validates it.
 let data;
 try{data=await response.json();}catch(_){return;}
 if(data.source_filings_scanned!==3231||data.readable_filings!==3230||!Array.isArray(data.topics)||!data.topics.length)return;
 const list=$("at-open-list"),evidence=$("at-open-evidence"),actions=$("at-open-actions");
 const select=topic=>{
   $("at-open-title").textContent="Full-text topic: "+topic.top_terms.slice(0,3).join(" · ");
   $("at-open-meta").textContent=n(topic.assigned_filings)+" filings assigned by nonexclusive model weights; "+
     n(topic.unique_exact_texts)+" distinct exact-text hashes; "+
     n(topic.filings_with_repeated_exact_text)+" filings in repeated-text families. "+
     "No stance, relevance or coalition is inferred.";
   evidence.replaceChildren();
   const terms=el("p","atlas-basis","Model terms: "+topic.top_terms.join(", "));evidence.append(terms);
   if(topic.largest_filer_name_share>=.5)evidence.append(el("p","atlas-risk","One unverified normalized filer-name field makes up "+
     n(100*topic.largest_filer_name_share)+"% of assigned filings. This is a concentration warning, not evidence of improper coordination."));
   for(const e of topic.illustrative_quotes||[]){
     const article=el("article"),top=el("div");
     top.append(link(e.filer||"FCC filing "+e.id,source(e.id)));
     top.append(el("span","atlas-sub"," · "+String(e.date||"").slice(0,10)+(e.ocr?" · OCR candidate":"")));
     article.append(top,el("blockquote","",e.quote));
     const links=el("div","atlas-linkrow");
     links.append(link("Read extracted source ↗","./corpus.html?id="+encodeURIComponent(e.id)));
     article.append(links);evidence.append(article);
   }
   if(!topic.illustrative_quotes?.length)evidence.append(el("p","atlas-basis","No excerpt satisfied the strict automatic source-selection rule. The topic still has source-linked filing memberships in its overall assignment count; do not infer a position."));
   actions.replaceChildren();
   actions.append(link("Ask the entire corpus about these terms ↗",search(makeQuestion(topic.top_terms.slice(0,5).join(", ")))));
 };
 const topics=[...data.topics].sort((a,b)=>b.assigned_filings-a.assigned_filings);
 list.replaceChildren();
 topics.forEach(topic=>{
   const button=el("button","atlas-cluster");button.type="button";
   button.append(el("h3","",topic.top_terms.slice(0,3).join(" · ")),el("div","atlas-count",n(topic.assigned_filings)),
     el("p","","assigned filing records · "+n(topic.unique_exact_texts)+" distinct exact-texts"));
   if(topic.largest_filer_name_share>=.5)button.append(el("span","atlas-stamp","Source concentration"));
   button.onclick=()=>select(topic);list.append(button);
 });
 $("at-open-status").textContent=n(topics.length)+" automatically inferred topics from "+
  n(data.fit_documents_after_exact_duplicate_and_filer_cap)+" balanced fitting documents; all "+
  n(data.source_filings_scanned)+" filings scanned and scored. Topic count depends on vocabulary structure and model parameters, not the FCC codebook. This layer has not been semantically reviewed.";
 $("open-discovery").hidden=false;select(topics[0]);
}
loadOpenDocumentTopics().catch(err=>{const section=$("open-discovery");if(section&&!section.hidden){$("at-open-status").textContent="Open-document topic data could not be rendered: "+err.message}});
const params=new URLSearchParams(location.search),id=params.get("cluster");
if(id&&clusters.find(x=>x.id===id)){selectedCluster=clusters.find(x=>x.id===id);renderClusters();renderEvidence();}
const reason=params.get("reason");if(reason&&reasons.find(x=>x.id===reason)){selectedReason=reasons.find(x=>x.id===reason);renderReasons();renderRoles();}
})();