#!/usr/bin/env python3
"""Build a privacy-minimal, evidence-conscious FCC speaker/organization registry.

A filing is NOT a person and a representative's employer is NOT necessarily the
client whose position they submit. Classifications here are *candidates*, not
verified affiliations. Filer metadata and explicit source self-description are
kept separate. Text mentioning a role in a citation is never sufficient.
"""
from __future__ import annotations
import argparse
import base64
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/fcc_corpus'
INDEX = ROOT / 'docs/data/corpus_index.json'
BASE_ROLES = ROOT / 'docs/data/full_text_filer_roles.json'
OVERRIDES = ROOT / 'data/player_review_overrides.json'
DEST = ROOT / 'docs/data/player_registry.json'

# Specificity matters: "education" and "internet" alone are never identifiers.
ROLE_LABELS = {
    'school_district': 'School district or system',
    'individual_school': 'Individual school or academy',
    'school_technology_staff': 'School/district IT or technology staff',
    'school_educator': 'Teacher or educator',
    'school_administrator': 'School administrator or superintendent',
    'school_connected_unknown': 'School-connected; authority unclear',
    'library_institution': 'Library or library system',
    'library_staff': 'Librarian or library employee',
    'edtech_learning_vendor': 'Learning software or instructional technology vendor',
    'edtech_safety_vendor': 'Student safety, filtering or monitoring vendor',
    'edtech_device_vendor': 'Education device or hardware vendor',
    'telecom_isp': 'Internet or broadband service provider',
    'network_technology_vendor': 'Networking or connectivity technology vendor',
    'erate_consultant': 'E-rate consultant or compliance services firm',
    'procurement_adviser': 'Procurement or grant adviser',
    'trade_association': 'Trade or professional association',
    'advocacy_organization': 'Advocacy or nonprofit organization',
    'parent_guardian': 'Parent or caregiver',
    'student': 'Student',
    'government': 'Government or tribal institution',
    'researcher': 'Researcher or health professional',
    'other_vendor': 'Other commercial organization',
    'named_person_capacity_unstated': 'Named-person filer; professional capacity not established',
    'unresolved': 'Affiliation not established',
}
ORG_RULES = [
    ('erate_consultant', r'\b(?:e[- ]?rate consulting|e[- ]?rate services|funds for learning|e[- ]?rate management|erate consultant)\b'),
    ('edtech_safety_vendor', r'\b(?:student safety (?:software|platform)|content filtering (?:vendor|software)|school (?:monitoring|filtering) (?:software|platform))\b'),
    ('edtech_learning_vendor', r'\b(?:learning management (?:system|software)|educational (?:software|technology) (?:company|vendor)|edtech (?:company|vendor))\b'),
    ('edtech_device_vendor', r'\b(?:educational devices? (?:company|vendor)|student device manufacturer)\b'),
    ('school_district', r'\b(?:public schools|school district|unified school|independent school district|school system|county office of education|educational service (?:agency|district))\b'),
    ('individual_school', r'\b(?:elementary school|middle school|high school|charter school|academy|preparatory school)\b'),
    ('library_institution', r'\b(?:public librar(?:y|ies)|county librar(?:y|ies)|district librar(?:y|ies)|library system)\b'),
    ('telecom_isp', r'\b(?:internet service provider|broadband provider|telecommunications provider|telephone company|cable operator|fiber internet provider)\b'),
    ('network_technology_vendor', r'\b(?:network equipment (?:vendor|manufacturer)|networking equipment (?:company|manufacturer))\b'),
    ('trade_association', r'\b(?:trade association|professional association|association of|national association|state association)\b'),
    ('advocacy_organization', r'\b(?:foundation|coalition|advocacy|nonprofit|non-profit|institute|citizens for|center for|common sense media|fairplay)\b'),
    ('government', r'\b(?:department of|commission|tribal nation|state senate|legislature|bureau of|office of the governor)\b'),
    ('procurement_adviser', r'\b(?:procurement (?:adviser|advisor|consultant)|grant (?:consultant|management firm))\b'),
    ('other_vendor', r'\b(?:incorporated|corporation|\bllc\b|\bltd\b|technologies (?:inc|llc))\b'),
]
SELF_DESCRIBED = [
    ('school_technology_staff', r'\b(?:i am|i work as|i serve as|as) (?:an? |the )?(?:district |school )?(?:it director|technology director|technology coordinator|technology officer|network administrator|systems administrator|chief technology officer)\b'),
    ('school_administrator', r'\b(?:i am|i serve as|as) (?:an? |the )?(?:superintendent|school principal|district administrator|school administrator|school board member)\b'),
    ('school_educator', r'\b(?:i am|i work as|as) (?:an? |the )?(?:teacher|educator|classroom instructor|special education teacher)\b'),
    ('library_staff', r'\b(?:i am|i work as|i serve as|as) (?:an? |the )?(?:librarian|library director|library administrator)\b'),
    ('erate_consultant', r'\b(?:i am|i work as|i serve as|as) (?:an? |the )?(?:e[- ]?rate consultant|e[- ]?rate adviser|e[- ]?rate advisor)\b'),
    ('parent_guardian', r'\b(?:i am|as) (?:an? |the )?(?:parent|mother|father|guardian|caregiver)\b'),
    ('student', r'\b(?:i am|as) (?:an? |the )?(?:student|high school student|college student)\b'),
    ('researcher', r'\b(?:i am|i work as|as) (?:an? |the )?(?:researcher|scientist|pediatrician|public health researcher)\b'),
]
ORG_PATTERNS = [(k,re.compile(p,re.I)) for k,p in ORG_RULES]
SELF_PATTERNS = [(k,re.compile(p,re.I)) for k,p in SELF_DESCRIBED]
PERSON_ROLES = {'named_person_capacity_unstated', 'parent_guardian',
                'student', 'school_connected_voice_capacity_unconfirmed',
                'educator_or_school_staff', 'researcher_or_health_professional'}
