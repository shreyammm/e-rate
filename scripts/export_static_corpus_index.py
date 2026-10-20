#!/usr/bin/env python3
"""Build a public-safe, per-filing FCC index for a static GitHub Pages explorer.

No filing texts, emails, phone numbers, person-name fields, or OCR transcripts
are published. The index contains filing IDs, official URLs, dates, provisional
affiliation cues, issue mentions and counts. Source remains the original FCC.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from erate.engine import read_csv, normalized_text, sha256

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'docs/data'
ISSUES={
 'sunset_or_narrow':['sunset','eliminat','terminat','phase out','phase-out','ending the e-rate','end the e-rate','e-rate funding cuts','reduce e-rate'],
 'cipa_filtering':['cipa','content filtering','network level filtering','network-level filtering','monitoring of minors'],
 'screen_limits':['screen time','screen-time','screen-use','limit time on screens'],
 'competitive_bidding':['competitive bidding','form 470','form 471','lowest corresponding price'],
 'consultant_rules':['consultant','form 5654','percentage-based fees','percentage based compensation'],
 'radiofrequency':['radiofrequency','radio frequency','radiation','emf exposure','electromagnetic','wireless health'],
 'discount_matrix':['discount matrix','national school lunch','nslp','rural discount','discount rate'],
 'special_construction':['special construction','dark fiber','self-provisioned'],
 'parent_opt_out':['opt-out','opt out','screen-based instruction']
}
ROLE_KEYS=['unresolved','school','nonprofit','library','government','business','telecom','consultant']

def affiliation_hint(raw: str) -> str:
    """Conservative, ordered lexical proxy, NOT verified speaker identity."""
    t=raw.casefold()
    if re.search(r'(?:environmental health|brain tumor|wireless and emf|health sciences|utility reform|citizens against|center for democracy|nonprofit)',t):
        return 'nonprofit'
    if re.search(r'\b(?:library|libraries|librarian|ala\b|lib(?:rary)?\s+assoc)',t):
        return 'library'
    if re.search(r'\b(?:school district|school board|school system|public schools|unified school|independent school district|community unit school|\bcusd\b|\busd\b|\bisd\b|\besc\b|elementary school|middle school|high school|academy|charter school|archdiocese|parochial school|head start|school network|school technology|district schools|\bedlin[c]?\b)',t):
        return 'school'
    if re.search(r'\b(?:department of|commission|federal communications|fcc\b|government|office of|city of|county of|state of|tribal nation|navajo nation|bureau of|\bntia\b)',t):
        return 'government'
    if re.search(r'\b(?:communications|telecom|broadband|internet provider|cable|\bfiber\b|wireless|satellite|\.net\b|networks?|comcast|verizon|at&t|\bncta\b)',t):
        return 'telecom'
    if re.search(r'\b(?:consultant|consulting|funds for learning|e-rate services|erate management|grant solutions)',t):
        return 'consultant'
    if re.search(r'\b(?:association|coalition|alliance|foundation|advocacy|institute|council|society|\baclu\b|fairplay|common sense media|environmental health|tumor|children|health sciences|the utility reform network)',t):
        return 'nonprofit'
    if re.search(r'\b(?:university|college|education department|educational technology|school|educat(?:ion|ional)|student)',t):
        return 'school'
    if re.search(r'\b(?:llc|inc|ltd|company|corporation|corp\b|firm\b|technolog(?:y|ies)|enterprise|solutions|consulting)',t):
        return 'business'
    return 'unresolved'

def safe_org_display(name: str, role: str) -> str:
    """Do not republish individual name lists or cofiling identity strings."""
    if role=='unresolved' or '|' in name or len(name)>110:
        return ''
    if re.search(r'[@\d]{4,}|\+?\d{3}[-.\s]\d{3}',name):
        return ''
    if not re.search(r'\b(?:school|district|academy|library|libraries|commission|association|coalition|alliance|department|foundation|network|college|university|government|nation|corporation|\\bllc\\b|institute|society|fairplay|media|ncta|telecom)\b',name,re.I):
        return ''
    return name

def export(corpus: Path,snapshot_id='ocr_candidate_v1',dest: Path | None = None) -> dict:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,80}',snapshot_id):
        raise ValueError('Invalid snapshot identifier')
    snap=corpus.expanduser().resolve()/'analysis_observatory'/f'research_snapshot_{snapshot_id}'
    inventory,_=read_csv(snap/'research_inventory.csv')
    folder=snap/'ocr_augmented_text'
    issue_keys=list(ISSUES)
    pairs=[]
    mentions=Counter()
    roles=Counter()
    distinct_by_role={k:set() for k in ROLE_KEYS}
    duplicates=Counter(r['augmented_sha256'] for r in inventory if r.get('augmented_sha256'))
    for r in inventory:
        sid=r['submission_id']
        if not re.fullmatch(r'\d{8,15}',sid):
            raise ValueError('Unexpected FCC filing ID')
        role=affiliation_hint(r.get('filer_raw',''))
        roles[role]+=1
        if r['filer_raw'].strip():distinct_by_role[role].add(r['filer_raw'])
        path=folder/f'{sid}.txt'
        matches=[]
        if path.is_file():
            text=path.read_text(encoding='utf-8-sig').strip()
            if sha256(normalized_text(text).encode())!=r['augmented_sha256']:
                raise ValueError('Source hash mismatch for '+sid)
            low=text.lower()
            matches=[key for key,terms in ISSUES.items() if any(term in low for term in terms)]
            mentions.update(matches)
        elif r.get('augmented_sha256'):
            raise FileNotFoundError('Expected text file for '+sid)
        pairs.append({
          'id':sid,'date':r['date_submission'][:10],'type':r['submission_type'],
          'role':role,'agency_candidate':r['agency_record_candidate']=='1',
          'ocr':r['has_unreviewed_ocr']=='1','issues':sum(1<<issue_keys.index(k) for k in matches),
          'chars':int(r['augmented_chars'] or 0),
          'duplicate_count':duplicates[r['augmented_sha256']] if r.get('augmented_sha256') else 0,
          'organization':safe_org_display(r['filer_raw'],role)
        })
    # Cross-check against the versioned, previously audited aggregate before publishing.
    aggregate=json.loads((PUBLIC/'research_dashboard.json').read_text())
    if len(pairs)!=aggregate['indexed_filings']:
        raise ValueError('Aggregate/filing count mismatch')
    check={r['id']:r['n'] for r in aggregate['issues']}
    if dict(mentions)!=check:
        raise ValueError(f'Issue mention frequencies differ from audited aggregate. {dict(mentions)}')
    published={r['id']:(r['filings'],r['distinct_filer_fields']) for r in aggregate['roles']}
    for key in ROLE_KEYS:
        if (roles[key],len(distinct_by_role[key]))!=published[key]:
            raise ValueError(f'Affiliation category differs from audited reference: {key}')
    out=dest or PUBLIC/'corpus_index.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    payload={'version':'1.0','snapshot':snapshot_id,'generated_utc':datetime.now(timezone.utc).isoformat(),
       'privacy':'filing IDs and limited organizational labels only; no personal-name field or source transcript',
       'issue_keys':issue_keys,
       'filings':pairs}
    out.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return {'path':str(out),'indexed':len(pairs),'issue_mentions':dict(mentions),
            'role_filings':dict(roles),'bytes':out.stat().st_size}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,default=Path.home()/'Downloads/fcc_complete_corpus')
    p.add_argument('--snapshot-id',default='ocr_candidate_v1')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    print(json.dumps(export(args.corpus,args.snapshot_id,args.output),indent=2))

if __name__=='__main__': main()
