'use strict';
(async function(){
  const $=id=>document.getElementById(id);
  const make=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=String(txt);if(cls)e.className=cls;return e;};
  const n=x=>Number(x||0).toLocaleString('en-US');
  const pct=(x,d)=>d?((100*x/d).toFixed(1).replace(/\.0$/,''))+'%':'—';
  const fcc=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(id);
  const visit=(label,url)=>{const a=make('a',label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;};
  let data=null,selectedTopic=null,visibleEvidence={};
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
    $('group-description').textContent=(g==='all'?'Browse every indexed source filing.':
      'Explore the filing-based record for this group, including names and tentative affiliations.');
    const stats=[
      [n(ids.length),'FCC filings in this group'],
      [n(hashes.size),'Distinct original source texts'],
      [n(coded.length),'Filings with coded argument themes']
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
        selectedTopic=t.id;visibleEvidence={};table();renderEvidence();renderOrgs();navigateState();
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
  function renderOrgs(){
    const g=groupValue(),c=compareValue();
    const ids=new Set(all(g,selectedTopic).map(f=>f.id));
    if(c)for(const f of all(c,selectedTopic))ids.add(f.id);
    const names=new Map();
    for(const f of data.filings){
      if(!ids.has(f.id)||!f.organization)continue;
      if(!names.has(f.organization))names.set(f.organization,{name:f.organization,ids:new Set(),first:f.id});
      names.get(f.organization).ids.add(f.id);
    }
    const sorted=[...names.values()].sort((a,b)=>b.ids.size-a.ids.size||a.name.localeCompare(b.name));
    $('org-caption').textContent='Named submitters in the selected topic. Multiple filings from one institution do not imply independent supporters.';
    const root=$('organization-list');root.replaceChildren();
    for(const o of sorted.slice(0,24)){
      const div=make('div',undefined,'org-line');
      div.append(visit(o.name,fcc(o.first)),make('small',n(o.ids.size)+' filing'+(o.ids.size===1?'':'s')));
      root.append(div);
    }
    if(!sorted.length)root.append(make('p','No organization names are established in the selected set. Open individual filings for affiliations.','empty-state'));
  }
  function coverage(){
    const root=$('coverage-list');root.replaceChildren();
    const sorted=[...data.stakeholder_groups].sort((a,b)=>b.filings-a.filings);
    for(const f of sorted){
      const b=make('div',undefined,'coverage-item');
      b.append(make('span',n(f.filings),'coverage-value'),make('strong',f.label),
        make('p',n(f.filings_with_coded_topics)+' with identified argument themes'));
      b.tabIndex=0;b.setAttribute('role','button');b.setAttribute('aria-label','Explore '+f.label);
      const go=()=>{$('primary-group').value=f.id;$('second-group').value='';selectedTopic=null;update();$('explore').scrollIntoView({block:'start',behavior:'smooth'});};
      b.addEventListener('click',go);b.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});
      root.append(b);
    }
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
    summary();table();visibleEvidence={};renderEvidence();renderOrgs();navigateState();
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