BASE_CROSSWALK = {
    'school_district_or_school':'school_connected_unknown',
    'educator_or_school_staff':'school_connected_unknown',
    'school_connected_voice_capacity_unconfirmed':'school_connected_unknown',
    'library_or_library_system':'library_institution',
    'consultant_or_e_rate_services_firm':'erate_consultant',
    'government_or_tribal_organization':'government',
    'advocacy_nonprofit_or_trade_association':'advocacy_organization',
    'other_business_or_vendor':'other_vendor',
    'parent_guardian':'parent_guardian',
    'student':'student',
    'researcher_or_health_professional':'researcher',
    'named_person_capacity_unstated':'named_person_capacity_unstated',
    'unresolved':'unresolved',
}
SENSITIVE = re.compile(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}|(?<!\d)(?:\+1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\d)',re.I)
ORG_TOKEN = re.compile(r'\b(?:school|district|academy|library|libraries|commission|association|coalition|alliance|department|foundation|network|college|university|government|nation|corporation|llc|institute|society|technologies|telecom|communications|media)\b',re.I)

def organization_label(name: str) -> str:
    """Conservative names from an institution-valued filer field only."""
    name=' '.join(str(name or '').split())
    if len(name)<5 or len(name)>110 or not ORG_TOKEN.search(name): return ''
    if SENSITIVE.search(name) or any(x in name for x in ('|',' - ',',')):return ''
    return name

def canon(name: str) -> str:
    # Case and punctuation, not broad name equivalence or membership inference.
    return re.sub(r'[^a-z0-9]+',' ',name.casefold()).strip()

def first_rule(s: str, rules) -> tuple[str,str]:
    for role,rx in rules:
        m=rx.search(s)
        if m:return role,m.group(0)
    return '', ''

def explicit_personal_role(text: str) -> tuple[str,str]:
    # Only first-page author introduction or brief signature vicinity.
    # NEVER inspect an entire scientific bibliography for self-identification.
    intro=text[:min(2200,len(text))]
    for section in (intro,):
        role,match=first_rule(section,SELF_PATTERNS)
        if role:return role,match
    return '', ''

