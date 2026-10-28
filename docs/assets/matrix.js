'use strict';
(function () {
  const $ = id => document.getElementById(id);
  const number = x => Number(x || 0).toLocaleString('en-US');
  const rate = (num, den) => den ? (100 * num / den).toFixed(1).replace(/\.0$/, '') + '%' : '—';
  const el = (tag, value, cls) => {
    const node = document.createElement(tag);
    if (value !== undefined) node.textContent = String(value);
    if (cls) node.className = cls;
    return node;
  };
  const fcc = id => 'https://www.fcc.gov/ecfs/filing/' + encodeURIComponent(String(id));
  const url = (text, href) => {
    const a = el('a', text);
    a.href = href;
    a.rel = 'noopener noreferrer';
    a.target = '_blank';
    return a;
  };
  const spotlight = [
    'program_continuity','learning_outcomes','screen_harms','screen_policy',
    'screen_use_distinctions','edtech_study_evidence','accessibility',
    'school_discretion','consultant_registration','consultant_definition',
    'consultant_fees','consultant_reporting','consultant_value',
    'consultant_independence','vendor_influence','alleged_misuse'
  ];
  const focusGroups = [
    'school_institutions','school_professionals','school_affiliation_uncertain',
    'edtech_vendors','edtech_trade_associations','erate_consultants',
    'consultant_associations'
  ];
  const groupPresets = {
    focus: focusGroups,
    edtech: ['school_institutions','school_professionals','school_affiliation_uncertain',
      'edtech_vendors','edtech_trade_associations'],
    consultants: ['school_institutions','school_professionals','school_affiliation_uncertain',
      'erate_consultants','consultant_associations']
  };
  // Every frame is a transparent retrieval heuristic over model-extracted
  // claims: it is neither a classifier of endorsement nor a population count.
  const frames = {
    edtech: [
      ['educational_value','Instructional value','Claims about learning outcomes and classroom benefits',
        ['learning_outcomes','adaptive_learning','digital_literacy','teacher_workload'],
        /\b(?:learn(?:ing)?|instruction|academic|classroom|educat|student achievement|teacher|literacy)\b/i],
      ['research','Research and evidence','Claims invoking studies, research or measurable outcomes',
        ['edtech_study_evidence','learning_outcomes'],/\b(?:research|stud(?:y|ies)|evidence|trial|measur|outcome|academic performance)\b/i],
      ['screen_differences','Different kinds of screen use','Distinguishing instruction from recreational or passive screen use',
        ['screen_use_distinctions','screen_policy','learning_outcomes'],
        /\b(?:recreational|instructional|passive|not all screen|types of screen|educational screen|productive screen)\b/i],
      ['screen_risks','Concerns about screen use','Discussion of screen harms, risks and developmental effects, regardless of position',
        ['screen_harms','screen_policy'],
        /\b(?:harm|risk|concern|addict|screen time|screen-time|mental health|developmental|excessive)\b/i],
      ['accessibility','Accessibility and inclusion','Discussion of assistive technology or disability access',
        ['accessibility'],/\b(?:accessib|disabil|assistive|special education|screen reader)\b/i],
      ['decision_making','School and family choice','Local discretion, parental choice and federal conditions',
        ['school_discretion','parent_choice','screen_policy'],
        /\b(?:local|school|district|parent|family|opt.out|mandat|federal|decision|choice)\b/i],
      ['edtech_costs','Cost and procurement','Vendor prices, purchasing choices and financial tradeoffs',
        ['technology_cost_benefit','competitive_bidding','vendor_influence'],
        /\b(?:cost|procure|price|vendor|spend|software|bidd|roi|fund)\b/i]
    ],
    consultants: [
      ['registration','Registration and definitions','Who must register, qualify or be defined as a consultant',
        ['consultant_registration','consultant_definition','consultant_qualifications'],
        /\b(?:consultant|registr|qualif|credential|licens|defin|exempt)\b/i],
      ['fees','Fees and compensation','Percentage, contingency and other consultant payment structures',
        ['consultant_fees'],/\b(?:fee|percent|contingen|compensat|payment|billing)\b/i],
      ['expertise','Consultants as support','Expertise, capacity, school assistance and compliance navigation',
        ['consultant_value'],/\b(?:consultant|support|expert|comply|compliance|assist|capacity)\b/i],
      ['burden','Paperwork and burden','Compliance and administrative costs or form requirements',
        ['administrative_burden','consultant_reporting'],
        /\b(?:paperwork|burden|compliance|administrat|form|filing|disclos|record|report)\b/i],
      ['independence','Consultant independence','Vendor ties, impartiality, conflicts of interest and independence',
        ['consultant_independence','vendor_influence','bid_independence'],
        /\b(?:vendor|conflict|independ|neutral|impartial|incentive|steer|interest)\b/i],
      ['bidding','Procurement and competition','Rules for fair bidding and choosing service providers',
        ['competitive_bidding','bid_independence'],
        /\b(?:bid|procure|competit|rfp|vendor|service provider)\b/i],
      ['misuse','Alleged misuse versus oversight','Potential fraud or misuse claims, not ordinary calls for better oversight',
        ['alleged_misuse'],/\b(?:fraud|misus|misappropriat|kickback|overbill|improper)\b/i]
    ]
  };

  let data, byTopic = new Map(), byGroup = new Map(), groupRows = new Map();
  let activeGroup = 'edtech_vendors', activeTopic = 'learning_outcomes';
  let visibleGroups = [], visibleTopics = [], evidenceLimits = {};
  const fullGroupCounts = new Map(), fullTopicCounts = new Map(), fullCells = new Map();

  function cell(topic, group) {
    return topic.by_stakeholder[group] || {filings:0,distinct_source_texts:0,named_institutions:0,
      needs_attribution_or_identity_review:0,lower_risk_filings:0};
  }
  function groupSize(group) { return byGroup.get(group)?.filings || 0; }
  function label(group) { return byGroup.get(group)?.label || group; }
  function count(topic, group) { return cell(topic, group).filings || 0; }
  function fullOnly() { return $('coverage-filter').value === 'full'; }
  function scopedGroupSize(group) { return fullOnly() ? (fullGroupCounts.get(group)||0) : groupSize(group); }
  function scopedTopicSize(topic) { return fullOnly() ? (fullTopicCounts.get(topic.id)||0) : topic.filings; }
  function scopedCount(topic, group) {
    return fullOnly() ? (fullCells.get(topic.id+'|'+group)||0) : count(topic,group);
  }
  function sourceFilings(group) {
    const records=groupRows.get(group)||[];
    return fullOnly() ? records.filter(f=>f.quality_scope==='full_text') : records;
  }
  function measureValue(topic, group) {
    const c=scopedCount(topic,group),measure=$('measure').value;
    if (measure==='topic') return scopedTopicSize(topic)?c/scopedTopicSize(topic):0;
    if (measure==='within') return scopedGroupSize(group)?c/scopedGroupSize(group):0;
    return c;
  }
  function checkedGroup(group) {
    return group && byGroup.has(group) ? group : '';
  }
  function topicRow(f, topic) {
    return (f.topics || []).find(e => e.topic === topic) || null;
  }
  function allFor(group, topic) {
    return sourceFilings(group).filter(f=>topicRow(f,topic));
  }
  function checkDataset(d) {
    if (!d || d.schema !== 'stakeholder-arguments-v1' || d.coverage?.filings !== 3231 ||
        !Array.isArray(d.filings) || d.filings.length !== d.coverage.filings)
      throw Error('The source snapshot does not match the expected 3,231 filings.');
    if (new Set(d.filings.map(f => f.id)).size !== d.filings.length)
      throw Error('The source dataset contains duplicated filing IDs.');
    if (d.stakeholder_groups.reduce((s,g) => s+g.filings,0) !== d.filings.length)
      throw Error('Stakeholder filing denominators do not reconcile.');
    for (const t of d.topics) {
      const sum = Object.values(t.by_stakeholder || {}).reduce((s,g)=>s+g.filings,0);
      if (sum !== t.filings) throw Error('Argument frequencies do not reconcile: '+t.id);
    }
  }
  function calcTopics() {
    const category = $('issue-filter').value, q = $('topic-search').value.trim().toLowerCase();
    let topics = data.topics.filter(t => {
      if (category === 'focus' && !spotlight.includes(t.id)) return false;
      if (category !== 'focus' && category !== 'all' && t.category !== category) return false;
      return !q || (t.label + ' ' + t.id + ' ' + t.category).toLowerCase().includes(q);
    });
    if (category === 'focus') topics.sort((a,b) => spotlight.indexOf(a.id)-spotlight.indexOf(b.id));
    else topics.sort((a,b) => b.filings-a.filings || a.label.localeCompare(b.label));
    return topics;
  }
  function calcGroups() {
    const scope = $('group-scope').value;
    const allowed = groupPresets[scope] || data.stakeholder_groups.map(g=>g.id);
    return allowed.filter(g=>byGroup.has(g));
  }
  function updatePresetButtons() {
    for (const btn of document.querySelectorAll('[data-preset]')) {
      let active = btn.dataset.preset === $('group-scope').value;
      if (btn.dataset.preset === 'screens') active = $('issue-filter').value === 'Screens & learning';
      btn.setAttribute('aria-pressed', String(active));
    }
  }
  function renderScopeStatus() {
    const total=data.coverage.filings;
    const full=[...fullGroupCounts.values()].reduce((n,x)=>n+x,0);
    $('scope-message').textContent=fullOnly() ?
      'Full-text model-read subset: '+number(full)+' of '+number(total)+' filing records. All comparison counts, percentages, and examples below use this subset. Candidate OCR may still be unreviewed; full-text model access does not guarantee a correct interpretation.' :
      'Entire indexed snapshot: '+number(total)+' filings. '+number(data.coverage.filings_selected_windows_only)+
        ' were analyzed using selected text windows and '+number(data.coverage.filings_with_ocr_candidate||0)+' include candidate OCR. A missing theme does not imply the filer said nothing about it.';
    $('audit-status').textContent=data.method.source_context_audit_sha256_verified ?
      'Machine source-context audit matches the current claim ledger. Its review flags are automated warnings, not independent confirmation.' :
      'Review status: the source-context audit is out of sync with the machine-claim ledger. Speaker/context risk cannot be assessed reliably until the audit is regenerated. All argument frequencies remain unvalidated.';
  }
  function renderMatrix() {
    visibleGroups = calcGroups(); visibleTopics = calcTopics();
    updatePresetButtons();
    renderScopeStatus();
    const description = {
      within:'Within group = filings with this argument ÷ all filings assigned to this group.',
      topic:'Share of argument = filings in this group with the argument ÷ all filings with the argument.',
      count:'Each cell is the number of distinct FCC filing records in this group that raise the argument.'
    };
    $('measure-explanation').textContent = description[$('measure').value];
    const head=$('matrix-head'),body=$('matrix-body');head.replaceChildren();body.replaceChildren();
    $('matrix-empty').hidden = visibleTopics.length !== 0;
    const tr=el('tr'),main=el('th','Argument / topic total','rowhead');
    main.scope='col';tr.append(main);
    for (const group of visibleGroups) {
      const g = byGroup.get(group);
      const th=el('th');th.scope='col';
      th.append(el('span',g.label),el('span',number(scopedGroupSize(group))+' filings'+(scopedGroupSize(group)<15?' · small sample':''),'col-total'));
      tr.append(th);
    }
    head.append(tr);
    const max = Math.max(1,...visibleTopics.flatMap(t=>visibleGroups.map(g=>measureValue(t,g))));
    for (const topic of visibleTopics) {
      const r=el('tr'),heading=el('th',undefined,'rowhead');heading.scope='row';
      heading.append(el('strong',topic.label),el('small',topic.category+' · '+number(scopedTopicSize(topic))+' total filings'));
      r.append(heading);
      for (const group of visibleGroups) {
        const groupRecord=byGroup.get(group),countHere=scopedCount(topic,group),v=measureValue(topic,group);
        const td=el('td'),btn=el('button',undefined,countHere?'':'zero');btn.type='button';
        const opacity=v/max;
        const colorScale=Math.round(247-opacity*89),tealScale=Math.round(250-opacity*51);
        btn.style.setProperty('--heat','rgb('+colorScale+','+tealScale+','+Math.round(251-opacity*35)+')');
        btn.append(el('strong',$('measure').value==='count'?number(countHere):
          rate(countHere,$('measure').value==='topic'?scopedTopicSize(topic):scopedGroupSize(group))));
        btn.append(el('small',number(countHere)+' filing'+(countHere===1?'':'s')));
        btn.title=groupRecord.label+' / '+topic.label+': '+number(countHere)+' of '+
          number(scopedGroupSize(group))+' group filings in scope; '+number(scopedTopicSize(topic))+' filings overall for this argument in scope.';
        btn.setAttribute('aria-pressed',String(activeGroup===group&&activeTopic===topic.id));
        btn.setAttribute('aria-label',btn.title+'; open source evidence');
        btn.addEventListener('click',()=>selectCell(group,topic.id,true));
        td.append(btn);r.append(td);
      }
      body.append(r);
    }
  }
  function setDeepLink() {
    const qs=new URLSearchParams();
    qs.set('group',activeGroup);qs.set('topic',activeTopic);
    const c=checkedGroup($('comparison-group').value);
    if(c && c!==activeGroup)qs.set('compare',c);
    $('detail-deep-link').href='./stakeholders.html?'+qs.toString();
  }
  function selectCell(group, topic, scroll) {
    if (!byGroup.has(group) || !byTopic.has(topic)) return;
    activeGroup=group;activeTopic=topic;evidenceLimits={};
    const query=new URLSearchParams(location.search);
    query.set('group',group);query.set('topic',topic);
    if (typeof history.replaceState === 'function') history.replaceState(null,'',location.pathname+'?'+query);
    const current = checkedGroup($('comparison-group').value);
    if (current===group || !current) {
      $('comparison-group').value = group.startsWith('school_') ? 'edtech_vendors' : 'school_institutions';
      if ($('comparison-group').value===group)$('comparison-group').value='';
    }
    $('evidence-query').value='';
    renderMatrix();renderDetail();
    if(scroll)$('detail-section').scrollIntoView({behavior:'smooth',block:'start'});
  }
  function renderDetail() {
    const t=byTopic.get(activeTopic),group=activeGroup;
    if(!t)return;
    $('detail-title').textContent=t.label;
    $('detail-subtitle').textContent=label(group)+' · Source-linked comments, with the same exclusive filing categories as the matrix.';
    const nFilings=scopedCount(t,group);
    const matched=allFor(group,t.id);
    const hashes=new Set(matched.map(f=>f.text_sha256).filter(Boolean));
    const stats=[
      [number(nFilings),'Filings in this stakeholder group with the argument'],
      [rate(nFilings,scopedGroupSize(group)),'Share of '+label(group).toLowerCase()+' filings in selected scope'],
      [rate(nFilings,scopedTopicSize(t)),'Share of all filings with this argument in selected scope'],
      [number(hashes.size),'Distinct original texts in this cell']
    ];
    $('detail-metrics').replaceChildren(...stats.map(([v,k])=>{
      const box=el('div',undefined,'detail-stat');box.append(el('strong',v),el('span',k));return box;
    }));
    setDeepLink();
    const comp=checkedGroup($('comparison-group').value);
    const root=$('detail-evidence');root.replaceChildren();root.classList.toggle('one',!comp||comp===group);
    for(const g of [group,...(comp&&comp!==group?[comp]:[])]) renderEvidenceColumn(root,g,t);
  }
  function renderEvidenceColumn(root,g,t) {
    const column=el('div',undefined,'evidence-col');
    const q=$('evidence-query').value.trim().toLowerCase();
    let rows=allFor(g,t.id).map(f=>({f,e:topicRow(f,t.id)}));
    rows=rows.filter(({f,e})=>!q||[f.id,f.organization,e.action,e.argument,e.quote].join(' ').toLowerCase().includes(q));
    const risk=({f,e})=>Number(Boolean(e.needs_speaker_review))*5 + Number(Boolean(f.identity_review_required))*2+
      Number(f.quality_scope!=='full_text')*2+Number(Boolean(f.joint_filing));
    rows.sort((a,b)=>{
      const ra=$('prefer-clear').checked?risk(a):0,rb=$('prefer-clear').checked?risk(b):0;
      return ra-rb || Number(!a.f.organization)-Number(!b.f.organization) ||
        (b.e.quote || '').length-(a.e.quote || '').length || String(a.f.id).localeCompare(String(b.f.id));
    });
    column.append(el('h3',label(g)+' · '+number(rows.length)+' matching filings'));
    if(!rows.length)column.append(el('p','No extracted examples in this selection. This is not evidence that the group holds no view on the topic.','empty'));
    let seenTexts=new Set(),distinct=[];
    for(const entry of rows){
      const hash=entry.f.text_sha256 || entry.f.id;
      if(seenTexts.has(hash))continue;
      seenTexts.add(hash);distinct.push(entry);
    }
    const limit=evidenceLimits[g]||5;
    for(const {f,e} of distinct.slice(0,limit)){
      const card=el('article',undefined,'evidence-row');
      card.append(el('h4',f.organization || 'Affiliation not confirmed'));
      if(e.action && !/^(?:none|not specified|no recommendation)$/i.test(e.action))card.append(el('p',e.action,'action'));
      else if(e.argument)card.append(el('p',e.argument,'action'));
      card.append(el('blockquote',e.quote||'Source excerpt unavailable.'));
      card.append(url('Read original FCC filing '+f.id,fcc(f.id)));
      const issues=[];
      if(f.identity_review_required)issues.push('Organization or role needs review');
      if(e.needs_speaker_review)issues.push('Speaker context needs review');
      if(f.quality_scope==='prioritized_windows')issues.push('Only selected passages were model-read');
      if(f.ocr_candidate)issues.push('OCR transcript may be unreviewed');
      if(!data.method.source_context_audit_sha256_verified)issues.push('Automated source-context audit is out of sync');
      if(f.joint_filing)issues.push('Joint institutional filing');
      if(issues.length)card.append(el('p',issues.join(' · '),'flags'));
      column.append(card);
    }
    if(distinct.length>limit){
      const more=el('button','Show '+number(Math.min(5,distinct.length-limit))+' more distinct-text examples','more');
      more.type='button';more.addEventListener('click',()=>{evidenceLimits[g]=limit+5;renderDetail();});
      column.append(more);
    }
    if(rows.length>distinct.length)column.append(el('p',number(rows.length-distinct.length)+' additional filing records repeat a source text shown or indexed here.','fineprint'));
    root.append(column);
  }
  function renderIdentityBreakdown() {
    const unmatched=(groupRows.get('other_or_unidentified')||[]);
    const counts=new Map();
    for(const f of unmatched)counts.set(f.role,(counts.get(f.role)||0)+1);
    const titles={
      named_person_capacity_unstated:'Named individuals without confirmed professional capacity',
      unresolved:'Affiliation could not be established',
      researcher:'Researchers and health professionals',
      student:'Students'
    };
    const root=$('identity-breakdown');root.replaceChildren();
    const items=[...counts.entries()].sort((a,b)=>b[1]-a[1]);
    for(const [role,n] of items) {
      const line=el('div',undefined,'identity-line');
      line.append(el('span',titles[role]||role.replace(/_/g,' ')),
        el('strong',number(n)+' · '+rate(n,unmatched.length)));
      root.append(line);
    }
  }
  function frameMatches(def, groups) {
    const codes=new Set(def[3]),pattern=def[4],matches=[];
    for(const g of groups)for(const f of sourceFilings(g)) {
      if(f.topics.some(e => codes.has(e.topic) && pattern.test([e.action,e.argument].join(' '))))matches.push(f);
    }
    return matches;
  }
  function renderFrames() {
    const key=$('frame-focus').value;
    const aGroups=key==='edtech'?['edtech_vendors','edtech_trade_associations']:['erate_consultants','consultant_associations'];
    const b=$('frame-compare').value;
    const totalA=aGroups.reduce((s,g)=>s+scopedGroupSize(g),0),totalB=scopedGroupSize(b);
    $('frame-context').textContent=number(totalA)+' filings assigned to the selected industry categories; '+number(totalB)+
      ' filings assigned to '+label(b).toLowerCase()+'. Counts reflect '+(fullOnly()?'full-text model reads only':'the complete index')+'. Joint submissions remain separate. Small denominators make percentages volatile.';
    const root=$('frame-list');root.replaceChildren();
    for(const def of frames[key]){
      const a=frameMatches(def,aGroups),comparison=frameMatches(def,[b]);
      const row=el('div',undefined,'frame-item');
      const name=el('div');
      name.append(el('span',def[1],'frame-name'),el('span',def[2],'frame-description'));
      row.append(name);
      const ca=el('div',undefined,'frame-value');
      ca.append(el('strong',number(a.length)+' / '+number(totalA)),
        el('span',rate(a.length,totalA)+' of industry filings'));
      const cb=el('div',undefined,'frame-value');
      cb.append(el('strong',number(comparison.length)+' / '+number(totalB)),
        el('span',rate(comparison.length,totalB)+' of comparator'));
      row.append(ca,cb);
      const links=el('div',undefined,'frame-sources');
      const examples=a.slice(0,3);
      if (examples.length) {
        links.append(el('span','Example filings: '));
        for(const f of examples) links.append(url(f.organization || 'FCC '+f.id,fcc(f.id)));
      } else links.append(el('span','No matching machine-extracted argument from this industry set.'));
      const go=el('a','Open related argument frequencies');
      const relevant=def[3].find(t=>byTopic.has(t))||'program_continuity';
      const group=aGroups.find(g=>groupSize(g))||aGroups[0];
      go.href='./stakeholders.html?group='+encodeURIComponent(group)+'&compare='+encodeURIComponent(b)+'&topic='+encodeURIComponent(relevant);
      links.append(go);
      row.append(links);root.append(row);
    }
  }
  function exportCSV() {
    const head=['source_scope','argument_id','argument','issue_area','stakeholder_id','stakeholder_group',
      'filings_in_scope_for_group','group_filings_with_extracted_themes',
      'filings_with_argument','share_within_group_pct','share_of_argument_pct',
      'distinct_source_texts','named_institutions','needs_identity_or_attribution_review',
      'review_status'];
    const out=[head],quote=x=>{
      let s=String(x===null||x===undefined?'':x);
      if(/^[\s]*[=+@-]/.test(s))s="'"+s;
      return '"'+s.replace(/"/g,'""')+'"';
    };
    for(const t of data.topics)for(const g of data.stakeholder_groups) {
      const c=cell(t,g.id),subset=allFor(g.id,t.id),scope=fullOnly()?'full_text_model_reads':'all_machine_coded_filings';
      const countHere=scopedCount(t,g.id),gTotal=scopedGroupSize(g.id),tTotal=scopedTopicSize(t);
      const hashes=new Set(subset.map(f=>f.text_sha256).filter(Boolean));
      const names=new Set(subset.map(f=>f.organization).filter(Boolean));
      const cautions=subset.filter(f=>{
        const e=topicRow(f,t.id);
        return e?.needs_speaker_review || f.identity_review_required || f.joint_filing || f.ocr_candidate;
      }).length;
      const coded=sourceFilings(g.id).filter(f=>f.topics.length).length;
      const pctWithin=fullOnly()?(gTotal?countHere/gTotal:0):(g.filings?c.filings/g.filings:0);
      const pctTopic=fullOnly()?(tTotal?countHere/tTotal:0):(t.filings?c.filings/t.filings:0);
      out.push([scope,t.id,t.label,t.category,g.id,g.label,gTotal,coded,countHere,
        (100*pctWithin).toFixed(2),(100*pctTopic).toFixed(2),hashes.size,names.size,cautions,
        'unvalidated machine-extracted argument; no verified stance count']);
    }
    const blob=new Blob(['\ufeff'+out.map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n'],
      {type:'text/csv;charset=utf-8'});
    const object=URL.createObjectURL(blob),a=el('a');
    a.href=object;a.download='erate_stakeholder_argument_matrix_'+(fullOnly()?'full_text':'all_filings')+'.csv';a.click();
    setTimeout(()=>URL.revokeObjectURL(object),1000);
  }
  function exportIndustryAudit() {
    const selectedGroups=new Set(['edtech_vendors','edtech_trade_associations',
      'erate_consultants','consultant_associations']);
    const isEdtechCofiling=f=>f.joint_filing && (f.joint_institutions||[]).some(
      name=>/\b(?:curriculum associates|software (?:and|&) information industry association)\b/i.test(name));
    const selected=data.filings.filter(f=>selectedGroups.has(f.group)||isEdtechCofiling(f))
      .sort((a,b)=>a.group.localeCompare(b.group)||a.id.localeCompare(b.id));
    const headers=[
      'fcc_filing_id','preliminary_stakeholder_group','specific_role_candidate',
      'institution_candidate','joint_institution_names','source_read_scope',
      'role_requires_review','possible_representative_or_client','argument_topic_id',
      'machine_argument_unverified','machine_action_unverified','verbatim_quote',
      'machine_speaker_flag','fcc_url','review_source_read','review_actual_speaker',
      'review_role_correct','review_argument_present','review_argument_endorsed',
      'review_verified_position','reviewer_notes'
    ];
    const encode=value=>{
      let s=String(value===undefined||value===null?'':value);
      if(/^\s*[=+@-]/.test(s))s="'"+s;
      return '"'+s.replace(/"/g,'""')+'"';
    };
    const rows=[headers];
    for(const f of selected){
      for(const item of f.topics.length?f.topics:[null]){
        rows.push([
          f.id,f.group,f.role,f.organization,(f.joint_institutions||[]).join(' | '),
          f.quality_scope,Boolean(f.identity_review_required),Boolean(f.representative_possible),
          item?.topic||'',item?.argument||'',item?.action||'',item?.quote||'',
          Boolean(item?.needs_speaker_review),fcc(f.id),
          '','','','','','',''
        ]);
      }
    }
    const blob=new Blob(['\ufeff'+rows.map(row=>row.map(encode).join(',')).join('\r\n')+'\r\n'],
      {type:'text/csv;charset=utf-8'});
    const target=URL.createObjectURL(blob),a=el('a');
    a.href=target;a.download='erate_edtech_consultant_source_review.csv';a.click();
    setTimeout(()=>URL.revokeObjectURL(target),1000);
    $('industry-audit-status').textContent=number(selected.length)+
      ' source filings ('+number(rows.length-1)+' filing–argument review lines) exported. '+
      'All review answers are blank. This is a targeted census of known industry filings and named joint cofilers, not a representative population sample.';
  }
  function wireControls() {
    $('measure').addEventListener('change',renderMatrix);
    $('group-scope').addEventListener('change',renderMatrix);
    $('issue-filter').addEventListener('change',renderMatrix);
    $('topic-search').addEventListener('input',renderMatrix);
    $('comparison-group').addEventListener('change',renderDetail);
    $('evidence-query').addEventListener('input',renderDetail);
    $('prefer-clear').addEventListener('change',renderDetail);
    $('frame-focus').addEventListener('change',renderFrames);
    $('frame-compare').addEventListener('change',renderFrames);
    $('matrix-export').addEventListener('click',exportCSV);
    $('coverage-filter').addEventListener('change',()=>{evidenceLimits={};renderMatrix();renderDetail();renderFrames();});
    $('industry-audit-export').addEventListener('click',exportIndustryAudit);
    for(const b of document.querySelectorAll('[data-preset]'))b.addEventListener('click',()=>{
      const preset=b.dataset.preset;
      if(preset==='screens'){$('group-scope').value='focus';$('issue-filter').value='Screens & learning';}
      else{$('group-scope').value=preset;$('issue-filter').value=preset==='all'?'all':'focus';}
      $('topic-search').value='';
      if(preset==='edtech'){$('frame-focus').value='edtech';$('frame-compare').value='school_institutions';}
      if(preset==='consultants'){$('frame-focus').value='consultants';$('frame-compare').value='school_institutions';}
      renderMatrix();renderFrames();
    });
  }
  async function main() {
    try {
      const response=await fetch('./data/stakeholder_argument_census.json');
      if(!response.ok)throw Error('Index unavailable (HTTP '+response.status+')');
      const d=await response.json();checkDataset(d);data=d;
      for(const g of data.stakeholder_groups){byGroup.set(g.id,g);groupRows.set(g.id,[]);}
      for(const t of data.topics)byTopic.set(t.id,t);
      for(const f of data.filings){
        if(!groupRows.has(f.group))throw Error('Unknown group: '+f.group);
        groupRows.get(f.group).push(f);
        if(f.quality_scope==='full_text'){
          fullGroupCounts.set(f.group,(fullGroupCounts.get(f.group)||0)+1);
          for(const issue of f.topics){
            fullCells.set(issue.topic+'|'+f.group,(fullCells.get(issue.topic+'|'+f.group)||0)+1);
            fullTopicCounts.set(issue.topic,(fullTopicCounts.get(issue.topic)||0)+1);
          }
        }
      }
      $('stat-filings').textContent=number(data.coverage.filings);
      $('stat-coded').textContent=number(data.coverage.filings_with_coded_topics);
      $('stat-categories').textContent=number(data.topics.length);
      $('stat-groups').textContent=number(data.stakeholder_groups.length);
      for(const g of data.stakeholder_groups){
        const opt=document.createElement('option');opt.value=g.id;opt.textContent=g.label;
        $('comparison-group').append(opt);
      }
      $('comparison-group').value='school_institutions';
      wireControls();
      $('prefer-clear').disabled=!Boolean(data.method.source_context_audit_sha256_verified);
      if($('prefer-clear').disabled)$('prefer-clear').parentElement.append(el('span',' (source-context audit not current)'));
      const fullCount=[...fullGroupCounts.values()].reduce((n,x)=>n+x,0);
      if(fullCount+data.coverage.filings_selected_windows_only>data.coverage.filings)throw Error('Analyzed text scope does not reconcile');
      const p=new URLSearchParams(location.search);
      if(byGroup.has(p.get('group')))activeGroup=p.get('group');
      if(byTopic.has(p.get('topic')))activeTopic=p.get('topic');
      if(activeGroup==='school_institutions')$('comparison-group').value='edtech_vendors';
      $('load-status').textContent=number(data.coverage.filings)+' filing records · '+number(data.coverage.filings_with_coded_topics)+
        ' with extracted arguments · Categories and quotations are preliminary and source-linked.';
      renderMatrix();renderDetail();renderFrames();renderIdentityBreakdown();
    } catch(error) {
      $('load-status').textContent='Unable to load the stakeholder data: '+error.message+
        '. You can still use the complete filing browser or source search.';
      $('load-status').classList.add('error');
      $('matrix-empty').hidden=false;
    }
  }
  main();
})();
