'use strict';
(async function(){
  const $=id=>document.getElementById(id);
  const node=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=String(txt);if(cls)e.className=cls;return e};
  const n=x=>Number(x||0).toLocaleString('en-US');
  const source=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(String(id));
  const corpus=id=>'./corpus.html?id='+encodeURIComponent(String(id));
  const link=(txt,url)=>{const a=node('a',txt);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a};
  const lens={
    screen:/(screen[ -]?time|device use|excessive screen|digital exposure|screen use|daily.hour.limit|screen_time_condition)/i,
    benefits:/(educational outcome|education_outcomes|learning (?:benefit|opportunit|outcome)|academic (?:improv|benefit)|accessib|assistive tech|personalized learning|digital (?:literacy|learning)|instructional technolog)/i,
    consultants:/(consultant|form 5654|percentage.based fee|registration|compliance|bid process|consultant_)/i,
    conditions:/(screen_time_condition|erate_eligibility_scope|cipa_|parent_opt_out|eligibility|federal condition|filtering requirement|digital literacy)/i,
    misuse:/(misus|alleged fraud|procurement (?:fraud|abuse)|waste|improper payment|program integrity|oversight|fraud|vendor_influence)/i,
    funding:/(erate_sunset|erate_eligibility_scope|sunset|cut|continuation|preserv|end (?:e.?rate|the program)|funding)/i
  };
  let data=null, claims=null, filteredReview=[],reviewPage=0, claimPage=0, candidates=[], changes=new Map(), selectedOrg=null;
  const group=r=>{
    if(['school_district','individual_school','school_technology_staff','school_educator','school_administrator','school_connected_unknown'].includes(r.role))return 'school';
    if(r.role.startsWith('edtech_'))return 'edtech';
    if(r.industry_focus==='edtech_industry')return 'edtech_industry';
    if(r.industry_focus==='telecom_industry')return 'telecom';
    if(r.industry_focus==='erate_consulting')return 'consultant';
    if(['telecom_isp','network_technology_vendor'].includes(r.role))return 'telecom';
    if(['erate_consultant','procurement_adviser'].includes(r.role))return 'consultant';
    if(['library_institution','library_staff'].includes(r.role))return 'library';
    if(r.role==='parent_guardian')return 'parent';
    return 'other';
  };
  const groupNames={school:'Schools and educators',edtech:'Edtech companies',edtech_industry:'Edtech industry associations',telecom:'Telecom and networking',consultant:'Consultants and advisers',library:'Libraries',parent:'Parents and caregivers',other:'Others / unresolved'};
  const byFiling=new Map();
  function stats(){
    const p=data.coverage;
    const vals=[['Filing records',p.filings],['Recognized institutional names',p.named_organizations],['Identity reviews needed',p.filings_requiring_identity_review],['Human-reviewed identity records',p.manually_reviewed_filings]];
    $('ps-stats').replaceChildren(...vals.map(([label,v])=>{const x=node('div',undefined,'ps-stat');x.append(node('strong',n(v)),node('span',label,'ps-small'));return x}));
    const holder=$('ps-roles');holder.replaceChildren();
    const t=node('table',undefined,'ps-table');t.appendChild(node('thead'));let h=node('tr');h.append(node('th','Candidate role'),node('th','Filing records'));t.tHead.append(h);
    const tb=node('tbody');
    for(const [role,count] of Object.entries(data.role_filing_counts).sort((a,b)=>b[1]-a[1])){
      let tr=node('tr');tr.append(node('td',data.roles[role]||role),node('td',n(count)));tb.append(tr);
    }
    t.append(tb);holder.append(t);
  }
  function initSelects(){
    const rs=Object.entries(data.roles).sort((a,b)=>a[1].localeCompare(b[1]));
    for(const [k,v] of rs){
      $('ps-org-role').append(new Option(v,k));
      $('ps-review-role').append(new Option(v,k));
    }
  }
  function displayOrgs(){
    const q=$('ps-org-query').value.trim().toLowerCase(),r=$('ps-org-role').value;
    let rows=data.organizations.filter(o=>(!q||o.name.toLowerCase().includes(q))&&(!r||Object.prototype.hasOwnProperty.call(o.role_candidates,r)));
    $('ps-org-summary').textContent=n(rows.length)+' names match; first 120 shown. A named entity is not a verified organization-level political position.';
    const body=$('ps-org-table');body.replaceChildren();
    for(const o of rows.slice(0,120)){
      let tr=node('tr');let c=node('td');
      let btn=node('button',o.name);btn.type='button';btn.style.cssText='border:0;background:transparent;color:#13537e;cursor:pointer;text-align:left;text-decoration:underline;padding:0';btn.addEventListener('click',()=>detailOrg(o));c.append(btn);
      let src=node('td');for(let id of o.filing_ids.slice(0,3)){src.append(link(id,source(id)),document.createTextNode(' '))}
      tr.append(c,node('td',n(o.filings)),node('td',n(o.distinct_source_texts)),src);body.append(tr);
    }
  }
  function detailOrg(o){
    const box=$('ps-org-detail');box.hidden=false;box.replaceChildren(node('strong',o.name));
    box.append(node('p',n(o.filings)+' filing records · '+n(o.distinct_source_texts)+' distinct texts. Candidate roles: '+Object.entries(o.role_candidates).map(([r,n])=>(data.roles[r]||r)+' ('+n+')').join('; '),'ps-muted'));
    if(o.disagreement_on_type)box.append(node('p','Conflicting candidate roles across filings: investigate before aggregating an institutional position.','ps-muted'));
    for(let id of o.filing_ids.slice(0,20))box.append(link('FCC '+id,source(id)),document.createTextNode(' · '));
    if(o.filing_ids.length>20)box.append(node('p','Additional filings available through the full corpus explorer.','ps-muted'));
    const explore=node('button','Explore this institution\'s machine-extracted claims');
    explore.type='button';explore.style.cssText='display:block;margin:12px 0;padding:9px 13px;border:1px solid #7b9bb0;color:#12496e;background:#eef5f9;cursor:pointer';
    explore.addEventListener('click',async()=>{
      selectedOrg=o;
      if(!claims)await loadClaims();
      if(!claims)return;
      $('ps-sector').value='';$('ps-claim-query').value='';
      displayClaims();
      $('ps-claims-panel').scrollIntoView({behavior:'smooth',block:'start'});
    });
    box.append(explore);
  }
  function refreshReview(){
    let q=$('ps-review-query').value.trim().toLowerCase(),role=$('ps-review-role').value;
    filteredReview=data.filings.filter(r=>r.needs_review&&(!role||r.role===role)&&(!q||[r.id,r.organization,r.role].join(' ').toLowerCase().includes(q)));
    filteredReview.sort((a,b)=>(b.review_priority||0)-(a.review_priority||0)||String(a.id).localeCompare(String(b.id)));
    reviewPage=0;displayReview();
  }
  function displayReview(){
    $('ps-review-count').textContent=n(filteredReview.length)+' cases in the current review queue; '+n(changes.size)+' proposed decisions in this browser session.';
    const box=$('ps-review-list');box.replaceChildren();
    for(const r of filteredReview.slice(0,(reviewPage+1)*25)){
      const x=node('div',undefined,'ps-review');
      x.append(link('FCC filing '+r.id,source(r.id)),node('span',' · '+(data.roles[r.role]||r.role),'ps-chip'));
      x.append(node('span','Priority: '+(r.review_tier||'unranked')+' ('+(r.review_priority||0)+')','ps-chip'));
      if(r.organization)x.append(node('p','Source metadata institution or possible affiliation: '+r.organization,'ps-muted'));
      if(r.review_reasons?.length)x.append(node('p','Review leads: '+r.review_reasons.join('; '),'ps-small'));
      x.append(node('p','Basis: '+r.basis+'; possible representative/client attribution: '+(r.proxy_possible?'yes—verify':'not detected')+'. Open the source and check letterhead, opening, signatory and capacity.','ps-small'));
      if(r.evidence_cue)x.append(node('p','Source cue (not an independently validated affiliation): '+r.evidence_cue,'ps-small'));
      let form=node('div',undefined,'ps-controls'),select=node('select'),opt=new Option('— choose reviewed capacity —','');select.add(opt);
      for(let [k,v] of Object.entries(data.roles))select.add(new Option(v,k));
      const existing=changes.get(r.id);if(existing)select.value=existing.role;
      const input=node('input');input.placeholder='Paste an EXACT supporting excerpt from the FCC filing (minimum 12 characters)';
      input.setAttribute('aria-label','Original evidence quotation for '+r.id);if(existing)input.value=existing.evidence_quote;
      const org=node('input');org.placeholder='Organization name, only if explicitly documented (optional)';org.setAttribute('aria-label','Reviewed organization for '+r.id);if(existing)org.value=existing.organization;
      const save=node('button','Record review proposal');save.type='button';
      const message=node('span','','ps-small');
      save.addEventListener('click',()=>{
        if(!select.value||input.value.trim().length<12){message.textContent='Select capacity and paste exact evidence before saving.';return;}
        changes.set(r.id,{role:select.value,organization:org.value.trim(),evidence_quote:input.value.trim(),review_status:'human_reviewed'});
        message.textContent='Saved locally for export. Original-source match will be verified on import.';
        $('ps-review-count').textContent=n(filteredReview.length)+' queued; '+n(changes.size)+' decisions proposed.';
      });
      form.append(select,input,org,save,message);x.append(form);box.append(x);
    }
    $('ps-more-review').hidden=(reviewPage+1)*25>=filteredReview.length;
  }
  function exportReviews(){
    if(!changes.size){$('ps-export-status').textContent='No reviewed decisions have been recorded yet.';return;}
    const payload=JSON.stringify(Object.fromEntries(changes),null,2)+'\n';
    const obj=URL.createObjectURL(new Blob([payload],{type:'application/json'}));
    const a=node('a');a.href=obj;a.download='player_review_proposals.json';a.click();
    setTimeout(()=>URL.revokeObjectURL(obj),1500);
    $('ps-export-status').textContent=n(changes.size)+' evidence-required proposed decisions exported. Changes are not live until the source-validating build.';
  }
  function matchesLens(r){
    const hay=[r.issue,r.argument,r.action,r.reason_family,r.quote].join(' ');
    return lens[$('ps-lens').value].test(hay);
  }
  function displayClaims(){
    if(!claims)return;
    const sector=$('ps-sector').value, query=$('ps-claim-query').value.trim().toLowerCase();
    const selectedFilingIds=selectedOrg?new Set(selectedOrg.filing_ids):null;
    const notice=$('ps-org-active');
    notice.hidden=!selectedOrg;
    if(selectedOrg)$('ps-org-active-label').textContent='Institution profile: '+selectedOrg.name+' · '+n(selectedOrg.filings)+' original filing records';
    candidates=claims.rows.filter(r=>{
      if(selectedFilingIds&&!selectedFilingIds.has(String(r.id)))return false;
      if(!matchesLens(r))return false;
      const identity=byFiling.get(String(r.id));
      if(sector&&group(identity||{role:'unresolved'})!==sector)return false;
      if(query&&![r.argument,r.action,r.quote,r.organization,r.issue,r.reason_family].join(' ').toLowerCase().includes(query))return false;
      return true;
    });
    const groups=new Map();
    for(const r of candidates){
      const g=group(byFiling.get(String(r.id))||{role:'unresolved'});
      if(!groups.has(g))groups.set(g,new Set());
      groups.get(g).add(String(r.id));
    }
    $('ps-claim-count').textContent=n(candidates.length)+' machine-extracted claim rows from '+n(new Set(candidates.map(r=>r.id)).size)+' distinct filing IDs under this lens. Some claims may be misattributed or incomplete.';
    const cards=$('ps-claim-summary');cards.replaceChildren();
    for(let [k,v] of Object.entries(groupNames)){
      const c=node('div',undefined,'ps-stat');
      c.append(node('strong',n(groups.get(k)?.size||0)),node('span',v+' · filing IDs with candidate claims','ps-small'));
      cards.append(c);
    }
    claimPage=0;drawClaimRows();
  }
  function drawClaimRows(){
    const out=$('ps-claim-list');out.replaceChildren();
    for(const r of candidates.slice(0,(claimPage+1)*25)){
      const id=String(r.id),info=byFiling.get(id),box=node('article',undefined,'ps-row');
      const heading=node('div');heading.append(link('FCC '+id,source(id)),node('span',' · '+(groupNames[group(info||{role:'unresolved'})]||'Unknown'),'ps-chip'));
      if(info?.organization)heading.append(node('span',info.organization,'ps-chip'));
      heading.append(node('span',r.issue+' · '+(r.position||'unclear')+' (machine ONLY)','ps-chip'));
      box.append(heading,node('strong',r.action||r.argument||'Claim identified without a distinct requested action'));
      if(r.argument&&r.action!==r.argument)box.append(node('p',r.argument));
      if(r.quote)box.append(node('blockquote',r.quote));
      box.append(link('Inspect the original source ↗',corpus(id)),document.createTextNode(' · '));
      const ask=node('a','Investigate counterevidence ↗');ask.href='./ask.html?q='+encodeURIComponent('What evidence supports or challenges this FCC filing claim: '+String(r.argument||r.action||'').slice(0,170)+'? Search the full corpus, cite original filings, and distinguish attributed arguments from external verified facts.');box.append(ask);
      if(info?.proxy_possible)box.append(node('p','Possible intermediary submission: representative/client distinction needs manual inspection.','ps-small'));
      out.append(box);
    }
    $('ps-more-claims').hidden=(claimPage+1)*25>=candidates.length;
  }
  async function loadClaims(){
    $('ps-load-claims').disabled=true;
    $('ps-claim-count').textContent='Loading the separately published Kaggle claim ledger…';
    try{
      const r=await fetch('./data/kaggle/machine_claim_rows.json');
      if(!r.ok)throw Error('Kaggle claim index unavailable (HTTP '+r.status+')');
      const j=await r.json();
      if(!Array.isArray(j.rows)||Number(j.source_filings)!==3231||!j.rows.every(row=>/^\d{8,20}$/.test(String(row.id))))throw Error('Invalid source-linked claim index');
      claims=j;
      $('ps-load-claims').hidden=true;
      displayClaims();
    }catch(e){
      $('ps-load-claims').disabled=false;
      $('ps-claim-count').textContent='Claim comparison unavailable: '+e.message+'. The player registry and original FCC filing links remain usable.';
    }
  }
  try{
    const res=await fetch('./data/player_registry.json');
    if(!res.ok)throw Error('The source-player index has not yet been generated by GitHub Actions');
    const j=await res.json();
    if(j.schema_version!=='player-registry-v1'||!Array.isArray(j.filings)||j.filings.length!==3231||
       new Set(j.filings.map(r=>r.id)).size!==3231)throw Error('Player index integrity check failed');
    data=j;for(let r of data.filings)byFiling.set(r.id,r);
    $('ps-status').textContent='Source-aligned registry: '+n(j.coverage.filings)+' filing records · '+n(j.coverage.filings_requiring_identity_review)+' identity cases still require review. All categories are provisional except recorded human reviews.';
    stats();initSelects();displayOrgs();refreshReview();
  }catch(err){
    $('ps-status').textContent='Player registry not yet available: '+err.message+'. Original filings and the existing Atlas remain available.';
    for(let x of ['ps-org-table','ps-review-list','ps-roles'])$(x).textContent='Player registry publication pending.';
    return;
  }
  $('ps-clear-organization').addEventListener('click',()=>{selectedOrg=null;displayClaims();});
  $('ps-org-query').addEventListener('input',displayOrgs);$('ps-org-role').addEventListener('change',displayOrgs);
  $('ps-review-query').addEventListener('input',refreshReview);$('ps-review-role').addEventListener('change',refreshReview);
  $('ps-more-review').addEventListener('click',()=>{reviewPage++;displayReview()});
  $('ps-export').addEventListener('click',exportReviews);
  $('ps-load-claims').addEventListener('click',loadClaims);
  $('ps-more-claims').addEventListener('click',()=>{claimPage++;drawClaimRows()});
  $('ps-lens').addEventListener('change',displayClaims);$('ps-sector').addEventListener('change',displayClaims);
  $('ps-claim-query').addEventListener('input',displayClaims);
})();