def inferred_identity(meta: dict, base: str, text: str) -> dict:
    name=organization_label(meta.get('filer_raw',''))
    person=base in PERSON_ROLES or (not name and base in ('unresolved', 'named_person_capacity_unstated'))
    self_role,self_quote=explicit_personal_role(text) if person else ('','')
    org_role,org_cue=first_rule(name,ORG_PATTERNS) if name else ('','')
    default=BASE_CROSSWALK.get(base,'unresolved')
    # A recognizable letterhead or sign-off is only a lead for manual review.
    # Do not infer authorization to speak for an institution.
    letterhead = bool(re.search(
        r'(?im)^[^\n]{0,100}\b(?:school district|public schools|library system|'
        r'elementary school|county office of education)\b[^\n]{0,40}$',
        text[:700])) if person and not self_role else False
    signature = ''
    if person and not self_role:
        tail = text[-2400:]
        closing = re.search(r'(?i)\b(?:sincerely|respectfully submitted|best regards)\s*[,\n]', tail)
        if closing:
            signed = tail[closing.end():closing.end()+500]
            if re.search(r'(?i)\b(?:director of technology|chief technology officer|it administrator|district technology coordinator)\b', signed):
                signature = 'school_technology_staff'
            elif re.search(r'(?i)\b(?:superintendent|principal|school board member)\b', signed):
                signature = 'school_administrator'
            elif re.search(r'(?i)\be[- ]?rate consultant\b', signed):
                signature = 'erate_consultant'
    candidate = signature or ('school_connected_unknown' if letterhead else '')
    role = self_role or org_role or candidate or default
    basis = ('author_self_description' if self_role else
             'filer_field_organization' if org_role else
             'signature_candidate' if signature else
             'letterhead_candidate' if letterhead else 'provisional_full_text_role')
    review = (not self_role and not org_role) or bool(candidate) or role in (
        'school_connected_unknown','named_person_capacity_unstated',
        'unresolved','other_vendor','advocacy_organization')
    proxy=bool(re.search(r'\b(?:on behalf of|representing (?:our|the|a)|counsel for|submitted for (?:our|the|a))\b',text[:2400],re.I))
    if proxy:review=True
    # A reviewer can reopen the FCC link. Do not republish a broad paragraph
    # of text from a private individual's letter as evidence.
    return {'role':role,'organization':name,
            'basis':basis,'evidence_cue':self_quote or org_cue or ('signature title' if signature else 'opening letterhead' if letterhead else ''),
            'speaker_is_proxy_possible':proxy,'needs_review':review,
            'identity_status':'candidate' if review else 'strong_source_cue'}

def base_lookup(index: list[dict], role_file: Path) -> dict:
    data=json.loads(role_file.read_text(encoding='utf-8'))
    codes=gzip.decompress(base64.b64decode(data['sequence'])).decode('ascii')
    assert len(codes)==len(index)==data['expected_records']
    assert index[0]['id']==data['expected_first_id'] and index[-1]['id']==data['expected_last_id']
    assert dict(Counter(codes))==data['expected_code_counts']
    return {row['id']:data['legend'][code] for row,code in zip(index,codes)}

