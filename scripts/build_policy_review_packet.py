#!/usr/bin/env python3
"""Create a private offline, human-centered review packet for FCC proposal positions.

Source text, excerpts, coder data and review forms remain on the local Mac.
A sampled review is not a census and not representative without weighting.
"""
from __future__ import annotations
import argparse, html, json, random, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv, sha256, normalized_text

POSITIONS=[
  ('','Choose a result'),
  ('support','Support the FCC policy option'),
  ('oppose','Oppose the FCC policy option'),
  ('conditional_or_amend','Support only with conditions or amendments'),
  ('alternative_proposal','Advocates a different regulatory approach'),
  ('discussion_no_position','Discusses the question, no discernible position'),
  ('unclear','Cannot determine'),
  ('not_addressed','Not addressed in this filing')
]
REASONS=['statutory_authority','budget_cost_efficiency','access_affordability_equity',
 'education_effectiveness','child_safety','parental_autonomy','privacy_free_expression',
 'administrative_burden','competition_market_effects','fraud_integrity',
 'implementation_feasibility','evidence_quality','other']
ROLES=['unknown','school_district','school_staff','library','parent_guardian',
       'student','telecom_provider','vendor','consultant','advocacy_group',
       'researcher','government','individual_other','other_organization']


def make_review_sample(queue: list[dict], all_filings: list[dict],
                       provisions: list[dict], per_provision: int,
                       negative_controls: int, seed: int) -> list[dict]:
    """Deterministic broad-topic candidate sample plus random keyword negatives."""
    rng=random.Random(seed)
    by_prov=defaultdict(list)
    found=set()
    for r in queue:
        key=(r['submission_id'],r['provision_id'])
        if key in found:
            raise ValueError('Duplicate retrieval queue filing/provision pair')
        found.add(key)
        by_prov[r['provision_id']].append(r)
    result=[]
    for p in provisions:
        pool=sorted(by_prov[p['id']],key=lambda r:r['submission_id'])
        rng.shuffle(pool)
        result.extend(pool[:per_provision])
    valid=[r for r in all_filings if r.get('augmented_chars','0').isdigit()
           and int(r['augmented_chars'])>0 and r.get('agency_record_candidate')=='0']
    potential=[]
    # Uniform over provisions and filings; not a statistical survey.
    for p in provisions:
        for row in valid:
            key=(row['submission_id'],p['id'])
            if key not in found:
                potential.append({
                    'submission_id':row['submission_id'],
                    'provision_id':p['id'],
                    'source_url':row['source_url'],
                    'matched_terms':'',
                    'ocr_candidate':row.get('has_unreviewed_ocr','0'),
                    'selection_stratum':'keyword_negative_control'
                })
    rng.shuffle(potential)
    used={(r['submission_id'],r['provision_id']) for r in result}
    for r in potential:
        key=(r['submission_id'],r['provision_id'])
        if key not in used:
            result.append(r);used.add(key)
        if len(result)>=len(used) and sum(x.get('selection_stratum')=='keyword_negative_control' for x in result)>=negative_controls:
            break
    for r in result:
        r.setdefault('selection_stratum','keyword_candidate')
    return result


