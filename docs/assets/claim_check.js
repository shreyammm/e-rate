'use strict';
(async()=>{
  const $=id=>document.getElementById(id);
  const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=String(text);if(cls)e.className=cls;return e};
  const n=x=>Number(x||0).toLocaleString('en-US');
  const href=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(String(id));
  const link=(txt,url)=>{let a=el('a',txt);a.href=url;a.rel='noopener noreferrer';a.target='_blank';return a};
  const labels={school:'Schools and educators',edtech:'Edtech vendors',telecom:'Telecom and networking',consultants:'Consultants',library:'Libraries',other:'Other / uncertain'};
  const themes={
    screen:/(screen[\s-]?time|device use|screen use|digital exposure|daily.hour.limit|screen_time_condition)/i,
    benefits:/(education_outcomes|educational outcome|student achievement|instructional technol|academic performance|assistive|accessibility|learning benefit|digital literacy|personalized learning|screen use)/i,
    consultants:/(consultant|consulting|form 5654|percentage.based|competitive bidding|procurement|compliance|registration)/i,
    misuse:/(misuse|misappropriat|fraud|waste|improper payment|program integrity|overbilling|oversight|abuse|ineligible expense)/i,
    funding:/(erate_sunset|erate_eligibility_scope|sunset|eliminat|fund|discount|conditions|eligib|preserv|reducing e.?rate)/i,
    all:/./
  };
  const reviews=new Map();let all=[],filtered=[],quality={},filings={},shown=0;
  function group(role){
    if(/^(school_|individual_school)/.test(role))return 'school';
    if(role.startsWith('edtech_'))return 'edtech';
    if(['telecom_isp','network_technology_vendor'].includes(role))return 'telecom';
    if(['erate_consultant','procurement_adviser'].includes(role))return 'consultants';
    if(['library_institution','library_staff'].includes(role))return 'library';
    return 'other';
  }
  function key(r){return [r.id,r.issue,r.start,String(r.argument||r.action||'').slice(0,160)].join('::')}
  function qualityFor(r){return quality[String(r.id)]||{}}
  function flags(r){
    let f=qualityFor(r),a=[];
    if(f.semantic_scope&&f.semantic_scope!=='full_text')a.push('Only selected source windows model-read');
    if(Array.isArray(f.suspected_sunset_polarity_claim_indices)&&f.suspected_sunset_polarity_claim_indices.length&&r.issue==='erate_sunset')a.push('Potential reversal of sunset support/oppose direction');
    if(f.ocr_candidate||r.ocr_candidate)a.push('OCR requires source inspection');
    if(!f.semantic_scope)a.push('No available per-filing model-quality record');
    return a;
  }
  function refresh(){
    const topic=$('cf-topic').value,who=$('cf-group').value,q=$('cf-query').value.trim().toLowerCase(),s=$('cf-status-filter').value;
    filtered=all.filter(r=>{
      const body=[r.issue,r.argument,r.action,r.quote,r.reason_family,r.claim_kind,r.organization].join(' ');
      if(!themes[topic].test(body))return false;
      if(who&&group(filings[String(r.id)]?.role||'unresolved')!==who)return false;
      if(q&&!body.toLowerCase().includes(q)&&!String(r.id).includes(q))return false;
      if(s==='unreviewed'&&reviews.has(key(r)))return false;
      if(s==='reviewed'&&!reviews.has(key(r)))return false;
      if(s==='partial'&&qualityFor(r).semantic_scope==='full_text')return false;
      if(s==='polarity'&&!flags(r).some(x=>x.includes('reversal')))return false;
      return true;
    });
    const ids=new Set(filtered.map(r=>String(r.id)));
    $('cf-result-count').textContent=n(filtered.length)+' unreviewed-machine claim rows in '+n(ids.size)+' distinct filing records; counts are neither unique speakers nor validated positions.';
    $('cf-metrics').replaceChildren(...[
      ['Candidate claim rows',filtered.length],['Distinct source filings',ids.size],
      ['Manual review decisions',reviews.size]
    ].map(([label,val])=>{let c=el('div',undefined,'cf-metric');c.append(el('strong',n(val)),el('span',label,'cf-small'));return c}));
    shown=0; $('cf-list').replaceChildren(); addRows();
  }
  function addRows(){
    const slice=filtered.slice(shown,shown+25);
    for(const r of slice){
      const id=String(r.id),info=filings[id]||{},box=el('article',undefined,'cf-card'),reviewKey=key(r);
      const top=el('div',undefined,'cf-meta');
      top.append(el('span',info.organization||labels[group(info.role||'unresolved')],'cf-tag'),
                 el('span',String(r.issue||'other_policy_issue').replace(/_/g,' '),'cf-tag'),
                 el('span','Machine position: '+String(r.position||'unclear'),'cf-tag'));
      for(const f of flags(r))top.append(el('span',f,'cf-tag'));
      box.append(top,el('h3',r.action||r.argument||'Source text without extracted requested action'));
      if(r.argument&&r.action!==r.argument)box.append(el('p',r.argument,'cf-small'));
      if(r.quote)box.append(el('blockquote',r.quote));
      const links=el('div',undefined,'cf-buttons');
      links.append(link('Original FCC filing ↗',href(id)),link('Full text in corpus ↗','./corpus.html?id='+encodeURIComponent(id)));
      let counter=el('a','Search competing evidence ↗');counter.href='./ask.html?q='+encodeURIComponent('What FCC comments offer evidence supporting or challenging the following claim: '+String(r.argument||r.action||'').slice(0,200)+'? Identify speakers and exact original filing sources.');
      links.append(counter);box.append(links);
      const toggle=el('button',reviews.has(reviewKey)?'Edit saved assessment':'Assess this claim');
      toggle.type='button';toggle.style.cssText='border:1px solid #6b97b2;background:#f2f8fa;color:#164c6a;border-radius:4px;padding:8px 12px;cursor:pointer';
      box.append(toggle);
      const form=el('div',undefined,'cf-review');form.hidden=true;
      const select=el('select');for(const [v,t] of [
        ['','Choose provisional evidence assessment'],['supported','Supported by independently checked evidence'],['partly_supported','Partly supported or important limitations'],['contradicted','Contradicted by independently checked evidence'],
        ['unresolved','Insufficient evidence to assess'],['value_judgment','Normative/subjective claim, not directly fact-checkable'],
        ['misattributed','Incorrect speaker attribution / quotation does not establish claim']])select.add(new Option(t,v));
      let judgement=el('label','Review conclusion');judgement.append(select);
      let notes=el('textarea');notes.rows=3;notes.placeholder='Explain the evidence, including qualifications and why it applies to this particular claim.';
      let noteLabel=el('label','Reasoning and evidence limitations');noteLabel.append(notes);
      let url=el('input');url.type='url';url.placeholder='https://... independently reviewed reference (optional)';
      let urlLabel=el('label','Independent source link, when relevant');urlLabel.append(url);
      let attribution=el('select');
      for(const [v,t] of [['','Verify whether author endorses claim'],['yes','Author clearly advocates claim'],['quotes','Author only quotes or disputes claim'],['uncertain','Endorsement unclear']])attribution.add(new Option(t,v));
      let aLabel=el('label','Speaker attribution');aLabel.append(attribution);
      let save=el('button','Save review in this session');save.type='button';
      const status=el('span','','cf-small');
      const prior=reviews.get(reviewKey);
      if(prior){select.value=prior.assessment;notes.value=prior.rationale;url.value=prior.independent_source_url;attribution.value=prior.attribution;}
      save.addEventListener('click',()=>{
        if(!select.value||!attribution.value||notes.value.trim().length<30){
          status.textContent='Select conclusion and attribution, and give at least 30 characters of reasoning.';return;
        }
        if(url.value.trim()&&!/^https:\/\//i.test(url.value.trim())){status.textContent='External evidence URLs must start with https://';return;}
        reviews.set(reviewKey,{
          filing_id:id,issue:r.issue,evidence_start:r.start,
          source_quote:r.quote,model_argument:r.argument,model_requested_action:r.action,
          attribution:attribution.value,assessment:select.value,
          rationale:notes.value.trim(),independent_source_url:url.value.trim(),
          review_kind:'proposed_human_assessment_requires_source_check',
          source_url:href(id)
        });
        toggle.textContent='Edit saved assessment';status.textContent='Saved locally. Export to preserve.';
        $('cf-reviewed').textContent=n(reviews.size)+' reviewed candidates';
      });
      form.append(aLabel,judgement,noteLabel,urlLabel,save,status);
      toggle.addEventListener('click',()=>{form.hidden=!form.hidden;});
      box.append(form);$('cf-list').append(box);
    }
    shown+=slice.length;$('cf-more').hidden=shown>=filtered.length;
  }
  function exportRows(){
    if(!reviews.size){$('cf-export-message').textContent='No reviewer assessments have been recorded.';return;}
    let content=JSON.stringify({review_protocol:'claim-review-v1',reviewed_at_utc:new Date().toISOString(),
      warnings:['Human assessments are not independently validated by this tool','Original FCC source and external evidence must be checked before publication'],reviews:[...reviews.values()]},null,2);
    const url=URL.createObjectURL(new Blob([content],{type:'application/json'}));
    let a=el('a');a.href=url;a.download='fcc_claim_review_proposals.json';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1200);
    $('cf-export-message').textContent=n(reviews.size)+' review records exported. This does not publish verdicts to the website.';
  }
  try{
    const files=['./data/kaggle/machine_claim_rows.json','./data/kaggle/filing_quality.json','./data/player_registry.json'];
    const rs=await Promise.all(files.map(f=>fetch(f)));
    for(let i=0;i<rs.length;i++)if(!rs[i].ok)throw Error('Required published data unavailable: '+files[i]);
    const [claims,q,registry]=await Promise.all(rs.map(r=>r.json()));
    if(claims.source_filings!==3231||!Array.isArray(claims.rows)||registry.coverage.filings!==3231||q.coverage.processed_readable_filings!==3230)throw Error('Disagreement across corpus, player and machine evidence versions');
    all=claims.rows;quality=q.filings;for(let f of registry.filings)filings[f.id]=f;
    $('cf-status').textContent='Loaded '+n(all.length)+' machine claim candidates, '+n(registry.coverage.filings)+' source-aligned identities and '+n(Object.keys(quality).length)+' per-filing quality records. No independent verification implied.';
    refresh();
  }catch(err){$('cf-status').textContent='Evidence review workspace unavailable: '+err.message+'. Use the source corpus and existing argument atlas instead.';return;}
  for(const id of ['cf-topic','cf-group','cf-status-filter'])$(id).addEventListener('change',refresh);
  $('cf-query').addEventListener('input',refresh);$('cf-more').addEventListener('click',addRows);
  $('cf-export').addEventListener('click',exportRows);
})();