def build(source=SOURCE, index_file=INDEX, role_file=BASE_ROLES, overrides_file=OVERRIDES, output=DEST):
    index=json.loads(Path(index_file).read_text(encoding='utf-8'))['filings']
    by_id={r['id']:r for r in index}
    base=base_lookup(index,Path(role_file))
    manifest=json.loads((Path(source)/'manifest.json').read_text(encoding='utf-8'))
    overrides=json.loads(Path(overrides_file).read_text(encoding='utf-8')) if Path(overrides_file).exists() else {}
    if not isinstance(overrides,dict):raise ValueError('Review overrides must be filing-keyed dictionary')
    unknown=set(overrides)-set(by_id)
    if unknown:raise ValueError('Unknown filing overrides: '+str(sorted(unknown)[:4]))
    filings=[];seen=set()
    for shard in manifest['shards']:
        p=Path(source)/'shards'/shard['name']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=shard['sha256']:raise ValueError('Source shard hash mismatch')
        with gzip.open(p,'rt',encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():continue
                source_row=json.loads(line)
                sid=str(source_row['submission_id'])
                if sid not in by_id or sid in seen:raise ValueError('Missing/duplicate source filing')
                seen.add(sid)
                body=str(source_row.get('text') or '')
                if hashlib.sha256(body.encode('utf-8')).hexdigest()!=source_row.get('text_sha256'):
                    # One no-text entry can have an absent text hash.
                    if body or source_row.get('text_sha256'):raise ValueError('Filing text hash mismatch')
                # Only use institution names already vetted for public display by\n                # the existing privacy-minimized corpus index, never raw filer names.\n                safe_meta={'filer_raw':by_id[sid].get('organization','')}\n                found=inferred_identity(safe_meta,base[sid],body)
                if sid in overrides:
                    v=overrides[sid]
                    if not isinstance(v,dict) or v.get('role') not in ROLE_LABELS or v.get('review_status')!='human_reviewed':
                        raise ValueError('Invalid manual override '+sid)
                    quote=str(v.get('evidence_quote') or '')
                    if len(quote)<12 or quote not in body:raise ValueError('Override lacks original source evidence '+sid)
                    org=organization_label(v.get('organization',''))
                    found.update(role=v['role'],organization=org,basis='human_source_review',
                                 evidence_cue='human reviewer checked source',
                                 identity_status='human_reviewed',needs_review=False)
                filings.append({'id':sid,'base_role':base[sid],
                     'role':found['role'],'organization':found['organization'],
                     'basis':found['basis'],'evidence_cue':found['evidence_cue'],
                     'identity_status':found['identity_status'],
                     'needs_review':found['needs_review'],
                     'proxy_possible':found['speaker_is_proxy_possible'],
                     'source_url':'https://www.fcc.gov/ecfs/filing/'+sid,
                     'text_sha256':source_row.get('text_sha256') or '',
                     'ocr_candidate':str(source_row.get('has_unreviewed_ocr','0'))=='1'})
    if len(filings)!=len(index) or seen!=set(by_id):raise ValueError('Registry does not cover all filing IDs')
    filings.sort(key=lambda x:x['id'])
    groups=defaultdict(list)
    for row in filings:
        if row['organization']:groups[canon(row['organization'])].append(row)
    organizations=[]
    for key,rs in groups.items():
        forms=Counter(r['organization'] for r in rs)
        organizations.append({'key':key,'name':forms.most_common(1)[0][0],
            'filings':len(rs),'distinct_source_texts':len({r['text_sha256'] for r in rs if r['text_sha256']}),
            'role_candidates':dict(Counter(r['role'] for r in rs)),
            'filing_ids':[r['id'] for r in rs],
            'disagreement_on_type':len({r['role'] for r in rs})>1})
    organizations.sort(key=lambda r:(-r['filings'],r['name']))
    counts=Counter(row['role'] for row in filings)
    payload={'schema_version':'player-registry-v1',
       'generated_utc':datetime.now(timezone.utc).isoformat(),
       'coverage':{'filings':len(filings),'readable_source_texts':manifest['records_with_text'],
             'named_organizations':len(organizations),
             'filings_requiring_identity_review':sum(r['needs_review'] for r in filings),
             'manually_reviewed_filings':sum(r['identity_status']=='human_reviewed' for r in filings)},
       'method':'Organization-valued filer field + explicit self-description in the opening; all provisional unless manually reviewed. No topical-content identity inference.',
       'roles':ROLE_LABELS,'role_filing_counts':dict(counts),
       'organizations':organizations,'filings':filings}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return payload['coverage']

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=SOURCE)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--roles',type=Path,default=BASE_ROLES)
    p.add_argument('--overrides',type=Path,default=OVERRIDES)
    p.add_argument('--output',type=Path,default=DEST)
    a=p.parse_args()
    print(json.dumps(build(a.source,a.index,a.roles,a.overrides,a.output),indent=2))
