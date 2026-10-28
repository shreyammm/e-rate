'use strict';
(async function(){
  const $=id=>document.getElementById(id);
  const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e;};
  const fmt=n=>Number(n||0).toLocaleString('en-US');
  const fcc=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(id);
  const corpus=id=>'./corpus.html?id='+encodeURIComponent(id);
  const link=(text,url)=>{const a=make('a',text);a.href=url;if(/^https:/.test(url)){a.target='_blank';a.rel='noopener noreferrer';}return a;};
  const themes={
    benefits:{title:'Educational benefit, outcomes and accessibility',rx:/(?:academic|achievement|learning (?:benefit|outcome|opportunit)|student (?:learning|outcome)|accessib|assistive|individualiz|personaliz|digital (?:literacy|learning)|instructional technolog|educational technolog|educational opportunit)/i},
    screen:{title:'Screen time and developmental concerns',rx:/(?:screen[\s-]?time|screen[\s-]?based|excessive screen|screens? (?:use|exposure)|device use|device time|mental health|developmental (?:harm|effect|risk)|screen_time_condition)/i},
    consultants:{title:'Consultant registration, pay and compliance',rx:/(?:consultant|consulting|form 5654|percentage[\s-]?based|contingenc|procurement adviser|professional fees|registration|competitive bidd?ing|compensation)/i},
    procurement:{title:'Vendor influence and procurement',rx:/(?:vendor.?influenc|vendor.?driven|edtech procurement|competitive bidd?ing|procurement|vendor (?:incentiv|control|pressure|interest)|contracting|vendor_influence|conflict of interest)/i},
    misuse:{title:'Misuse allegations and program integrity',rx:/(?:alleged (?:fraud|misuse)|\bmisus\w*|\bfraud\b|improper payment|ineligible spending|oversight|program integrity|waste and abuse|overbilling|kickback)/i},
    conditions:{title:'Funding conditions, CIPA and parent choice',rx:/(?:screen_time_condition|erate_eligibility_scope|parent_opt_out|opt[\s-]?out|funding condition|eligibility restriction|cipa_|parental consent|filtering|protective safeguard)/i},
    funding:{title:'E-Rate funding and continuity',rx:/(?:erate_sunset|funding cut|eliminat(?:e|ion) (?:e[\s-]?rate|fund)|sunset|maintain (?:e[\s-]?rate|fund)|preserv(?:e|ing) (?:e[\s-]?rate|fund)|program continuity|erate_eligibility_scope)/i}
  };
  const lensOrder=['benefits','screen','consultants','procurement','misuse','conditions','funding'];
  const sectors=[
    ['school','School/district/educator'],
    ['edtech_industry','Edtech-industry organizations'],
    ['consultants','E-Rate consulting industry'],
    ['telecom','Telecom/networking'],
    ['other','Other and unresolved']
  ];
  let registry=null,ledger=null,quality={},audit={},auditVerified=false, filingMap=new Map(),rows=[],selection=[],shown=0, topic='all';
  const id=r=>String(r.id||'');
  const filing=r=>filingMap.get(id(r))||{role:'unresolved',industry_focus:'unspecified'};
  const sector=r=>{
    const x=filing(r),role=x.role||'',industry=x.industry_focus||'';
    if(industry==='edtech_industry'||role.startsWith('edtech_'))return 'edtech_industry';
    if(industry==='erate_consulting'||role==='erate_consultant'||role==='procurement_adviser')return 'consultants';
    if(industry==='telecom_industry'||role==='telecom_isp'||role==='network_technology_vendor')return 'telecom';
    if(role.startsWith('school_')||role==='individual_school')return 'school';
    if(role==='library_institution'||role==='library_staff')return 'library';
    if(role==='parent_guardian')return 'parent';
    return 'other';
  };
  function matchGroup(r,g){
    if(!g)return true;
    if(g==='edtech_vendor')return filing(r).role.startsWith('edtech_');
    if(g==='edtech_industry')return sector(r)==='edtech_industry';
    return sector(r)===g;
  }
  function textOf(r){return [r.issue,r.reason_family,r.claim_kind,r.argument,r.action,r.quote].join(' ');}
  function rowTheme(r,l){return l==='all'||themes[l].rx.test(textOf(r));}
  function flags(r){
    const q=quality[id(r)]||{},notes=[];
    if(id(r)==='26110081266')notes.push('NTIA reports listening-session views; not an agency endorsement');
    if(q.semantic_scope&&q.semantic_scope!=='full_text')notes.push('Only some original text windows model-read');
    if(q.ocr_candidate||r.ocr_candidate)notes.push('OCR not independently reviewed');
    if(r.issue==='erate_sunset'&&(q.suspected_sunset_polarity_claim_indices||[]).length)notes.push('Possible reversed machine position');
    if(auditVerified)for(const f of (audit[String(r.ledger_index)]||[])){
      if(['possible_attributed_or_opposing_voice','fcc_prompt_or_policy_question_near_quote','possible_bibliography_or_cited_material','low_lexical_overlap_between_quote_and_machine_paraphrase'].includes(f))notes.push('Context review: '+f.replace(/_/g,' '));
    }
    return notes;
  }
  function needReview(r){return flags(r).length>0||filing(r).needs_review;}
  function exportCsv(){
    const headers=['filing_id','organization_metadata_candidate','provisional_role','industry_focus','machine_issue','machine_position_unvalidated','machine_action','machine_argument','verbatim_source_quote','source_url','source_and_identity_cautions'];
    function quote(x){
      let v=String(x??'');
      // Avoid spreadsheet formula evaluation of arbitrary source text on open.
      if(/^[\s]*[=+@-]/.test(v))v="'"+v;
      return '"'+v.replace(/"/g,'""')+'"';
    }
    const out=[headers.map(quote).join(',')];
    for(const r of selection){
      const f=filing(r);
      const warnings=flags(r).concat(f.needs_review?['Provisional commenter identity requires source review']:[]);
      out.push([id(r),f.organization||'',f.role||'unresolved',f.industry_focus||'unspecified',r.issue||'',r.position||'',r.action||'',r.argument||'',r.quote||'',fcc(id(r)),warnings.join('; ')].map(quote).join(','));
    }
    const blob=new Blob(['\ufeff'+out.join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=make('a');
    a.href=url;a.download='erate_source_claim_candidates_'+topic+'.csv';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('br-export-status').textContent=fmt(selection.length)+' unvalidated machine claim rows exported, with original filing links and caution flags.';
  }
  function controls(){
    let p=new URLSearchParams(location.search);
    const q=p.get('lens'),g=p.get('group');
    topic=themes[q]?q:'all';
    $('br-lens').value=topic;
    if(['school','edtech_industry','edtech_vendor','consultants','telecom','library','parent','other'].includes(g))$('br-group').value=g;
    for(const btn of document.querySelectorAll('[data-topic]'))btn.addEventListener('click',()=>{
      $('br-lens').value=btn.dataset.topic;topic=btn.dataset.topic;recalc();
      $('br-lens').scrollIntoView({block:'center',behavior:'smooth'});
    });
    for(const i of ['br-lens','br-group','br-quality'])$(i).addEventListener('change',recalc);
    $('br-query').addEventListener('input',recalc);
    $('br-more').addEventListener('click',()=>{shown+=30;renderEvidence();});
    $('br-export').addEventListener('click',exportCsv);
  }
  function syncTopic(){
    topic=$('br-lens').value;
    for(const btn of document.querySelectorAll('[data-topic]'))btn.setAttribute('aria-pressed',String(btn.dataset.topic===topic));
  }
  function recalc(){
    syncTopic();
    const g=$('br-group').value,q=$('br-query').value.trim().toLowerCase(),qa=$('br-quality').value;
    selection=rows.filter(r=>{
      if(!rowTheme(r,topic)||!matchGroup(r,g))return false;
      const f=filing(r);
      if(q&&!([f.organization,r.issue,r.action,r.argument,r.quote,r.reason_family,id(r)].join(' ').toLowerCase().includes(q)))return false;
      if(qa==='full'&&quality[id(r)]?.semantic_scope!=='full_text')return false;
      if(qa==='caution'&&!needReview(r))return false;
      return true;
    });
    const ids=new Set(selection.map(id)),orgs=new Set(selection.map(r=>filing(r).organization).filter(Boolean));
    const reviewed=selection.filter(needReview).length;
    const tiles=[
      ['Candidate machine claim rows',selection.length],
      ['Distinct filing IDs',ids.size],
      ['Identifiable institutions in results',orgs.size],
      ['Rows with any source/identity caution',reviewed]
    ];
    $('br-stats').replaceChildren(...tiles.map(([label,value])=>{let d=make('div',undefined,'b-stat');d.append(make('strong',fmt(value)),make('span',label));return d;}));
    renderMatrix();renderOrganizations();shown=30;renderEvidence();
  }
  function renderMatrix(){
    const t=$('br-matrix');t.replaceChildren();
    const scope=rows.filter(r=>matchGroup(r,$('br-group').value));
    const q=$('br-query').value.trim().toLowerCase(),qa=$('br-quality').value;
    for(const [key,detail] of Object.entries(themes)){
      if(topic!=='all'&&topic!==key)continue;
      const subset=scope.filter(r=>{
        if(!rowTheme(r,key))return false;
        if(q&&!([filing(r).organization,r.issue,r.action,r.argument,r.quote,r.reason_family,id(r)].join(' ').toLowerCase().includes(q)))return false;
        if(qa==='full'&&quality[id(r)]?.semantic_scope!=='full_text')return false;
        if(qa==='caution'&&!needReview(r))return false;
        return true;
      });
      const tr=make('tr');tr.append(make('td',detail.title));
      for(const [g] of sectors){
        const ids=new Set(subset.filter(r=>sector(r)===g).map(id));
        tr.append(make('td',fmt(ids.size)));
      }
      t.append(tr);
    }
  }
  function renderOrganizations(){
    const t=$('br-orgs');t.replaceChildren();
    let counts=new Map(),idsByOrg=new Map();
    for(const r of selection){
      const f=filing(r);if(!f.organization)continue;
      if(!idsByOrg.has(f.organization))idsByOrg.set(f.organization,new Set());
      idsByOrg.get(f.organization).add(id(r));
    }
    for(const [name,ids] of idsByOrg){
      const a=registry.organizations.find(x=>x.name===name);
      const selected=Array.from(ids),hashes=new Set(selected.map(x=>filingMap.get(x).text_sha256).filter(Boolean));
      counts.set(name,{name,ids:selected,unique:hashes.size,meta:a});
    }
    const sorted=Array.from(counts.values()).sort((a,b)=>b.ids.length-a.ids.length||a.name.localeCompare(b.name));
    $('br-org-note').textContent=fmt(sorted.length)+' named institutional candidates. Listings reflect FCC submitter metadata; a participant may be a client, co-signer or representative. Open sources to verify.';
    for(const o of sorted.slice(0,100)){
      const f=filingMap.get(o.ids[0])||{},tr=make('tr');
      const name=make('td'),b=make('button',o.name);
      b.addEventListener('click',()=>{$('br-query').value=o.name;recalc();$('br-evidence').scrollIntoView({block:'start',behavior:'smooth'});});
      name.append(b);
      tr.append(name,make('td',(registry.roles[f.role]||f.role)+' · '+String(f.industry_focus||'unspecified').replace(/_/g,' ')),
        make('td',fmt(o.ids.length)),make('td',fmt(o.unique)));
      const links=make('td');
      for(const fid of o.ids.slice(0,3)){links.append(link('FCC '+fid,fcc(fid)),document.createTextNode(' '));}
      tr.append(links);t.append(tr);
    }
  }
  function balancedRows(){
    const sorted=selection.slice().sort((a,b)=>{
      const aa=needReview(a)?1:0,bb=needReview(b)?1:0;
      if(aa!==bb)return aa-bb;
      const fa=filing(a),fb=filing(b);
      const na=Number(!fa.organization),nb=Number(!fb.organization);
      if(na!==nb)return na-nb;
      return id(a).localeCompare(id(b));
    });
    const used=new Set(),out=[];
    for(const r of sorted){
      if(used.has(id(r)))continue;
      used.add(id(r));out.push(r);
    }
    return out;
  }
  function renderEvidence(){
    const out=$('br-evidence');out.replaceChildren();
    const exemplars=balancedRows();
    const shownRows=exemplars.slice(0,shown);
    $('br-evidence-note').textContent=fmt(exemplars.length)+' source filings with machine-extracted arguments under the current lens; showing '+fmt(shownRows.length)+'. One illustrative machine claim per filing is shown initially. Follow original links to see the full submission and other claims.';
    for(const r of shownRows){
      const f=filing(r),who=f.organization||registry.roles[f.role]||'Attribution unresolved';
      const a=make('article',undefined,'b-evidence'),head=make('div',undefined,'b-tags');
      head.append(make('span',who,'b-tag'),
        make('span',String(r.issue||'other_policy_issue').replace(/_/g,' '),'b-tag'),
        make('span','Model direction: '+String(r.position||'unclear'),'b-tag'));
      const issues=flags(r);
      if(f.basis==='multi_party_metadata_affiliation_candidate')issues.push('Organization inferred from two-party metadata; confirm represented client');
      if(f.proxy_possible)issues.push('Possible intermediary filing; confirm whose opinion this represents');
      if(f.needs_review)issues.push('Speaker identity needs verification');
      for(const issue of issues)head.append(make('span',issue,'b-tag b-risk'));
      const h=make('h3',r.action||r.argument||'Machine-identified passage with no clear action');
      a.append(head,h);
      if(r.argument&&r.argument!==r.action)a.append(make('p',r.argument,'b-note'));
      if(r.quote)a.append(make('blockquote',r.quote));
      const links=make('div',undefined,'b-buttons');
      links.append(link('FCC '+id(r),fcc(id(r))),link('Read extracted full text',corpus(id(r))));
      const next=link('Evaluate claim & attribution','./claims-to-check.html');
      links.append(next);
      const ask=link('Ask about competing arguments','./ask.html?q='+encodeURIComponent('Identify evidence supporting and disputing this FCC comment claim and identify each speaker: '+String(r.action||r.argument||'').slice(0,180)));
      links.append(ask);a.append(links);out.append(a);
    }
    $('br-more').hidden=shown>=exemplars.length;
  }
  try{
    controls();
    // Verify all three datasets refer to the same number of original source records.
    const requests=['./data/player_registry.json','./data/kaggle/machine_claim_rows.json','./data/kaggle/filing_quality.json','./data/kaggle/claim_context_audit.json'];
    const res=await Promise.all(requests.map(x=>fetch(x)));
    for(let i=0;i<res.length;i++)if(!res[i].ok)throw Error('Required research dataset '+requests[i]+' HTTP '+res[i].status);
    const [reg,raw,q,au]=await Promise.all([res[0].json(),res[1].text(),res[2].json(),res[3].json()]);
    const ledgerJson=JSON.parse(raw);
    if(reg.schema_version!=='player-registry-v1'||reg.filings.length!==3231||
       ledgerJson.source_filings!==3231||!Array.isArray(ledgerJson.rows)||
       q.coverage.processed_readable_filings!==3230)throw Error('FCC source snapshot consistency check failed');
    registry=reg;ledger=ledgerJson;quality=q.filings||{};
    for(const f of registry.filings)filingMap.set(String(f.id),f);
    rows=ledger.rows.map((x,i)=>({...x,ledger_index:i}));
    if(window.crypto?.subtle){
      const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(raw));
      const hash=Array.from(new Uint8Array(digest)).map(x=>x.toString(16).padStart(2,'0')).join('');
      if(hash===au.machine_claim_ledger_sha256&&au.coverage.machine_claim_rows_checked===rows.length){
        auditVerified=true;audit=au.flags_by_ledger_row_index||{};
      }
    }
    $('br-status').textContent='Loaded '+fmt(rows.length)+' source-linked machine claim candidates across '+fmt(reg.coverage.filings)+' FCC filings; '+fmt(reg.coverage.filings_requiring_identity_review)+' identities require review. '+(auditVerified?'Machine claim context-warning ledger verified.':'Context audit not matched to this machine ledger; attribution remains unverified.');
    recalc();
  }catch(e){
    $('br-status').textContent='Briefing unavailable: '+e.message+'. Use the original source-text reader and Argument Atlas while this publication is repaired.';
    $('br-status').classList.add('b-error');
    $('br-more').hidden=true;
  }
})();