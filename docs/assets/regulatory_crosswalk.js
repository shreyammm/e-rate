"use strict";
(async()=>{
const $=id=>document.getElementById(id),fmt=n=>Number(n||0).toLocaleString("en-US");
const make=(tag,cl,s)=>{const e=document.createElement(tag);if(cl)e.className=cl;if(s!==undefined)e.textContent=String(s);return e};
const link=(s,url)=>{const a=make("a","",s);a.href=url;a.rel="noopener noreferrer";a.target="_blank";return a};
const nice=s=>String(s||"").replace(/_/g," ").replace(/\b\w/g,x=>x.toUpperCase());
const q=s=>"./ask.html?q="+encodeURIComponent(s);
const language={
 scope:["continuity_without_sunset","infrastructure_maintenance_and_buildout","ongoing_broadband_costs"],
 funding:["ongoing_broadband_costs","rural_tribal_and_equity"],
 evaluation:["educational_opportunity","screen_health_learning_risks"],
 screens:["screen_health_learning_risks","family_choice_parental_rights","local_instructional_autonomy"],
 cipa:["privacy_free_expression","family_choice_parental_rights","screen_health_learning_risks"],
 consultants:["consultant_incentives_integrity","procurement_administrative_burden"],
 accountability:["consultant_incentives_integrity","procurement_administrative_burden"],
 administration:["procurement_administrative_burden","infrastructure_maintenance_and_buildout"]
};
let rows=[],counts=new Map(),metadata;
try{
const [p,c]=await Promise.all([
 fetch("./data/provisions.json").then(r=>{if(!r.ok)throw Error("Missing regulatory draft");return r.json()}),
 fetch("./data/exhaustive_census.json").then(r=>{if(!r.ok)throw Error("Missing full-corpus census");return r.json()})
]);
if(!Array.isArray(p.provisions)||p.provisions.length!==29||c.coverage.filings!==3231||c.coverage.filing_policy_checks!==29*3231)
 throw Error("Draft regulatory options are inconsistent with corpus population");
rows=p.provisions;counts=new Map(c.provisions.map(x=>[x.id,x]));metadata=c.coverage;
if(rows.some(x=>!counts.has(x.id)))throw Error("Regulatory mention census does not align with codebook");
for(const x of [...new Set(rows.map(x=>x.notice_status))]){
 const o=make("option","",nice(x));o.value=x;$("reg-status").append(o);
}
for(const x of [...new Set(rows.map(x=>x.category))]){
 const o=make("option","",nice(x));o.value=x;$("reg-category").append(o);
}
$("reg-items").textContent=fmt(rows.length);
$("reg-records").textContent=fmt(metadata.filings);
$("reg-checks").textContent=fmt(metadata.filing_policy_checks);
}catch(err){$("reg-status-text").textContent="Unable to verify regulatory crosswalk: "+err.message;return}
function render(){
 const text=$("reg-q").value.toLowerCase().trim(),status=$("reg-status").value,section=$("reg-category").value;
 const selected=rows.filter(x=>(!status||x.notice_status===status)&&(!section||x.category===section)&&
  (!text||[x.label,x.policy_option,x.category,x.id].join(" ").toLowerCase().includes(text)));
 $("reg-status-text").textContent=fmt(selected.length)+" of "+fmt(rows.length)+" analyst-defined regulatory items. All mention counts are filing-language matches; positions are unknown.";
 const host=$("reg-list");host.replaceChildren();
 for(const x of selected){
 const c=counts.get(x.id),card=make("article","reg-item"),head=make("div");
 head.append(make("h3","",x.label));
 head.append(make("span","reg-stamp",nice(x.notice_status)));
 head.append(make("span","reg-stamp",nice(x.category)));
 card.append(head,make("p","",x.policy_option));
 card.append(make("p","reg-meta","FCC notice section paragraphs "+String(x.notice_paragraph_range||"not yet resolved")+" (broad range; exact paragraph not validated)"));
 const stats=make("div","reg-meta");
 stats.append(make("span","reg-count",fmt(c.mentions)));
 stats.append(make("span","","filing records with keyword/phrase matches (not positions)"));
 card.append(stats);
 if(c.agency_type_candidates||c.other_docket_signature){
 card.append(make("p","reg-flags",fmt(c.agency_type_candidates)+" unverified agency-type records · "+fmt(c.other_docket_signature)+" potential cross-docket text flags. These are not automatically excluded."));
 }
 const tools=make("div","reg-questions");
 tools.append(link("Ask all filings about this regulatory question ↗",q("What actual positions and reasons do FCC filers express regarding: "+x.policy_option+"? Include disagreement and original sources.")));
 const lens=language[x.category]||[];
 if(lens.length)tools.append(link("Explore related reason-language lens ↗","./atlas.html?reason="+encodeURIComponent(lens[0])+"#reasoning"));
 card.append(tools);
 host.append(card);
 }
 if(!selected.length)host.append(make("p","reg-sub","No codebook entries match these filters."));
}
$("reg-q").addEventListener("input",render);
$("reg-status").addEventListener("change",render);
$("reg-category").addEventListener("change",render);
render();
})();