if __name__=='__main__':main()
,
        text[:700])) if person and not self_role else False
    signature=''
    if person and not self_role:
        tail=text[-2400:]
        closing=re.search(r'(?i)\\b(?:sincerely|respectfully submitted|best regards)\\s*[,\\n]',tail)
        if closing:
            signed=tail[closing.end():closing.end()+500]
            if re.search(r'(?i)\\b(?:director of technology|chief technology officer|'
                         r'it administrator|district technology coordinator)\\b',signed):
                signature='school_technology_staff'
            elif re.search(r'(?i)\\b(?:superintendent|principal|school board member)\\b',signed):
                signature='school_administrator'
            elif re.search(r'(?i)\\b(?:e[- ]?rate consultant)\\b',signed):
                signature='erate_consultant'
    candidate=signature or ('school_connected_unknown' if letterhead else '')
    role=self_role or org_role or candidate or default
    # A person's workplace or a lawyer's client is not an institutional filing
    # unless a human checks represented capacity in the original document.
    basis=('author_self_description' if self_role else
           'filer_field_organization' if org_role else
           'signature_candidate' if signature else
           'letterhead_candidate' if letterhead else 'provisional_full_text_role')
    review=(not self_role and not org_role) or bool(candidate) or role in (
        'school_connected_unknown','named_person_capacity_unstated',
        'unresolved','other_vendor','advocacy_organization')
    proxy=bool(re.search(r'\b(?:on behalf of|representing (?:our|the|a)|counsel for|submitted for (?:our|the|a))\b',text[:2400],re.I))
    if proxy:review=True
    # A reviewer can reopen the FCC link. Do not republish a broad paragraph
    # of text from a private individual's letter as evidence.
    return {'role':role,'organization':name,
            'basis':basis,'evidence_cue':self_quote or org_cue or '',
            'speaker_is_proxy_possible':proxy,'needs_review':review,
            'identity_status':'candidate' if review else 'strong_source_cue'}

def base_lookup(index: list[dict], role_file: Path) -> dict:
    data=json.loads(role_file.read_text(encoding='utf-8'))
    codes=gzip.decompress(base64.b64decode(data['sequence'])).decode('ascii')
    assert len(codes)==len(index)==data['expected_records']
    assert index[0]['id']==data['expected_first_id'] and index[-1]['id']==data['expected_last_id']
    assert dict(Counter(codes))==data['expected_code_counts']
    return {row['id']:data['legend'][code] for row,code in zip(index,codes)}

