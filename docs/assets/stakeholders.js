'use strict';
(async function(){
  const $=id=>document.getElementById(id);
  const make=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=String(txt);if(cls)e.className=cls;return e;};
  const n=x=>Number(x||0).toLocaleString('en-US');
  const pct=(x,d)=>d?((100*x/d).toFixed(1).replace(/\.0$/,''))+'%':'—';
  const fcc=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(id);
  const visit=(label,url)=>{const a=make('a',label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;};
  let data=null,selectedTopic=null,visibleEvidence={},orgLimit=24,selectedOrg=null;
  const labels={},byGroup={},byTopic={},groupIds=new Map();
  const groupValue=()=> $('primary-group').value;
  const compareValue=()=> $('second-group').value;
  const groupName=g=>g==='all'?'All commenters':labels[g]||g;
  const all=(g,topic)=>data.filings.filter(f=>(g==='all'||f.group===g)&&(!topic||f.topics.some(t=>t.topic===topic)));
  const groupSize=g=>g==='all'?data.coverage.filings:(byGroup[g]?.filings||0);
  const topicCell=(topic,g)=>{
    if(g==='all')return {filings:topic.filings,distinct_source_texts:topic.distinct_source_texts,group_filings:data.coverage.filings};
    return topic.by_stakeholder[g]||{filings:0,distinct_source_texts:0,group_filings:0};
  };
  function config(){
    let p=new URLSearchParams(location.search),g=p.get('group'),c=p.get('compare'),t=p.get('topic');
    if(g&&[...$('primary-group').options].some(o=>o.value===g))$('primary-group').value=g;
    if(c&&[...$('second-group').options].some(o=>o.value===c))$('second-group').value=c;
    if(t&&byTopic[t])selectedTopic=t;
    $('primary-group').addEventListener('change',()=>{selectedTopic=null;update()});
    $('second-group').addEventListener('change',update);
    $('category').addEventListener('change',()=>{selectedTopic=null;update()});
    $('sort-order').addEventListener('change',update);
    $('evidence-search').addEventListener('input',renderEvidence);
    $('evidence-clean').addEventListener('change',renderEvidence);
    $('download').addEventListener('click',download);
    $('download-matrix').addEventListener('click',downloadMatrix);
    $('download-audit').addEventListener('click',downloadReviewSample);
    $('org-profile-close').addEventListener('click',()=>{$('org-profile').hidden=true;selectedOrg=null;});
    for(const btn of document.querySelectorAll('[data-preset]'))btn.addEventListener('click',()=>{
      const key=btn.dataset.preset;
      $('category').value='all';selectedTopic=null;
      if(key==='edtech'){$('primary-group').value='edtech_vendors';$('second-group').value='school_institutions';selectedTopic='learning_outcomes'}
      if(key==='consultants'){$('primary-group').value='erate_consultants';$('second-group').value='school_institutions';selectedTopic='consultant_fees'}
      if(key==='screen'){$('primary-group').value='all';$('second-group').value='';$('category').value='Screens & learning';selectedTopic='screen_harms'}
      if(key==='procurement'){$('primary-group').value='all';$('second-group').value='';$('category').value='Consultants & procurement';selectedTopic='vendor_influence'}
      update();
      $('topics').scrollIntoView({block:'start',behavior:'smooth'});
    });
  }
  function navigateState(){
    if(typeof history?.replaceState!=='function')return;
    const params=new URLSearchParams();
    if(groupValue()!=='all')params.set('group',groupValue());
    if(compareValue())params.set('compare',compareValue());
    if(selectedTopic)params.set('topic',selectedTopic);
    history.replaceState(null,'',location.pathname+(params.toString()?'?'+params.toString():''));
  }
  function summary(){
    const g=groupValue(),name=groupName(g);
    $('group-heading').textContent=name;
    let ids=all(g),coded=ids.filter(f=>f.topics.length),hashes=new Set(ids.map(f=>f.text_sha256).filter(Boolean));
    const distinctInstitutions=new Set(ids.map(f=>f.organization).filter(Boolean)).size;
    $('group-description').textContent=(g==='all'?'Browse every indexed source filing.':
      'Explore the filing-based record for this group, including names and tentative affiliations.');
    const stats=[
      [n(ids.length),'FCC filings in this group'],
      [n(hashes.size),'Distinct original source texts'],
      [n(coded.length),'Filings with coded argument themes'],
      [n(distinctInstitutions),'Named institutions in selected group']
    ];
    $('summary-strip').replaceChildren(...stats.map(([num,label])=>{
      const el=make('div',undefined,'summary-stat');el.append(make('strong',num),make('span',label));return el;
    }));
  }
  function table(){
    let g=groupValue(),c=compareValue();
    const cat=$('category').value;
    const visible=data.topics.filter(t=>cat==='all'||t.category===cat);
    let sorted=[...visible];
    const rate=(t,x)=>{const v=topicCell(t,x);return v.filings/Math.max(1,groupSize(x));};
    switch($('sort-order').value){
      case 'difference':if(c)sorted.sort((a,b)=>Math.abs(rate(b,g)-rate(b,c))-Math.abs(rate(a,g)-rate(a,c)));else sorted.sort((a,b)=>rate(b,g)-rate(a,g));break;
      case 'overall':sorted.sort((a,b)=>b.filings-a.filings);break;
      case 'alpha':sorted.sort((a,b)=>a.label.localeCompare(b.label));break;
      default:sorted.sort((a,b)=>rate(b,g)-rate(a,g)||b.filings-a.filings);
    }
    if(!selectedTopic||!visible.some(t=>t.id===selectedTopic))selectedTopic=sorted[0]?.id||null;
    const root=$('argument-table');root.replaceChildren();
    let header=make('div',undefined,'table-header'+(c?' comparison':''));
    header.append(make('span','Argument'),make('span',groupName(g)));
    if(c)header.append(make('span',groupName(c),'second-header'));
    header.append(make('span',''));root.append(header);
    if(!sorted.length){root.append(make('p','No themes available under this filter.','empty-state'));return;}
    for(const t of sorted){
      const row=make('button',undefined,'arg-row'+(c?' comparison':''));
      row.type='button';row.setAttribute('aria-pressed',String(selectedTopic===t.id));
      row.setAttribute('aria-label',t.label+', '+n(topicCell(t,g).filings)+' filings, view sources');
      const left=make('span');left.append(make('span',t.label,'arg-title'),make('span',t.category,'arg-category'));row.append(left);
      for(const group of [g,...(c?[c]:[])]){
        const cell=topicCell(t,group),bar=make('span',undefined,'bar-unit');
        const bl=make('span',undefined,'bar-label');
        bl.append(make('b',n(cell.filings)+' filings'),make('small',pct(cell.filings,groupSize(group))));
        const track=make('span',undefined,'bar-line'),fill=make('span',undefined,'bar-fill'+(group===c?' second':''));
        fill.style.width=(groupSize(group)?100*cell.filings/groupSize(group):0)+'%';
        track.append(fill);bar.append(bl,track);row.append(bar);
      }
      row.append(make('span','›','arg-arrow'));
      row.addEventListener('click',()=>{
        selectedTopic=t.id;visibleEvidence={};table();renderStakeholdersForTopic();renderDetailedRoles();renderEvidence();renderOrgs();navigateState();
        $('evidence').scrollIntoView({block:'start',behavior:'smooth'});
      });
      root.append(row);
    }
  }
  function evidenceRows(g){
    const term=$('evidence-search').value.trim().toLowerCase();
    let rows=all(g,selectedTopic).map(f=>({f,e:f.topics.find(t=>t.topic===selectedTopic)}));
    if(term)rows=rows.filter(({f,e})=>[f.organization,f.id,e.argument,e.action,e.quote].join(' ').toLowerCase().includes(term));
    rows.sort((a,b)=>{
      const score=x=>Number(!x.f.organization)*10+Number(x.e.needs_speaker_review)*4+
         Number(x.f.quality_scope!=='full_text')*2+Number(x.f.joint_filing);
      const d=score(a)-score(b);
      if(d)return d;
      return (b.e.quote?.length||0)-(a.e.quote?.length||0)||a.f.id.localeCompare(b.f.id);
    });
    if($('evidence-clean').checked){
      const low=rows.filter(x=>!x.e.needs_speaker_review&&x.f.quality_scope==='full_text');
      // Never pretend there are no arguments when all available candidates need review.
      if(low.length)rows=low;
    }
    return rows;
  }
  function renderStakeholdersForTopic(){
    const t=byTopic[selectedTopic],root=$('group-by-topic');
    root.replaceChildren();
    if(!t)return;
    $('group-by-topic-description').textContent=n(t.filings)+' source filings, '+n(t.distinct_source_texts)+' distinct source texts, and '+n(t.named_institutions||0)+' named submitter institutions have an extracted argument in this category. See which stakeholder groups submitted them. Institutional names may be missing for personal or joint filings.';
    const header=make('div',undefined,'inverse-header');
    header.append(make('span','Stakeholder'),make('span','Filings raising argument'),
      make('span','Share of topic'),make('span','Within group'));root.append(header);
    const groups=data.stakeholder_groups.filter(g=>topicCell(t,g.id).filings>0);
    groups.sort((a,b)=>topicCell(t,b.id).filings-topicCell(t,a.id).filings);
    for(const g of groups){
      const count=topicCell(t,g.id).filings;
      const row=make('button',undefined,'inverse-row');
      row.type='button';
      row.title=n(topicCell(t,g.id).named_institutions||0)+' named institutional submitters; '+n(topicCell(t,g.id).distinct_source_texts||0)+' distinct original texts. All counts remain provisional.';
      row.append(make('span',g.label),make('b',n(count)),
        make('span',pct(count,t.filings)),
        make('span',pct(count,g.filings)));
      row.addEventListener('click',()=>{
        $('primary-group').value=g.id;
        $('second-group').value='';
        update();
        $('explore').scrollIntoView({block:'start',behavior:'smooth'});
      });
      root.append(row);
    }
  }
  function renderDetailedRoles(){
    const root=$('role-by-topic');root.replaceChildren();
    const topic=byTopic[selectedTopic];
    if(!topic||!topic.by_detailed_role){
      root.append(make('p','Detailed roles have not yet been published with this dataset.','small-note'));
      return;
    }
    const roles=data.stakeholder_roles.filter(r=>topic.by_detailed_role[r.id]?.filings>0)
      .sort((a,b)=>topic.by_detailed_role[b.id].filings-topic.by_detailed_role[a.id].filings);
    const head=make('div',undefined,'inverse-header');
    head.append(make('span','Specific role'),make('span','Filings raising argument'),
      make('span','Share of topic'),make('span','Within role'));root.append(head);
    for(const role of roles){
      const c=topic.by_detailed_role[role.id],row=make('div',undefined,'inverse-row');
      row.title=n(c.distinct_source_texts)+' distinct original source texts; classification remains provisional.';
      row.append(make('span',role.id.replace(/_/g,' ')),make('b',n(c.filings)),
        make('span',pct(c.filings,topic.filings)),make('span',pct(c.filings,c.role_filings)));
      root.append(row);
    }
  }
  function differences(){
    const c=compareValue(),root=$('comparison-leads');
    root.replaceChildren();root.hidden=!c;
    if(!c)return;
    const g=groupValue(),nA=groupSize(g),nB=groupSize(c);
    if(!nA||!nB){root.hidden=true;return;}
    const diffs=data.topics.map(t=>{
      const a=topicCell(t,g).filings,b=topicCell(t,c).filings;
      return {topic:t,delta:100*(a/nA-b/nB),a,b};
    }).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta));
    root.append(make('h3','Different emphases'));
    const caution=make('p', 'These are differences in how frequently filings mention an argument, not proof that the groups disagree.','small-note');
    root.append(caution);
    const top=diffs.filter(x=>x.a+x.b).slice(0,4);
    for(const {topic,delta,a,b} of top){
      const button=make('button',undefined,'difference-item');
      button.type='button';
      button.append(make('strong',topic.label),
        make('span',n(a)+' / '+n(nA)+' vs '+n(b)+' / '+n(nB)+' filings ('+
          Math.abs(delta).toFixed(1)+' percentage-point difference)'));
      button.addEventListener('click',()=>{
        selectedTopic=topic.id;table();renderEvidence();renderStakeholdersForTopic();renderDetailedRoles();renderOrgs();navigateState();
        $('evidence').scrollIntoView({block:'start',behavior:'smooth'});
      });
      root.append(button);
    }
    if(Math.min(nA,nB)<15)root.append(make('p','One comparison group contains fewer than 15 filings. Even large percentage differences may reflect only one or two comments.','small-note'));
  }
  function renderEvidence(){
    const t=byTopic[selectedTopic],g=groupValue(),c=compareValue();
    if(!t){$('evidence-columns').replaceChildren();return;}
    $('evidence-heading').textContent=t.label;
    $('evidence-description').textContent=c?'Read what each group submitted on this subject.':'Read attributed, source-linked examples from '+groupName(g).toLowerCase()+'.';
    const root=$('evidence-columns');root.replaceChildren();root.classList.toggle('single',!c);
    for(const x of [...new Set([g,...(c?[c]:[])])]){
      const matches=evidenceRows(x),limit=visibleEvidence[x]||5,col=make('div',undefined,'evidence-col');
      col.append(make('h4',groupName(x)+' · '+n(matches.length)+' filings'));
      if(!matches.length){col.append(make('p','No extracted argument found for this group and topic. This does not establish that the group has no position.','empty-state'));root.append(col);continue;}
      for(const {f,e} of matches.slice(0,limit)){
        const card=make('article',undefined,'source-article');
        card.append(make('h5',f.organization||labels[f.group]||'Filer affiliation not established'));
        if(e.action&&e.action!=='none')card.append(make('p',e.action,'interpretation'));
        else if(e.argument)card.append(make('p',e.argument,'interpretation'));
        card.append(make('blockquote',e.quote||'Quote was not included in the analysis output.'));
        card.append(visit('Read FCC filing '+f.id+' ↗',fcc(f.id)));
        const caveats=[];
        if(e.needs_speaker_review)caveats.push('Check speaker attribution and identity');
        if(f.quality_scope==='prioritized_windows')caveats.push('Only selected text windows were model-read');
        if(f.joint_filing)caveats.push('Joint filing; do not multiply speakers');
        if((e.context_flags||[]).length)caveats.push('Automated context review flags');
        if(caveats.length){
          const dt=make('details'),head=make('summary','Research notes'),body=make('p',caveats.join(' · '));
          dt.append(head,body);card.append(dt);
        }
        col.append(card);
      }
      if(matches.length>limit){
        const btn=make('button','Show more filings ('+n(matches.length-limit)+' remaining)','show-more');
        btn.addEventListener('click',()=>{visibleEvidence[x]=limit+5;renderEvidence();});
        col.append(btn);
      }
      root.append(col);
    }
  }
  function showOrgProfile(name){
    selectedOrg=name;
    const filings=data.filings.filter(f=>f.organization===name);
    const root=$('org-profile');root.hidden=false;
    $('org-profile-title').textContent=name;
    const norm=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'');
    const jointAppearances=data.filings.filter(f=>
      f.joint_filing&&(f.joint_institutions||[]).some(candidate=>norm(candidate)===norm(name)));
    const totalThemes=new Set(filings.flatMap(f=>f.topics.map(t=>t.topic)));
    const role=filings[0]?.role||'unresolved';
    const inferred=filings.some(f=>f.identity_review_required||f.joint_filing);
    $('org-profile-context').textContent=n(filings.length)+' source filing'+(filings.length===1?'':'s')+' · '+
      n(totalThemes.size)+' extracted argument themes · '+role.replace(/_/g,' ')+
      (inferred?' · Institution and representation require original-source confirmation.':'.');
    const topics=new Map();
    for(const f of filings)for(const e of f.topics){
      if(!topics.has(e.topic))topics.set(e.topic,[]);
      topics.get(e.topic).push({f,e});
    }
    const place=$('org-profile-topics');place.replaceChildren();
    const ordered=[...topics.entries()].sort((a,b)=>b[1].length-a[1].length);
    for(const [code,entries] of ordered){
      const topic=byTopic[code],detail=make('details',undefined,'profile-topic');
      const summary=make('summary',(topic?.label||code)+' · '+n(entries.length)+' filing'+(entries.length===1?'':'s'));
      detail.append(summary);
      for(const {f,e} of entries.slice(0,8)){
        const item=make('div',undefined,'profile-evidence');
        item.append(make('p',e.action||e.argument||'Model interpretation not available'));
        item.append(make('blockquote',e.quote||'Source excerpt unavailable'));
        item.append(visit('FCC '+f.id+' ↗',fcc(f.id)));
        if(e.needs_speaker_review)item.append(make('small',' · Attribution needs checking'));
        detail.append(item);
      }
      if(entries.length>8)detail.append(make('p','Additional filings are available in the original corpus.','small-note'));
      place.append(detail);
    }
    if(!ordered.length)place.append(make('p','No substantive argument was extracted for this institution. Open its original filing to inspect the complete submission.','empty-state'));
    const source=make('p',undefined,'method-links');
    for(const f of filings.slice(0,7))source.append(visit('Original FCC '+f.id,fcc(f.id)),document.createTextNode(' · '));
    place.append(source);
    if(jointAppearances.length){
      const co=make('div',undefined,'joint-note');
      co.append(make('strong','Additional joint filings mentioning this institution'));
      co.append(make('p','These are entries in multi-institution submitter metadata. They are not counted as separately authored comments or attributed individual endorsements.'));
      for(const f of jointAppearances)co.append(visit('Joint FCC '+f.id+' ↗',fcc(f.id)),document.createTextNode(' · '));
      place.append(co);
    }
    root.scrollIntoView({block:'center',behavior:'smooth'});
  }
  function renderOrgs(){
    // List all named organizations in the group, even if the selected topic
    // has no extracted argument for them. This prevents hiding niche vendors.
    const g=groupValue(),c=compareValue(),scope=data.filings.filter(f=>
      (g==='all'||f.group===g||Boolean(c&&f.group===c))&&Boolean(f.organization));
    const named=new Map();
    for(const f of scope){
      if(!named.has(f.organization))named.set(f.organization,{name:f.organization,ids:new Set(),themeIds:new Set()});
      const obj=named.get(f.organization);
      obj.ids.add(f.id);
      if(f.topics.some(t=>t.topic===selectedTopic))obj.themeIds.add(f.id);
    }
    const sorted=[...named.values()].sort((a,b)=>b.themeIds.size-a.themeIds.size||
      b.ids.size-a.ids.size||a.name.localeCompare(b.name));
    $('org-caption').textContent=n(sorted.length)+' named organizations in the chosen stakeholder group'+
      (c?'s':'')+'. The second number shows filings with the selected argument. Select an organization to see all its extracted themes.';
    const root=$('organization-list');root.replaceChildren();
    for(const o of sorted.slice(0,orgLimit)){
      const div=make('div',undefined,'org-line'),button=make('button',o.name,'org-name-button');
      button.type='button';button.addEventListener('click',()=>showOrgProfile(o.name));
      div.append(button,make('small',n(o.ids.size)+' total · '+n(o.themeIds.size)+' here'));
      root.append(div);
    }
    if(!sorted.length)root.append(make('p','No named institutions in this selection. You can still inspect the linked filings.','empty-state'));
    const more=$('org-more');more.hidden=sorted.length<=orgLimit;
    more.onclick=()=>{orgLimit+=24;renderOrgs();};
    if(selectedOrg&&!named.has(selectedOrg)){$('org-profile').hidden=true;selectedOrg=null;}
  }
  function coverage(){
    const root=$('coverage-list');root.replaceChildren();
    const sorted=[...data.stakeholder_groups].sort((a,b)=>b.filings-a.filings);
    for(const f of sorted){
      const b=make('div',undefined,'coverage-item');
      b.append(make('span',n(f.filings),'coverage-value'),make('strong',f.label),
        make('p',pct(f.filings,data.coverage.filings)+' of all indexed filings · '+
          n(f.filings_with_coded_topics)+' with identified argument themes · '+
          n(f.unique_texts)+' distinct source texts'));
      b.tabIndex=0;b.setAttribute('role','button');b.setAttribute('aria-label','Explore '+f.label);
      const go=()=>{$('primary-group').value=f.id;$('second-group').value='';selectedTopic=null;update();$('explore').scrollIntoView({block:'start',behavior:'smooth'});};
      b.addEventListener('click',go);b.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});
      root.append(b);
    }
  }
  function downloadReviewSample(){
    // A reproducible, purposefully oversampled QUALITY sample, not population
    // sampling: intentionally include every small, high-interest industry group.
    const priorityGroups=new Set(['edtech_vendors','edtech_trade_associations',
      'erate_consultants','consultant_associations','connectivity_and_network_vendors',
      'telecom_associations']);
    const rows=data.filings.filter(f=>f.quality_scope!=='not_modeled');
    const byId=new Map(rows.map(f=>[f.id,f]));
    const items=new Map();
    const fnv=str=>{
      let h=2166136261;
      for(const c of String(str)){h^=c.charCodeAt(0);h=Math.imul(h,16777619);}
      return h>>>0;
    };
    const sortFor=(pool,stratum)=>pool.slice().sort((a,b)=>
      fnv(stratum+'|'+a.id)-fnv(stratum+'|'+b.id)||a.id.localeCompare(b.id));
    function add(f,topic,reason){
      const item=f.topics.find(t=>t.topic===topic);
      const key=f.id+'|'+(topic||'none');
      if(items.has(key))return;
      items.set(key,{f,item,topic:topic||'',reason});
    }
    const highValue=(e)=>/^(consultant_|vendor_influence|competitive_bidding|bid_independence|administrative_burden|program_integrity|alleged_misuse|learning_outcomes|screen_policy|screen_harms|screen_use_distinctions|edtech_study_evidence|adaptive_learning|technology_cost_benefit)/.test(e.topic);
    for(const f of rows){
      if(!priorityGroups.has(f.group))continue;
      const topics=f.topics.slice().sort((a,b)=>Number(highValue(b))-Number(highValue(a))||
        a.topic.localeCompare(b.topic));
      if(!topics.length)add(f,'','high_priority_sector_no_extracted_argument');
      for(const e of topics.slice(0,Math.max(6,Math.min(topics.length,10))))
        add(f,e.topic,'all_filers_in_high_priority_industry_group');
    }
    const groups=data.stakeholder_groups.filter(g=>!priorityGroups.has(g.id));
    for(const g of groups){
      const pool=sortFor(rows.filter(f=>f.group===g.id),'comparison_group_'+g.id);
      for(const f of pool.slice(0,Math.min(12,pool.length))){
        const selected=f.topics.slice(0,2);
        if(!selected.length)add(f,'','comparison_group_no_coded_theme_control');
        else for(const e of selected)add(f,e.topic,'comparison_group_stratified_check');
      }
    }
    // Cover every thematic definition, including rare edtech and consultant
    // categories; this makes review useful for precision, not merely frequency.
    for(const theme of data.topics){
      const pool=sortFor(rows.filter(f=>f.topics.some(x=>x.topic===theme.id)),
        'theme_precision_'+theme.id);
      for(const f of pool.slice(0,Math.min(3,pool.length)))
        add(f,theme.id,'theme_precision_check');
      // Negative controls matter: an extraction gap is not a zero-stance.
      const negative=sortFor(rows.filter(f=>f.quality_scope==='full_text'&&
        !f.topics.some(x=>x.topic===theme.id)),
        'theme_omission_'+theme.id);
      if(negative.length)add(negative[0],theme.id,'no_extracted_argument_negative_control');
    }
    const headings=['selection_reason','fcc_filing_id','stakeholder_group','specific_role_candidate',
      'institution_candidate','argument_topic','argument_label','machine_interpretation_unverified',
      'original_filing_quote_if_extracted','original_fcc_url','text_scope',
      'identity_or_speaker_review_needed','joint_submission','independent_source_checked',
      'correct_stakeholder_role','author_endorses_argument','argument_actually_present',
      'reviewer_notes'];
    const clean=v=>{
      let s=String(v??'');
      if(/^\s*[=+@-]/.test(s))s="'"+s;
      return '"'+s.replace(/"/g,'""')+'"';
    };
    const lines=[headings.map(clean).join(',')];
    for(const {f,item,topic,reason} of items.values()){
      const label=byTopic[topic]?.label||'No model claim; inspect complete source';
      const negative=reason==='no_extracted_argument_negative_control';
      lines.push([
        reason,f.id,f.group,f.role,f.organization,topic,label,
        negative?'[No extracted argument for this topic; verify full original]':item?.action||item?.argument||'',
        negative?'':item?.quote||'',fcc(f.id),f.quality_scope,
        Boolean(f.identity_review_required||f.representative_possible||f.joint_filing||item?.needs_speaker_review),
        Boolean(f.joint_filing),'','','','',''
      ].map(clean).join(','));
    }
    const csv='\ufeff'+lines.join('\r\n')+'\r\n';
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
    const a=make('a');a.href=url;a.download='erate_stakeholder_validation_worksheet.csv';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('audit-download-status').textContent=n(items.size)+' source-linked review assignments exported. Review conclusions are blank until independently checked.';
  }
  function downloadMatrix(){
    const group=groupValue(),compare=compareValue(),category=$('category').value;
    const relevantGroups=group==='all'?data.stakeholder_groups:
      data.stakeholder_groups.filter(g=>g.id===group||Boolean(compare&&g.id===compare));
    const values=[['topic_id','argument_label','issue_area','stakeholder_group','stakeholder_label',
      'all_filings_in_group','group_filings_with_any_extracted_argument',
      'filings_with_this_argument','pct_of_all_group_filings','pct_of_coded_group_filings',
      'pct_of_all_filings_with_this_argument','distinct_original_source_texts',
      'named_institutions_with_this_argument','lower_risk_filings','needs_attribution_or_identity_review',
      'source_coding_status']];
    for(const t of data.topics){
      if(category!=='all'&&t.category!==category)continue;
      for(const g of relevantGroups){
        const c=topicCell(t,g.id);
        values.push([t.id,t.label,t.category,g.id,g.label,g.filings,g.filings_with_coded_topics,
          c.filings,c.pct_of_group_filings,c.pct_of_coded_group_filings,
          t.filings?Number((100*c.filings/t.filings).toFixed(2)):null,
          c.distinct_source_texts,c.named_institutions,c.lower_risk_filings,
          c.needs_attribution_or_identity_review,
          'Unvalidated model-extracted argument; filing counts not verified endorsements']);
      }
    }
    function escape(v){
      let s=v===null||v===undefined?'':String(v);
      if(/^\s*[=+@-]/.test(s))s="'"+s;
      return '"'+s.replace(/"/g,'""')+'"';
    }
    const csv='\ufeff'+values.map(row=>row.map(escape).join(',')).join('\r\n')+'\r\n';
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
    const a=make('a');a.href=url;a.download='erate_stakeholder_argument_frequencies.csv';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function download(){
    const g=groupValue(),c=compareValue(),cat=$('category').value;
    const rows=data.filings.filter(f=>(g==='all'||f.group===g||Boolean(c&&f.group===c)));
    const headers=['filing_id','stakeholder_group','role_candidate','institution_candidate','joint_filing','topic','topic_label','category','original_quote','machine_interpretation_unverified','fcc_source_url','attribution_needs_review','semantic_scope'];
    const quote=v=>{
      let s=String(v??'');
      if(/^\s*[=+@-]/.test(s))s="'"+s;
      return '"'+s.replace(/"/g,'""')+'"';
    };
    const lines=[headers.map(quote).join(',')];
    for(const f of rows)for(const item of f.topics){
      const topic=byTopic[item.topic];if(cat!=='all'&&topic.category!==cat)continue;
      lines.push([f.id,f.group,f.role,f.organization,f.joint_filing,item.topic,topic.label,topic.category,
        item.quote,item.action||item.argument,'https://www.fcc.gov/ecfs/filing/'+f.id,
        item.needs_speaker_review,f.quality_scope].map(quote).join(','));
    }
    const url=URL.createObjectURL(new Blob(['\ufeff'+lines.join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'}));
    const a=make('a');a.href=url;a.download='erate_stakeholder_arguments.csv';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function update(){
    const g=groupValue(),c=compareValue();
    if(g===c&&g!=='all')$('second-group').value='';
    if(g==='all'&&c==='all')$('second-group').value='';
    orgLimit=24;selectedOrg=null;$('org-profile').hidden=true;
    summary();table();visibleEvidence={};renderStakeholdersForTopic();renderDetailedRoles();renderEvidence();renderOrgs();differences();navigateState();
  }
  try{
    const r=await fetch('./data/stakeholder_argument_census.json');
    if(!r.ok)throw Error('analysis dataset unavailable (HTTP '+r.status+')');
    data=await r.json();
    if(data.schema!=='stakeholder-arguments-v1'||data.coverage.filings!==3231||
      data.filings.length!==3231||new Set(data.filings.map(f=>f.id)).size!==3231)
      throw Error('source completeness check failed');
    for(const g of data.stakeholder_groups){labels[g.id]=g.label;byGroup[g.id]=g;}
    for(const t of data.topics)byTopic[t.id]=t;
    config();update();coverage();
    $('load-status').textContent=n(data.coverage.filings)+' FCC filings · '+n(data.coverage.filings_with_coded_topics)+
      ' with categorized arguments · '+n(data.topics.length)+' argument topics. Source quotations are verifiable; topic and speaker interpretations remain preliminary.';
  }catch(e){
    $('load-status').textContent='The argument analysis is not available yet: '+e.message+
      '. The original filings and other research views remain accessible above.';
    $('load-status').classList.add('error');
    $('argument-table').replaceChildren(make('p','Unable to load the completed research dataset.','empty-state'));
  }
})();