def build(corpus: Path, snapshot_id: str = 'ocr_candidate_v1',
          per_provision: int = 3, negative_controls: int = 15,
          chars_per_document: int = 15000, seed: int = 20261020) -> tuple[Path,int]:
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',snapshot_id):
        raise ValueError('Invalid snapshot identifier')
    if not 1<=per_provision<=10 or not 0<=negative_controls<=60:
        raise ValueError('Invalid sample sizes')
    if not 1000<=chars_per_document<=100000:
        raise ValueError('Invalid preview length')
    root=Path(__file__).resolve().parents[1]
    book=json.loads((root/'analysis_methods/provision_codebook_v1.json').read_text())
    by_id={p['id']:p for p in book['provisions']}
    snap=corpus.expanduser().resolve()/'analysis_observatory'/f'research_snapshot_{snapshot_id}'
    source=snap/'ocr_augmented_text'
    inventory,_=read_csv(snap/'research_inventory.csv')
    q,_=read_csv(snap/'policy_analysis_augmented/review_queue_GENERATED.csv')
    inv={r['submission_id']:r for r in inventory}
    reviewed=make_review_sample(q,inventory,book['provisions'],
                                per_provision,negative_controls,seed)
    panels=[]
    for i,r in enumerate(reviewed,1):
        sid=r['submission_id'];pid=r['provision_id']
        p=by_id[pid]
        text_path=source/f'{sid}.txt'
        if not text_path.is_file():
            raise FileNotFoundError('Missing review text: '+str(text_path))
        text=text_path.read_text(encoding='utf-8-sig').strip()
        if sha256(normalized_text(text).encode())!=inv[sid]['augmented_sha256']:
            raise ValueError('Snapshot source text hash mismatch: '+sid)
        preview=text[:chars_per_document]
        shortened=len(text)>chars_per_document
        opts=''.join('<option value="'+html.escape(val,quote=True)+'">'+html.escape(label)+'</option>' for val,label in POSITIONS)
        reasons=''.join('<option value="'+html.escape(val)+'">'+html.escape(val.replace('_',' '))+'</option>' for val in REASONS)
        roles=''.join('<option value="'+html.escape(val)+'">'+html.escape(val.replace('_',' '))+'</option>' for val in ROLES)
        link=r.get('source_url') or inv[sid]['source_url']
        if not re.fullmatch(r'https://www\.fcc\.gov/ecfs/[^"<> ]+',link):link=''
        link_html=('<a target="_blank" rel="noopener noreferrer" href="'+html.escape(link,quote=True)+'">FCC source filing ↗</a>') if link else 'FCC source link not available'
        panels.append(
            '<article class="review" data-sid="'+html.escape(sid,quote=True)+'" data-provision="'+html.escape(pid,quote=True)+'">'
            '<div class="eyebrow">Review '+str(i)+' / '+str(len(reviewed))+' · '+html.escape(r['selection_stratum'])+'</div>'
            '<h2>'+html.escape(p['label'])+'</h2>'
            '<p class="policy">Policy option: '+html.escape(p['policy_option'])+'</p>'
            '<p class="small">FCC paragraph group '+html.escape(p['notice_paragraph_range'])
            +' · Filing '+html.escape(sid)+' · '+link_html
            +' · Retrieved terms: '+html.escape(r.get('matched_terms') or 'none — negative-control sample')
            +' · OCR candidate: '+html.escape(r.get('ocr_candidate','0'))+'</p>'
            '<details open><summary>Read filing text (possibly truncated in the viewer)</summary>'
            '<pre class="text">'+html.escape(preview)+'</pre>'
            +('<p>Preview is truncated. Open the original FCC filing before declaring an issue absent or reviewing text beyond the preview.</p>' if shortened else '')
            +'</details>'
            '<div class="form-grid">'
            '<label>Position<select class="position">'+opts+'</select></label>'
            '<label>Stakeholder role<select class="role">'+roles+'</select></label>'
            '<label>Reason category<select class="reason"><option value="">Choose reason</option>'+reasons+'</select></label>'
            '<label>Requested FCC action<textarea class="requested_action" rows="2" placeholder="Adopt, reject, narrow, amend, alternative…"></textarea></label>'
            '<label>Commenter rationale<textarea class="rationale" rows="2" placeholder="Why is the commenter asking for this?"></textarea></label>'
            '<label>Exact quote supporting your position<textarea class="quote" rows="2" placeholder="Copy an exact contiguous quote from the source text"></textarea></label>'
            '<label>Evidence for stakeholder role<textarea class="stakeholder_evidence" rows="2"></textarea></label>'
            '<label>Notes / possible OCR problems<textarea class="notes" rows="2"></textarea></label>'
            '</div></article>'
        )
    css='''
body{font:15px/1.5 system-ui,-apple-system,sans-serif;background:#f5f7fa;color:#17283c;max-width:1300px;margin:auto;padding:20px}
header{background:#fff;border:1px solid #cbd5de;padding:18px;position:sticky;top:0;z-index:3;border-radius:6px}
header h1{margin:0;font-size:24px}header p{margin:5px 0 10px;color:#526579}
button{padding:9px 15px;border:0;border-radius:5px;background:#175a80;color:white;font-weight:700;cursor:pointer}
input,select,textarea{font:inherit;padding:9px;border:1px solid #becbd5;border-radius:4px;width:100%;background:white}
input{max-width:220px}
.review{background:white;border:1px solid #cbd5de;border-radius:7px;padding:19px;margin:22px 0}
.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#416680;font-weight:750}
h2{font-size:21px;margin:7px 0}.policy{font-weight:650}.small{font-size:13px;color:#53677b}
details{margin:14px 0;background:#fafbfc;border:1px solid #e2e8ee;padding:11px}
summary{cursor:pointer;font-weight:bold}.text{font:13px/1.55 ui-monospace,monospace;white-space:pre-wrap;word-wrap:break-word;max-height:380px;overflow:auto}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.form-grid label{display:flex;flex-direction:column;gap:5px;font-weight:650}
@media(max-width:720px){.form-grid{grid-template-columns:1fr}header{position:relative}}
'''
    script=r'''
const q=(root,cls)=>root.querySelector('.'+cls);
const quote=x=>'"'+String(x||'').replace(/"/g,'""')+'"';
document.getElementById('save').addEventListener('click',()=>{
  const rows=[['submission_id','provision_id','position','review_status','coder_id',
    'requested_action','rationale','reason_families','stakeholder_role',
    'stakeholder_evidence','evidence_quote','notes']];
  const reviewer=document.getElementById('coder').value.trim();
  if(!reviewer){alert('Enter a reviewer ID before exporting.');return;}
  for(const box of document.querySelectorAll('.review')){
    const position=q(box,'position').value;
    if(!position)continue;
    rows.push([box.dataset.sid,box.dataset.provision,position,'manual_reviewed',reviewer,
      q(box,'requested_action').value,q(box,'rationale').value,q(box,'reason').value,
      q(box,'role').value,q(box,'stakeholder_evidence').value,q(box,'quote').value,
      q(box,'notes').value]);
  }
  if(rows.length===1){alert('Choose and complete at least one position.');return;}
  const blob=new Blob([rows.map(r=>r.map(quote).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);a.download='fcc_policy_human_reviews.csv';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),1000);
});
'''
    page=(
      '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Private FCC evidence review</title>'
      '<meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'</style></head><body>'
      '<header><h1>Private FCC position and rationale review</h1>'
      '<p>Read the actual filing, then record the requested action and supporting evidence. This is a stratified exploratory sample, not an estimate of public opinion. Browser edits disappear on refresh: export often.</p>'
      '<label>Reviewer ID <input id="coder" placeholder="e.g. researcher_1"></label> '
      '<button id="save">Export reviewed rows to CSV</button></header>'
      +''.join(panels)+'<script>'+script+'</script></body></html>')
    dest=snap/'policy_analysis_augmented'/'private_review_packet.html'
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(page,encoding='utf-8')
    return dest,len(reviewed)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--per-provision',type=int,default=3)
    p.add_argument('--negative-controls',type=int,default=15)
    p.add_argument('--max-preview-chars',type=int,default=15000)
    a=p.parse_args()
    path,n=build(a.corpus,a.snapshot_id,a.per_provision,
                 a.negative_controls,a.max_preview_chars)
    print(f'Generated private evidence review packet: {path} ({n} review questions)')
    print('Open locally: open '+str(path))
    print('Never commit the page to public GitHub: it embeds FCC source text.')


if __name__=='__main__':
    main()