def build(source=SOURCE, index_file=INDEX, role_file=BASE_ROLES, overrides_file=OVERRIDES, output=DEST):
    index=json.loads(Path(index_file).read_text(encoding='utf-8'))['filings']
    by_id={r['id']:r for r in index}
    base=base_lookup(index,Path(role_file))
    manifest=json.loads((Path(source)/'manifest.json').read_text(encoding='utf-8'))
    overrides=json.loads(Path(overrides_file).read_text(encoding='utf-8')) if Path(overrides_file).exists() else {}
    if not isinstance(overrides,dict):raise ValueError('Review overrides must be filing-keyed dictionary')
    unknown=set(overrides)-set(by_id)
    if unknown:raise ValueError('Unknown filing overrides: '+str(sorted(unknown)[:4]))
    filings=[];seen=set()
    for shard in manifest['shards']:
        p=Path(source)/'shards'/shard['name']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=shard['sha256']:raise ValueError('Source shard hash mismatch')
        with gzip.open(p,'rt',encoding='utf-8') as stream:
            for line in stream:
                if not line.strip():continue
                source_row=json.loads(line)
                sid=str(source_row['submission_id'])
                if sid not in by_id or sid in seen:raise ValueError('Missing/duplicate source filing')
                seen.add(sid)
                body=str(source_row.get('text') or '')
                if hashlib.sha256(body.encode('utf-8')).hexdigest()!=source_row.get('text_sha256'):
                    # One no-text entry can have an absent text hash.
                    if body or source_row.get('text_sha256'):raise ValueError('Filing text hash mismatch')
                # Only use institution names already vetted for public display by\n                # the existing privacy-minimized corpus index, never raw filer names.\n                safe_meta={'filer_raw':by_id[sid].get('organization','')}\n                found=inferred_identity(safe_meta,base[sid],body)
                if sid in overrides:
                    v=overrides[sid]
                    if not isinstance(v,dict) or v.get('role') not in ROLE_LABELS or v.get('review_status')!='human_reviewed':
                        raise ValueError('Invalid manual override '+sid)
                    quote=str(v.get('evidence_quote') or '')
                    if len(quote)<12 or quote not in body:raise ValueError('Override lacks original source evidence '+sid)
                    org=organization_label(v.get('organization',''))
                    found.update(role=v['role'],organization=org,basis='human_source_review',
                                 evidence_cue='human reviewer checked source',
                                 identity_status='human_reviewed',needs_review=False)
                filings.append({'id':sid,'base_role':base[sid],
                     'role':found['role'],'organization':found['organization'],
                     'basis':found['basis'],'evidence_cue':found['evidence_cue'],
                     'identity_status':found['identity_status'],
                     'needs_review':found['needs_review'],
                     'proxy_possible':found['speaker_is_proxy_possible'],
                     'source_url':'https://www.fcc.gov/ecfs/filing/'+sid,
                     'text_sha256':source_row.get('text_sha256') or '',
                     'ocr_candidate':str(source_row.get('has_unreviewed_ocr','0'))=='1'})
    if len(filings)!=len(index) or seen!=set(by_id):raise ValueError('Registry does not cover all filing IDs')
    filings.sort(key=lambda x:x['id'])
    groups=defaultdict(list)
    for row in filings:
        if row['organization']:groups[canon(row['organization'])].append(row)
    organizations=[]
    for key,rs in groups.items():
        forms=Counter(r['organization'] for r in rs)
        organizations.append({'key':key,'name':forms.most_common(1)[0][0],
            'filings':len(rs),'distinct_source_texts':len({r['text_sha256'] for r in rs if r['text_sha256']}),
            'role_candidates':dict(Counter(r['role'] for r in rs)),
            'filing_ids':[r['id'] for r in rs],
            'disagreement_on_type':len({r['role'] for r in rs})>1})
    organizations.sort(key=lambda r:(-r['filings'],r['name']))
    counts=Counter(row['role'] for row in filings)
    payload={'schema_version':'player-registry-v1',
       'generated_utc':datetime.now(timezone.utc).isoformat(),
       'coverage':{'filings':len(filings),'readable_source_texts':manifest['records_with_text'],
             'named_organizations':len(organizations),
             'filings_requiring_identity_review':sum(r['needs_review'] for r in filings),
             'manually_reviewed_filings':sum(r['identity_status']=='human_reviewed' for r in filings)},
       'method':'Organization-valued filer field + explicit self-description in the opening; all provisional unless manually reviewed. No topical-content identity inference.',
       'roles':ROLE_LABELS,'role_filing_counts':dict(counts),
       'organizations':organizations,'filings':filings}
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    return payload['coverage']

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,default=SOURCE)
    p.add_argument('--index',type=Path,default=INDEX)
    p.add_argument('--roles',type=Path,default=BASE_ROLES)
    p.add_argument('--overrides',type=Path,default=OVERRIDES)
    p.add_argument('--output',type=Path,default=DEST)
    a=p.parse_args()
    print(json.dumps(build(a.source,a.index,a.roles,a.overrides,a.output),indent=2))
if __name__=='__main__':main()
