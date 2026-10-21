'use strict';
/* Evidence navigator: operates on the *complete* lexical-hit set emitted by
   Ask the Corpus after a verified all-shard scan, not the model context. */
(() => {
  const $=id=>document.getElementById(id);
  const fmt=n=>Number(n||0).toLocaleString('en-US',{maximumFractionDigits:1});
  const nice=s=>String(s||'Unresolved').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
  const elem=(tag,cl,text)=>{const x=document.createElement(tag);if(cl)x.className=cl;if(text!==undefined)x.textContent=String(text);return x};
  const link=(title,url)=>{const a=elem('a','',title);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a};
  let full=null,evidence=[],lookup=null,indexPromise=null,offset=0;
  const pageSize=40;
  const index=async()=>{
    if(!indexPromise)indexPromise=fetch('./data/corpus_index.json').then(r=>{if(!r.ok)throw Error('Missing filing characteristics');return r.json()}).then(data=>{
      if(!Array.isArray(data.filings))throw Error('Invalid filing characteristics');
      return new Map(data.filings.map(d=>[String(d.id),d]));
    });
    return indexPromise;
  };
  const select=(id,options)=>{const el=$(id);el.replaceChildren();for(const [value,label] of options){const o=elem('option','',label);o.value=value;el.append(o)}};
  function candidates(){
    if(!full)return [];
    const role=$('ev-role').value,ocr=$('ev-ocr').value,sort=$('ev-order').value,needle=$('ev-find').value.toLowerCase().trim();
    const date=$('ev-date').value,kind=$('ev-coverage').value;
    const filtered=full.candidates.filter(r=>{
      const m=lookup?.get(r.id);
      if(role && (m?.role||'unresolved')!==role)return false;
      if(ocr==='candidate'&&!r.ocr)return false;
      if(ocr==='native'&&r.ocr)return false;
      if(date && !String(r.date||'').startsWith(date))return false;
      if(kind==='multi' && !(r.passages||[]).some(p=>p.coverage>=2))return false;
      if(needle && ![r.id,r.filer,...(r.passages||[]).map(p=>p.quote)].join(' ').toLowerCase().includes(needle))return false;
      return true;
    });
    filtered.sort((a,b)=>{
      if(sort==='oldest')return String(a.date).localeCompare(String(b.date))||b.score-a.score;
      if(sort==='recent')return String(b.date).localeCompare(String(a.date))||b.score-a.score;
      if(sort==='filer')return a.filer.localeCompare(b.filer)||b.score-a.score;
      if(sort==='least-copied')return (lookup?.get(a.id)?.duplicate_count||1)-(lookup?.get(b.id)?.duplicate_count||1)||b.score-a.score;
      return b.score-a.score||a.id.localeCompare(b.id);
    });
    return filtered;
  }
  function exportCSV(rows){
    const csv=v=>'"'+String(v??'').replace(/^[=+@\-\t\r]/,"'$&").replaceAll('"','""')+'"';
    const out=[['filing_id','date','provisional_category','ocr_candidate','exact_text_family_size','retrieval_score','snippet','fcc_url'].join(',')];
    for(const r of rows){
      const d=lookup?.get(r.id)||{};
      out.push([r.id,r.date,d.role||'unresolved',r.ocr?1:0,d.duplicate_count??'',r.score,r.passages?.[0]?.quote||'','https://www.fcc.gov/ecfs/filing/'+r.id].map(csv).join(','));
    }
    const url=URL.createObjectURL(new Blob([out.join('\n')],{type:'text/csv;charset=utf-8'}));
    const a=elem('a');a.href=url;a.download='fcc_ask_corpus_evidence.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function chart(target,entries,max){
    $(target).replaceChildren();
    entries.forEach(([name,value])=>{
      const row=elem('div','ev-stat-row'),nameEl=elem('span','',name),bar=elem('div','ev-stat-track'),fill=elem('div','ev-stat-fill'),n=elem('strong','',fmt(value));
      fill.style.width=(max?100*value/max:0)+'%';bar.append(fill);row.append(nameEl,bar,n);$(target).append(row);
    });
  }
  function update(){
    if(!full)return;
    const hits=candidates(),total=full.candidates.length;
    $('ev-count').textContent=fmt(hits.length)+' visible filing records out of '+fmt(total)+' lexical candidates; '+fmt(full.scanned)+' source filings scanned.';
    $('ev-export').disabled=hits.length===0;
    const matchedNames=new Set(hits.map(r=>r.filer.trim().toLowerCase()).filter(Boolean));
    const dup=hits.filter(r=>(Number(lookup?.get(r.id)?.duplicate_count)||1)>1).length;
    const familyEquivalent=hits.reduce((n,r)=>n+1/Math.max(1,Number(lookup?.get(r.id)?.duplicate_count)||1),0);
    $('ev-quality').textContent=fmt(matchedNames.size)+' distinct exact nonempty filer strings; '+fmt(dup)+' records in repeated exact-text families; fractional text-family equivalent '+fmt(familyEquivalent)+'. None are validated unique-person counts.';
    const byRole=new Map(),byDay=new Map();
    for(const r of hits){
      const role=nice(lookup?.get(r.id)?.role||'unresolved');
      byRole.set(role,(byRole.get(role)||0)+1);
      if(r.date){const d=r.date.slice(0,10);byDay.set(d,(byDay.get(d)||0)+1);}
    }
    const roles=[...byRole].sort((a,b)=>b[1]-a[1]).slice(0,12);
    const dates=[...byDay].sort((a,b)=>b[1]-a[1]).slice(0,12);
    chart('ev-roles',roles,Math.max(1,...roles.map(r=>r[1])));
    chart('ev-dates',dates,Math.max(1,...dates.map(r=>r[1])));
    const host=$('ev-results');host.replaceChildren();
    const shown=hits.slice(0,offset+pageSize);
    for(const r of shown){
      const card=elem('article','ev-hit');
      const m=lookup?.get(r.id)||{};
      const head=elem('div','ev-hit-title');
      head.append(link(r.filer||'FCC filing '+r.id,'./corpus.html?id='+encodeURIComponent(r.id)));
      head.append(elem('span','ask-small',String(r.date||'Date unknown')+' · '+nice(m.role||'unresolved')+(r.ocr?' · OCR candidate':'')));
      const p=r.passages?.[0];
      const quote=elem('blockquote','ev-excerpt',p?.quote||'No source excerpt');
      const links=elem('div','ask-source-links');
      links.append(link('Full text ↗','./corpus.html?id='+encodeURIComponent(r.id)),link('Original FCC filing ↗','https://www.fcc.gov/ecfs/filing/'+encodeURIComponent(r.id)),link('Find similar filings ↗','./similar.html?id='+encodeURIComponent(r.id)));
      card.append(head,quote,links);
      host.append(card);
    }
    $('ev-more').hidden=shown.length>=hits.length;
    $('ev-pages').textContent=fmt(shown.length)+' of '+fmt(hits.length)+' matching records shown.';
    $('ev-export').onclick=()=>exportCSV(hits);
    $('ev-all-link').textContent='Browse the entire extracted-text corpus ↗';
  }
  const onFilter=()=>{offset=0;update()};
  ['ev-role','ev-ocr','ev-order','ev-date','ev-coverage'].forEach(id=>$(id).addEventListener('change',onFilter));
  $('ev-find').addEventListener('input',onFilter);
  $('ev-more').addEventListener('click',()=>{offset+=pageSize;update()});
  $('ev-clear').addEventListener('click',()=>{for(const id of ['ev-role','ev-ocr','ev-date','ev-coverage','ev-find'])$(id).value='';$('ev-order').value='relevance';offset=0;update()});
  window.addEventListener('erate:scan-complete',async e=>{
    full=e.detail.found;evidence=e.detail.evidence;offset=0;
    $('ev-status').textContent='Full search finished. Loading metadata for categorical analysis…';
    try{lookup=await index();}catch(err){lookup=new Map();$('ev-status').textContent='Metadata unavailable ('+err.message+'); filing-level evidence remains accessible.';}
    const types=[...new Set(full.candidates.map(r=>lookup?.get(r.id)?.role||'unresolved'))].sort();
    select('ev-role',[['','All provisional commenter categories'],...types.map(x=>[x,nice(x)])]);
    const months=[...new Set(full.candidates.map(r=>String(r.date||'').slice(0,7)).filter(Boolean))].sort();
    select('ev-date',[['','All filing months'],...months.map(x=>[x,x])]);
    if(lookup.size)$('ev-status').textContent='Evidence navigator ready. All lexical candidates available independently of AI.';
    $('ev-navigator').hidden=false;update();
  });
})();