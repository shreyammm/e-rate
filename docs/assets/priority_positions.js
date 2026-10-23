'use strict';
(function(root){
 const CONFIG={
 funding:{name:'E-Rate continuation vs. restrictions',labels:{preserve_expand:'Preserve / strengthen E-Rate',abolish_program:'End / abolish the program',targeted_restriction:'Targeted cuts or narrower support',conditional_or_redesign:'Change program design'}},
 conditions:{name:'New federal conditions on E-Rate',labels:{favor_new_federal_condition:'Favor new federal recipient conditions',oppose_new_federal_condition:'Oppose new federal recipient conditions',conditional_or_locally_controlled:'Local control or qualified conditions',existing_rules_only:'Existing safeguards are sufficient'}},
 screen_harms:{name:'Screen-use harms',labels:{affirmative_harm_concern:'Affirmatively concerned about screen harms',questions_harm_claim:'Questions the harm evidence',acknowledges_concern_no_policy:'Mentions concern without clear stance'}},
 misuse:{name:'Potential allegations of E-Rate misuse',labels:{specific_allegation:'Possible concrete misuse allegation',general_misuse_allegation:'Possible general misuse allegation',risk_or_hypothetical:'Hypothetical misuse risk',oversight_only:'Routine oversight or fraud prevention'}}
 };
 const keys=Object.keys(CONFIG);
 const N=v=>Number(v||0).toLocaleString('en-US');
 const field=(x,axis)=>x.axes?.[axis]||{candidate_labels:[],evidence:[]};
 const key=(reviewer,axis,id)=>reviewer+'|'+axis+'|'+id;
 const fcc=id=>'https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(String(id));
 const full=id=>'./corpus.html?id='+encodeURIComponent(String(id));
 const counts=(filings,axis,label)=>filings.filter(x=>field(x,axis).candidate_labels.includes(label)).length;
 function reviewDecision(args){
  const {reviewer,axis,id,labels,note,source,read,legal,screen_link,condition_type,misuse_type}=args;
  const allowed=CONFIG[axis]?.labels;
  if(!allowed)return {ok:false,error:'Unknown research question'};
  if(!reviewer?.trim())return {ok:false,error:'Enter reviewer ID'};
  if(!read)return {ok:false,error:'Confirm that you read the complete original filing'};
  if(String(note||'').trim().length<12)return {ok:false,error:'Explain the reviewed source position in at least 12 characters'};
  const selected=[...new Set(labels)].filter(x=>Object.hasOwn(allowed,x));
  if(selected.length&&!source)return {ok:false,error:'Select a supporting source excerpt; otherwise do not assign an affirmative code'};
  if(axis==='misuse'&&selected.some(x=>x.includes('allegation'))&&(!legal||legal==='not_assessed'))
   return {ok:false,error:'Distinguish alleged rule violations from objections to possibly legal spending'};
  return {ok:true,value:{reviewer:reviewer.trim(),axis,filing_id:String(id),labels:selected,
    explanation:String(note).trim(),chosen_source_quote:source?.quote||'',
    source_offset:source?.start??'',source_origin:source?.origin||'',
    misuse_legal_characterization:axis==='misuse'?legal:'',
    misuse_allegation_type:axis==='misuse'?misuse_type||'not_assessed':'',
    screen_harm_to_funding_condition_link:screen_link||'not_assessed',
    new_condition_type:axis==='conditions'?condition_type||'not_assessed':'',
    read_entire_source:true,review_stage:'one_reviewer_only_not_validated',
    reviewed_at:new Date().toISOString()}};
 }
 const csvCell=x=>'"'+String(x??'').replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"';
 const csv=(rows,columns)=>[columns.map(csvCell).join(','),...rows.map(x=>columns.map(c=>csvCell(x[c])).join(','))].join('\r\n');
 const API={CONFIG,field,key,counts,reviewDecision,csv};
 if(typeof module!=='undefined'&&module.exports)module.exports=API;
 if(!root.document)return;
 const $=id=>document.getElementById(id);
 if(!$('pp-status'))return;
 const el=(tag,cls,text)=>{const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=String(text);return x};
 const link=(label,uri)=>{const a=el('a','',label);a.href=uri;if(uri.startsWith('https:')){a.target='_blank';a.rel='noopener noreferrer'}return a};
 const tag=(t,w)=>el('span','kr-pill'+(w?' kr-risk':''),t);
 const alert=()=>el('div','pp-flag-note','Unverified allegation or concern in a public filing, not an established finding of fraud, ineligibility, misconduct, or wrongdoing. A filer may object to spending that is legally eligible.');
 const state={records:[],data:null,filtered:[],page:0,intersect:null,decisions:{},reviewer:'reviewer-1',auditSample:null};
 const STORAGE='erate-four-questions-review-v1';
 try{state.decisions=JSON.parse(localStorage.getItem(STORAGE)||'{}')||{}}catch(_){}
 const saved=()=>{try{localStorage.setItem(STORAGE,JSON.stringify(state.decisions));return true}catch(_){return false}};
 const clear=id=>{const x=$(id);x.replaceChildren();return x};
 const reviewer=()=>$('pp-reviewer').value.trim()||'reviewer-1';
 const current=(axis,id)=>state.decisions[key(reviewer(),axis,id)];
 const named=s=>String(s||'unknown').replaceAll('_',' ');
 function updateStats(){
  const ds=state.data,area=clear('pp-kpis');
  [[ds.source_records,'Filing records scanned'],[ds.readable_filings,'Readably sourced comments'],[ds.model_completed_filings,'Kaggle processed'],
  [Object.values(state.decisions).length,'Local one-reader decisions']].forEach(([v,label])=>{
    const k=el('div','kr-kpi');k.append(el('strong','',N(v)),el('span','',label));area.append(k);
  });
  $('pp-status').textContent='Scanned all '+N(ds.source_records)+' source filings. All shown automated category counts are UNADJUDICATED review candidates.';
 }
 function setAxis(){
  const axis=$('pp-axis').value,select=clear('pp-label');
  let all=el('option','','All candidate labels');all.value='';select.append(all);
  for(const [k,label] of Object.entries(CONFIG[axis].labels)){const x=el('option','',label);x.value=k;select.append(x)}
  state.intersect=null;state.page=0;render();
 }
 function axisCards(){
  const area=clear('pp-axes'),data=state.data;
  for(const axis of keys){
   const config=CONFIG[axis],card=el('div','pp-axis-card');
   card.append(el('h3','',config.name),el('p','kr-muted','Automated candidate flags, not validated endorsement or prevalence'));
   if(axis==='misuse')card.append(alert());
   for(const [label,name] of Object.entries(config.labels)){
    const count=data.candidate_filing_counts?.[axis]?.[label]||0,button=el('button','pp-flag');
    button.append(el('span','',name),el('b','',N(count)+' candidates'));
    button.onclick=()=>{$('pp-axis').value=axis;setAxis();$('pp-label').value=label;state.page=0;render();$('pp-coding').scrollIntoView({behavior:'smooth'})};
    card.append(button);
   }
   area.append(card);
  }
 }
 function overlapCards(){
  const area=clear('pp-overlap-cards');
  for(const [keyName,caption,axisB,labelB] of [
    ['screen_concern_and_restriction_candidate','Screen-harm concern + possible funding restriction','funding','targeted_restriction'],
    ['screen_concern_and_new_condition_candidate','Screen-harm concern + possible federal conditions','conditions','favor_new_federal_condition']]){
    const box=el('div','kr-card');
    box.append(el('p','pp-overlap',N(state.data.candidate_intersections?.[keyName]||0)),
      el('h3','',caption),el('p','kr-muted','Distinct filings with matching candidate cues for both topics, not confirmed joint endorsement.'));
    const btn=el('button','kr-action-button','Review candidate intersection');
    btn.onclick=()=>{
      $('pp-axis').value='screen_harms';setAxis();$('pp-label').value='affirmative_harm_concern';
      state.intersect={axis:axisB,label:labelB};state.page=0;render();$('pp-coding').scrollIntoView({behavior:'smooth'});
    };box.append(btn);area.append(box);
  }
 }
 function filter(){
  const axis=$('pp-axis').value,label=$('pp-label').value,role=$('pp-role').value,
    q=$('pp-search').value.trim().toLowerCase(),priority=$('pp-priority').value,scope=$('pp-scope').value;
  state.filtered=state.records.filter(row=>{
   const f=field(row,axis);
   if(label&&!f.candidate_labels.includes(label))return false;
   if(role&&row.role!==role)return false;
   if(scope&&row.model_semantic_scope!==scope)return false;
   if(state.intersect&&!field(row,state.intersect.axis).candidate_labels.includes(state.intersect.label))return false;
   if(priority==='candidate'&&!f.candidate_labels.length)return false;
   if(priority==='conflicts'&&f.candidate_labels.length<2)return false;
   if(priority==='selective'&&!row.ocr_candidate&&row.model_semantic_scope!=='prioritized_windows')return false;
   if(priority==='uncoded'&&current(axis,row.id))return false;
   if(priority==='audit_sample'&&(!state.auditSample?.[axis]||!state.auditSample[axis].has(String(row.id))))return false;
   if(q&&!([row.filer,row.id,row.role,...f.candidate_labels,...f.evidence.map(e=>e.quote+' '+(e.machine_requested_action||''))].join(' ').toLowerCase().includes(q)))return false;
   return true;
  }).sort((a,b)=>{
   const rank=x=>field(x,axis).candidate_labels.length*4+Number(x.ocr_candidate)*3+
       Number(x.model_semantic_scope==='prioritized_windows')*2+Number(!current(axis,x.id));
   return rank(b)-rank(a)||String(a.id).localeCompare(String(b.id));
  });
 }
 function sourceEvidence(row,axis,prior){
   const list=el('div','pp-sources');
   const data=field(row,axis).evidence||[];
   if(!data.length){list.append(el('p','kr-muted','No automatic source excerpt was extracted. Read the original filing and explain any no-position decision. Absence of a cue is NOT a validated negative.'));return list;}
   for(const [i,ev] of data.entries()){
    const card=el('div','pp-quote'),top=el('label','pp-source-head');
    const radio=el('input');radio.type='radio';radio.name='pp-evidence-'+axis+'-'+row.id;radio.value=String(i);
    radio.checked=Boolean(prior&&prior.source_offset===ev.start&&prior.source_origin===ev.origin);
    top.append(radio,document.createTextNode('Source at character '+N(ev.start)+' · '+named(ev.origin)+' · '+(CONFIG[axis].labels[ev.label]||ev.label)));
    card.append(top,el('p','',ev.quote));
    if(ev.machine_requested_action)card.append(el('p','kr-muted','Machine interpreted action (unvalidated): '+ev.machine_requested_action));
    if(ev.caution_flags?.length)card.append(el('p','pp-flag-note','Context check: '+ev.caution_flags.join(' · ').replaceAll('_',' ')));
    card.append(link('Read complete filing ↗',full(row.id)));list.append(card);
   }
   return list;
 }
 function reviewCard(row,axis,evidenceNode){
  const prior=current(axis,row.id),box=el('div','pp-review');
  box.append(el('h4','','Reviewer coding · '+CONFIG[axis].name),
    el('p','kr-muted','Select all statements actually endorsed by the filer. None selected means no discernible endorsed position after reading the full source.'));
  const choices=el('div','pp-review-grid');
  for(const [code,label] of Object.entries(CONFIG[axis].labels)){
   const x=el('label','pp-check'),input=el('input');input.type='checkbox';input.value=code;
   input.checked=Boolean(prior?.labels?.includes(code));x.append(input,document.createTextNode(label));choices.append(x);
  }
  box.append(choices);
  function additionalSelect(title,values,selectedValue){
    const wrapper=el('label','kr-muted',title),list=el('select');
    for(const [value,name] of values){
      const choice=el('option','',name);choice.value=value;list.append(choice);
    }
    list.value=selectedValue||values[0][0];wrapper.append(list);box.append(wrapper);
    return list;
  }
  let screenLink=null,conditionType=null,misuseType=null;
  if(axis==='funding'||axis==='conditions'||axis==='screen_harms'){
   screenLink=additionalSelect('Does this filer DIRECTLY link a screen-time harm concern to reducing or conditioning E-Rate?',[
    ['not_assessed','Not yet assessed'],['yes_explicit','Yes: explicit causal connection'],
    ['no','No direct causal connection'],['ambiguous','Possible link, but unclear'],
    ['not_applicable','Screen-time concerns not addressed here']
   ],prior?.screen_harm_to_funding_condition_link);
  }
  if(axis==='conditions'){
   conditionType=additionalSelect('What NEW mandatory federal condition is proposed, if any?',[
     ['not_assessed','Not assessed / no identified new condition'],
     ['screen_time_cap','Screen-time or daily-hour limits'],
     ['filtering_blocking','Content filtering / platform blocking'],
     ['monitoring','Student surveillance or monitoring requirements'],
     ['parental_choice','Parental opt-out or parental control'],
     ['educational_use','Education-purpose or outcomes limits'],
     ['other_child_safety','Other child-safety condition'],
     ['other','Other recipient condition']
   ],prior?.new_condition_type);
  }
  let legality=null;
  if(axis==='misuse'){
   misuseType=additionalSelect('What KIND of misuse does the filer assert, if any?',[
     ['not_assessed','Not assessed / no alleged event'],
     ['ineligible_costs','Ineligible spending or cost category'],
     ['improper_billing','Billing, reimbursement, or overcharging'],
     ['procurement','Bidding or procurement manipulation'],
     ['vendor_consultant_conflict','Vendor / consultant conflict or improper influence'],
     ['wifi_device_screen_use','Wi-Fi or device use objected to on educational grounds'],
     ['diversion_waste','Waste or diversion of funds'],
     ['other','Other claimed misuse']
   ],prior?.misuse_allegation_type);
  }
  if(axis==='misuse'){
   box.append(alert());
   const label=el('label','kr-muted','Does the filer allege wrongdoing, or object to use that may be lawful?');
   legality=el('select');
   for(const [v,text] of [
     ['not_assessed','Choose legal / normative distinction'],
     ['alleges_illegal_or_ineligible','Claims illegal, improper or ineligible spending'],
     ['normative_objection_not_illegal','Objects to spending without establishing a rules violation'],
     ['ambiguous','Unclear whether this is a rules violation allegation'],
     ['not_applicable','Hypothetical risk / no accusation']]){
     const op=el('option','',text);op.value=v;legality.append(op);
   }
   legality.value=prior?.misuse_legal_characterization||'not_assessed';label.append(legality);box.append(label);
  }
  const noteLabel=el('label','kr-muted','Reviewer rationale (required, including why the quote is endorsed rather than quoted as an opposing view)');
  const notes=el('textarea');notes.rows=3;notes.placeholder='Explain the filing’s actual requested outcome and context.';notes.value=prior?.explanation||'';
  noteLabel.append(notes);box.append(noteLabel);
  const readLabel=el('label','pp-check'),read=el('input');read.type='checkbox';read.checked=Boolean(prior?.read_entire_source);
  readLabel.append(read,document.createTextNode('I read the complete original filing, not just these automated excerpts.'));box.append(readLabel);
  const button=el('button','','Save this one-reader decision'),message=el('p','');
  button.onclick=()=>{
   const labels=[...choices.querySelectorAll('input:checked')].map(x=>x.value);
   const checked=evidenceNode.querySelector('input:checked'),source=checked?field(row,axis).evidence[Number(checked.value)]:null;
   const result=reviewDecision({reviewer:reviewer(),axis,id:row.id,labels,note:notes.value,source,read:read.checked,
     legal:legality?.value||'',screen_link:screenLink?.value||'not_assessed',
     condition_type:conditionType?.value||'not_assessed',misuse_type:misuseType?.value||'not_assessed'});
   if(!result.ok){message.className='pp-error';message.textContent=result.error;return}
   state.decisions[key(reviewer(),axis,row.id)]=result.value;
   message.className=saved()?'pp-saved':'pp-error';
   message.textContent=message.className==='pp-saved'?
      'Saved locally as reviewed once, NOT as an independently validated supporter count. Export your results.':
      'Could not save browser storage; export your decisions.';
   updateStats();
  };
  box.append(button,message);return box;
 }
 function makeCard(row,axis){
  const card=el('article','pp-filing'),f=field(row,axis),prior=current(axis,row.id);
  card.append(el('p','kr-eyebrow','Filing '+row.id),el('h3','',row.filer||'Filer not identified from indexed metadata'));
  const tags=el('div','pp-tags');tags.append(tag(named(row.role)),tag(f.candidate_labels.length+' candidate categories'));
  if(row.ocr_candidate)tags.append(tag('OCR candidate — check accuracy',true));
  if(row.model_semantic_scope==='prioritized_windows')tags.append(tag('Long filing: selective Kaggle reading',true));
  if(row.duplicate_count>1)tags.append(tag('Similar/duplicate submission indicator',true));
  if(prior)tags.append(tag('Reviewed once — not validated'));
  card.append(tags);
  const links=el('p','');links.append(link('FCC original ↗',fcc(row.id)),document.createTextNode(' · '),
   link('Full extracted text ↗',full(row.id)),document.createTextNode(' · '),
   link('Kaggle filing profile ↗','./kaggle.html?id='+encodeURIComponent(row.id)+'#filing'));card.append(links);
  if(axis==='misuse')card.append(alert());
  card.append(el('p','kr-muted',f.candidate_labels.length?
    'UNADJUDICATED candidate terms: '+f.candidate_labels.map(x=>CONFIG[axis].labels[x]).join(' · '):
    'No query candidate located — NOT independently classified as neutral.'));
  const ev=sourceEvidence(row,axis,prior);card.append(ev,reviewCard(row,axis,ev));return card;
 }
 function render(){
  if(!state.data)return;
  filter();
  const axis=$('pp-axis').value,per=Number($('pp-per').value)||15,pages=Math.max(1,Math.ceil(state.filtered.length/per));
  state.page=Math.min(Math.max(state.page,0),pages-1);
  const area=clear('pp-results');
  for(const row of state.filtered.slice(state.page*per,(state.page+1)*per))area.append(makeCard(row,axis));
  if(!state.filtered.length)area.append(el('p','kr-muted','No candidate filings match this filter. Try all filings; this is not a no-support finding.'));
  $('pp-count').textContent=N(state.filtered.length)+' candidate or matched filings · '+N(state.filtered.filter(x=>current(axis,x.id)).length)+' locally reviewed once. No independently validated support/opposition counts.';
  $('pp-page').textContent='Page '+(state.page+1)+' of '+pages;
  $('pp-prev').disabled=state.page===0;$('pp-next').disabled=state.page>=pages-1;
 }
 function download(){
  const entries=Object.values(state.decisions),columns=['filing_id','reviewer','axis','labels','review_stage','misuse_legal_characterization','source_offset','chosen_source_quote','explanation','read_entire_source','reviewed_at'];
  const rows=entries.map(x=>({...x,labels:(x.labels||[]).join(';')}));
  const blob=new Blob([csv(rows,columns)],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob),linkNode=el('a');linkNode.href=url;linkNode.download='erate_targeted_reviewer_decisions.csv';linkNode.click();
  setTimeout(()=>URL.revokeObjectURL(url),2000);
 }
 async function load(){
  for(const name of ['pp-label','pp-role','pp-priority','pp-scope','pp-per']){
   $(name).addEventListener('change',()=>{state.page=0;state.intersect=null;render()});
  }
  $('pp-axis').addEventListener('change',setAxis);
  $('pp-search').addEventListener('input',()=>{state.page=0;render()});
  $('pp-reviewer').addEventListener('change',()=>{state.page=0;render()});
  $('pp-prev').onclick=()=>{state.page--;render();$('pp-coding').scrollIntoView({behavior:'smooth'})};
  $('pp-next').onclick=()=>{state.page++;render();$('pp-coding').scrollIntoView({behavior:'smooth'})};
  $('pp-reset').onclick=()=>{$('pp-label').value='';$('pp-role').value='';$('pp-search').value='';
   $('pp-priority').value='candidate';$('pp-scope').value='';state.intersect=null;state.page=0;render()};
  $('pp-export').onclick=download;
  try{
   const response=await fetch('./data/kaggle/priority_position_candidates.json');
   if(!response.ok)throw Error('Full-corpus candidate index not published yet (HTTP '+response.status+')');
   const data=await response.json();
   if(data.source_records!==3231||data.readable_filings!==3230||data.model_completed_filings!==3230||
       data.status!=='UNADJUDICATED_RETRIEVAL_CANDIDATES_NOT_VOTES_NOT_CONFIRMED_MISCONDUCT'||
       !Array.isArray(data.filings)||data.filings.length!==3231)
      throw Error('Cannot verify a complete four-axis source-census dataset');
   state.data=data;state.records=data.filings;
   const roles=[...new Set(state.records.map(x=>x.role))].sort();
   for(const role of roles){const option=el('option','',named(role));option.value=role;$('pp-role').append(option)}
   setAxis();updateStats();axisCards();overlapCards();render();
   try{
    const ar=await fetch('./data/kaggle/priority_audit_sample.json');
    if(ar.ok){const audited=await ar.json();if(audited.source_filings===3230&&audited.strata?.length===16){
      state.auditSample={};for(const axis of keys)state.auditSample[axis]=new Set();
      for(const entry of audited.assignments||[])if(state.auditSample[entry.axis])state.auditSample[entry.axis].add(String(entry.filing_id));
      if($('pp-priority').value==='audit_sample')render();
    }}
   }catch(_){/* Sample is additive; the all-filing review is independently functional. */}
  }catch(err){$('pp-status').className='kr-status pp-error';$('pp-status').textContent='The full-source data is not yet available: '+err.message+'. Caution: no incomplete counts will be shown as final.';}
 }
 load();
})(typeof window!=='undefined'?window:typeof globalThis!=='undefined'?globalThis:{});
