'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const N = n => Number(n || 0).toLocaleString('en-US');
  const BASE = './data/full_text_shards/';
  let index, byId = new Map(), current = [], selected = '', page = 0;
  let hits = null, running = false, controller = null;
  const cache = new Map();
  const PAGE_SIZE = 35;
  const text = (id, value) => { $(id).textContent = String(value); };
  const button = (label, onclick, className = '') => {
    const b = document.createElement('button'); b.textContent = label;
    b.type = 'button'; b.className = className; b.onclick = onclick; return b;
  };
  function isMissing(r) { return !r.has_text; }
  function sourceUrl(r) {
    const u = String(r.source_url || '');
    return /^https:\/\/www\.fcc\.gov\/ecfs\/filing\/\d+$/.test(u)
      ? u : 'https://www.fcc.gov/ecfs/filing/' + encodeURIComponent(r.submission_id);
  }
  function link(label, url, download = false) {
    const a = document.createElement('a');
    a.textContent = label; a.href = url; a.target = '_blank';
    a.rel = 'noopener noreferrer'; if (download) a.download = '';
    return a;
  }
  // Browsers may deliver .gz with Content-Encoding already decoded.
  // Look at the actual first bytes before creating the decompression stream.
  async function records(shard, signal, visit) {
    const response = await fetch(BASE + encodeURIComponent(shard), {signal});
    if (!response.ok || !response.body) throw Error('Could not load corpus shard ' + shard + ' (HTTP ' + response.status + ')');
    const reader = response.body.getReader();
    const first = await reader.read();
    if (first.done) throw Error('Empty corpus shard: ' + shard);
    const start = first.value;
    const source = new ReadableStream({
      start(control) { control.enqueue(start); },
      async pull(control) {
        const x = await reader.read();
        if (x.done) control.close(); else control.enqueue(x.value);
      },
      cancel(reason) { reader.cancel(reason); }
    });
    const gzip = start[0] === 31 && start[1] === 139;
    if (gzip && typeof DecompressionStream === 'undefined')
      throw Error('This browser cannot open compressed corpus files. Please update your browser.');
    const stream = gzip ? source.pipeThrough(new DecompressionStream('gzip')) : source;
    const decoded = stream.getReader(), decoder = new TextDecoder();
    let unfinished = '';
    const consume = async line => {
      if (line.trim()) await visit(JSON.parse(line));
    };
    try {
      for (;;) {
        const next = await decoded.read();
        if (next.done) break;
        unfinished += decoder.decode(next.value, {stream:true});
        let cut;
        while ((cut = unfinished.indexOf('\n')) !== -1) {
          const one = unfinished.slice(0, cut);
          unfinished = unfinished.slice(cut+1);
          await consume(one);
        }
      }
      unfinished += decoder.decode();
      await consume(unfinished);
    } finally {
      try { decoded.releaseLock(); } catch (_) {}
    }
  }
  function rowsForView() {
    const query = $('corpus-filter').value.trim().toLocaleLowerCase();
    const hasText = $('corpus-text-filter').value;
    const ocr = $('corpus-ocr').value;
    const sort = $('corpus-sort').value;
    const result = index.filings.filter(r => {
      if (hits && !hits.has(r.submission_id)) return false;
      if (query && !(r.submission_id.includes(query) ||
          String(r.filer_raw || '').toLocaleLowerCase().includes(query))) return false;
      if (hasText === 'text' && isMissing(r)) return false;
      if (hasText === 'missing' && !isMissing(r)) return false;
      if (ocr && (String(r.has_unreviewed_ocr) === '1') !== (ocr === 'yes')) return false;
      return true;
    });
    result.sort((a,b) => {
      if (sort === 'longest') return b.chars-a.chars || a.submission_id.localeCompare(b.submission_id);
      if (sort === 'shortest') return a.chars-b.chars || a.submission_id.localeCompare(b.submission_id);
      if (sort === 'id') return a.submission_id.localeCompare(b.submission_id);
      return String(b.date_submission).localeCompare(String(a.date_submission)) ||
        b.submission_id.localeCompare(a.submission_id);
    });
    return result;
  }
  function renderList() {
    if (!index) return;
    current = rowsForView();
    const pages = Math.max(1, Math.ceil(current.length/PAGE_SIZE));
    page = Math.max(0, Math.min(page, pages-1));
    text('corpus-count', N(current.length) + ' matching filing records');
    text('corpus-page', 'Page '+(page+1)+' of '+pages);
    $('corpus-prev').disabled = page===0;
    $('corpus-next').disabled = page >= pages-1;
    const box = $('corpus-results');
    box.replaceChildren();
    for (const r of current.slice(page*PAGE_SIZE, (page+1)*PAGE_SIZE)) {
      const b=button('',()=>openRecord(r.submission_id),'corpus-item');
      b.setAttribute('aria-current',r.submission_id===selected ? 'true':'false');
      const name = document.createElement('strong');
      name.textContent = r.filer_raw || 'Filing '+r.submission_id;
      const small = document.createElement('small');
      small.textContent = r.submission_id+' · '+(r.date_submission || 'Undated')+' · '+
        N(r.chars)+' characters'+(isMissing(r)?' · NO TEXT':'')+
        (String(r.has_unreviewed_ocr)==='1'?' · OCR candidate':'');
      b.append(name,small);
      if (hits && hits.has(r.submission_id)) {
        const excerpt = document.createElement('span'); excerpt.className = 'excerpt';
        excerpt.textContent = hits.get(r.submission_id);
        b.append(excerpt);
      }
      box.append(b);
    }
    if (!current.length) {
      const p=document.createElement('p'); p.className='corpus-muted';
      p.style.padding='1rem'; p.textContent='No filings match these filters.'; box.append(p);
    }
  }
  function shardName(id) { return byId.get(id)?.shard; }
  async function getRecord(id) {
    const shard=shardName(id);
    if (!shard) throw Error('Filing was not found in the public index');
    if (!cache.has(shard)) {
      const items = new Map();
      await records(shard, undefined, async row => { items.set(String(row.submission_id), row); });
      cache.clear(); // At most one decompressed shard in browser memory.
      cache.set(shard, items);
    }
    const row=cache.get(shard).get(id);
    if (!row) throw Error('Filing was indexed but missing from source shard');
    return row;
  }
  async function openRecord(id, push=true) {
    const info=byId.get(id);
    if (!info) return;
    selected=id;
    renderList();
    text('corpus-reader-title',info.filer_raw || 'FCC filing '+id);
    $('corpus-reader-meta').replaceChildren();
    for (const item of [id,info.date_submission || 'Date unavailable',
      N(info.words)+' words', String(info.has_unreviewed_ocr)==='1'?'Contains OCR candidate text':'Source text']) {
      const e=document.createElement('span');e.textContent=item;
      $('corpus-reader-meta').append(e);
    }
    const links=$('corpus-reader-links'); links.replaceChildren();
    links.append(link('Original FCC filing ↗',sourceUrl(info)));
    links.append(link('Download compressed source shard ↗',BASE+encodeURIComponent(info.shard),true));
    $('corpus-reader-text').hidden=true;
    text('corpus-reader-status',info.has_text?'Retrieving entire extracted filing…':'This filing has no recovered text in the source snapshot.');
    if(push)history.pushState(null,'','?id='+encodeURIComponent(id));
    if(!info.has_text)return;
    try{
      const row=await getRecord(id);
      if(selected!==id)return;
      if(!row.text) throw Error('Expected source text is missing');
      if(String(row.text_sha256||'')!==String(info.source_sha256||''))
        throw Error('Filing SHA-256 metadata disagrees with the public index');
      text('corpus-reader-status','Complete extracted filing text, '+N(row.text.length)+' characters. This is not an LLM summary.');
      $('corpus-reader-text').textContent=row.text; // Never interpret source HTML/JS.
      $('corpus-reader-text').hidden=false;
    }catch(e){if(selected===id)text('corpus-reader-status','Unable to load full text: '+e.message);}
  }
  async function searchFull() {
    if(running)return;
    const phrase=$('corpus-full-query').value.trim().toLocaleLowerCase();
    if(!phrase){
      hits=null;page=0;renderList();
      text('corpus-search-status','Enter words to search across every comment, or leave empty to clear a previous search.');
      return;
    }
    hits=new Map();running=true;controller=new AbortController();
    const b=$('corpus-search-full');b.disabled=true;b.textContent='Searching…';
    text('corpus-search-status','Searching all text shards…');
    try{
      let done=0, scanned=0;
      for(const spec of index.shards){
        await records(spec.name,controller.signal, async r=>{
          scanned++;
          if(typeof r.text==='string' && r.text.toLocaleLowerCase().includes(phrase)){
            const location=r.text.toLocaleLowerCase().indexOf(phrase);
            const lo=Math.max(0,location-100),hi=Math.min(r.text.length,location+phrase.length+130);
            hits.set(String(r.submission_id),(lo?'…':'')+
              r.text.slice(lo,hi).replace(/\s+/g,' ')+(hi<r.text.length?'…':''));
          }
        });
        done++;text('corpus-search-status','Searched '+done+' of '+index.shards.length+
          ' shards · '+N(scanned)+' filings scanned · '+N(hits.size)+' matches');
      }
      page=0;renderList();
      text('corpus-search-status','Finished exact full-text search: '+N(hits.size)+
        ' matching filings out of '+N(scanned)+' indexed records.');
    }catch(e){
      text('corpus-search-status','Search stopped before completion: '+e.message+
        '. Partial results are not a full-corpus count. Retry to search all shards.');
      hits=null;renderList();
    }finally{
      running=false;b.disabled=false;b.textContent='Search full texts';controller=null;
    }
  }
  async function main() {
    try {
      const r=await fetch('./data/full_corpus_index.json',{cache:'no-store'});
      if(!r.ok)throw Error('Full-text website data is not published yet (HTTP '+r.status+')');
      index=await r.json();
      if(!Array.isArray(index.filings) || index.filings.length!==index.records)
        throw Error('Incomplete public filing index');
      byId = new Map(index.filings.map(r=>[String(r.submission_id),r]));
      if(byId.size!==index.records) throw Error('Duplicate filing identifiers in index');
      const box=$('corpus-stats');
      for(const label of [
        N(index.records)+' filing records',N(index.records_with_text)+' readable texts',
        N(index.records_without_text)+' missing text',Math.round(index.compressed_bytes/1e6)+' MB source archive'
      ]) {const e=document.createElement('span');e.textContent=label;box.append(e);}
      text('corpus-loading','Complete index loaded. All available source texts can be read below.');
      for(const id of ['corpus-filter','corpus-text-filter','corpus-ocr','corpus-sort']){
        $(id).addEventListener(id==='corpus-filter'?'input':'change',()=>{page=0;renderList();});
      }
      $('corpus-prev').onclick=()=>{page--;renderList();};
      $('corpus-next').onclick=()=>{page++;renderList();};
      $('corpus-search-full').onclick=searchFull;
      $('corpus-full-query').addEventListener('keydown',event=>{if(event.key==='Enter')searchFull();});
      window.addEventListener('popstate',()=>{
        const id=new URLSearchParams(location.search).get('id');
        if(id && byId.has(id))openRecord(id,false);
      });
      renderList();
      const id=new URLSearchParams(location.search).get('id');
      if(id&&byId.has(id))await openRecord(id,false);
    } catch(e) {
      text('corpus-loading','The full corpus explorer is not ready yet: '+e.message+
        '. Existing source comments remain downloadable in the public GitHub repository.');
    }
  }
  document.addEventListener('DOMContentLoaded', main);
})();
