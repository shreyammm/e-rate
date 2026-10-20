'use strict';
// Applies a full-text role review layer to the existing public ECFS filing index.
// Refuses to attach any labels unless the ordered filing IDs match the analyzed snapshot.
window.applyFullTextRoles=async function(records,summary,labels){
  const response=await fetch('./data/full_text_role_codes.json',{cache:'no-store'});
  if(!response.ok)throw new Error('Full-text role data unavailable');
  const data=await response.json();
  if(records.length!==summary.indexed_filings||data.snapshot!=='ocr_candidate_v1')
    throw new Error('Role data count or snapshot mismatch');
  const encoder=new TextEncoder();
  const digest=new Uint8Array(await crypto.subtle.digest(
    'SHA-256',encoder.encode(records.map(r=>r.id).join('\n'))));
  const sha=[...digest].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(sha!==data.id_order_sha256)throw new Error('Role data filing-order hash mismatch');
  async function decompress(encoded){
    if(typeof DecompressionStream==='undefined')throw new Error('Unsupported browser decompression');
    const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
    const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'));
    return new TextDecoder().decode(await new Response(stream).arrayBuffer());
  }
  const [roles,levels]=await Promise.all([
    decompress(data.role_codes_deflate_b64),decompress(data.confidence_codes_deflate_b64)
  ]);
  if(roles.length!==records.length||levels.length!==records.length)
    throw new Error('Role classification length mismatch');
  // Validate all codes before altering even one row.
  const mapped=records.map((row,i)=>({
    id:data.role_keys[roles[i]],confidence:data.confidence_keys[levels[i]]
  }));
  if(mapped.some(x=>!x.id||!x.confidence))throw new Error('Unknown role or certainty code');
  const count={};const matrix={};
  for(const issue of summary.issues)matrix[issue.id]={};
  for(let i=0;i<records.length;i++){
    const row=records[i],role=mapped[i].id;
    row.role=role;row.role_confidence=mapped[i].confidence;
    count[role]=(count[role]||0)+1;
    for(let j=0;j<summary.issues.length;j++){
      if(Number(row.issues)&(1<<j)){
        const issue=summary.issues[j].id;
        matrix[issue][role]=(matrix[issue][role]||0)+1;
      }
    }
  }
  const order=['school_district','library','parent_guardian','advocacy_nonprofit',
    'government','tribal_government','telecom_provider','consultant',
    'business_other','individual_public','unresolved'];
  summary.roles=order.map(id=>({
    id,label:labels[id]||id,filings:count[id]||0,
    distinct_filer_fields:data.distinct_filer_fields_by_role[id]||0
  })).sort((a,b)=>b.filings-a.filings);
  summary.issue_role_matrix=matrix;
  summary.role_method=data.method;
  summary.role_provenance='Full-text candidate classification, not independently adjudicated';
  return true;
};