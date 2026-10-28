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
    'edtech_digital_content_vendor': 'Digital books, media or learning-content vendor',
    'edtech_virtual_school_vendor': 'Virtual school or online learning provider',
    'edtech_age_privacy_vendor': 'Age assurance or child privacy technology provider',
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
    # Exact organizations from FCC submitter metadata; no claim of endorsement.
    ('government', r'^national telecommunications and information administration$'),
    ('telecom_isp', r'^alaska power (?:and|&) telephone$'),
    ('erate_consultant', r'^hwc consultants$'),
    ('erate_consultant', r'^(?:funds for learning|american e[- ]rate solutions|e[- ]rate complete|e[- ]rate funding services|tel/logic.*e[- ]rate central|education service center region 12 e[- ]rate consulting services)\b'),
    ('trade_association', r'^(?:software (?:and|&) information industry association|e[- ]rate management professionals association|ncta|ustelecom|ntca[- ]|alaska telecom association|technology channel sales professionals)\b'),
    # Education-industry and professional bodies are not individual schools.
    ('trade_association', r'\b(?:school boards? association|school superintendents association|association of (?:charter )?schools?|association of school (?:administrators|superintendents)|school administrators association|state e[- ]?rate coordinators.{0,6}alliance)\b'),
    ('advocacy_organization', r'^national alliance for public charter schools$'),
    ('government', r'\b(?:state education department|department of education|education department|state education agency)\b'),
    ('network_technology_vendor', r'^united data technologies\b'),
    ('erate_consultant', r'\b(?:e[- ]?rate consulting|e[- ]?rate services|funds for learning|e[- ]?rate management|erate consultant)\b'),
    ('edtech_safety_vendor', r'\b(?:student safety (?:software|platform)|content filtering (?:vendor|software)|school (?:monitoring|filtering) (?:software|platform))\b'),
    ('edtech_learning_vendor', r'\b(?:learning management (?:system|software)|educational (?:software|technology) (?:company|vendor)|edtech (?:company|vendor))\b'),
    ('edtech_device_vendor', r'\b(?:educational devices? (?:company|vendor)|student device manufacturer)\b'),
    ('school_district', r'\b(?:public schools|school district|schools district|county district schools|sch district|unified school|independent school district|school system|school corporation|schools corporation|central schools?(?: corporation)?|school city of|regional school unit|exempted village school|indep sch(?:ool)? dist(?:rict)?|county office of education|(?:education|educational) service (?:agency|district)|area special education district)\b'),
    ('individual_school', r'\b(?:elementary school|middle school|high school|charter school|academy|preparatory school)\b|\b(?:school|schools)\b(?:\s+(?:of|for)\s+[a-z][a-z -]{2,35})?\s*(?:,?\s*(?:inc\.?|llc\.?))?$'),
    ('library_institution', r'\b(?:public librar(?:y|ies)|county librar(?:y|ies)|district librar(?:y|ies)|library system)\b'),
    ('telecom_isp', r'\b(?:internet service provider|broadband provider|telecommunications provider|telephone company|cable operator|fiber internet provider)\b'),
    ('network_technology_vendor', r'\b(?:network equipment (?:vendor|manufacturer)|networking equipment (?:company|manufacturer))\b'),
    ('trade_association', r'\b(?:trade association|professional association|association of|national association|state association)\b'),
    ('advocacy_organization', r'\b(?:foundation|coalition|advocacy|nonprofit|non-profit|institute|citizens for|center for|common sense media|fairplay)\b'),
    ('government', r'\b(?:department of|commission|tribal nation|state senate|legislature|bureau of|office of the governor|telecommunications and information administration)\b'),
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
                'consultant_or_e_rate_services_firm',
                'student', 'school_connected_voice_capacity_unconfirmed',
                'educator_or_school_staff', 'researcher_or_health_professional'}
BASE_CROSSWALK = {
    'school_district_or_school':'school_connected_unknown',
    'educator_or_school_staff':'school_connected_unknown',
    'school_connected_voice_capacity_unconfirmed':'school_connected_unknown',
    'library_or_library_system':'library_institution',
    'consultant_or_e_rate_services_firm':'unresolved',
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
ORG_TOKEN = re.compile(r'\b(?:school|district|academy|library|libraries|commission|association|coalition|alliance|department|administration|agency|foundation|network|college|university|government|nation|corporation|llc|inc|institute|society|technologies|telecom|communications|media|consulting|consultants|services|software|technology|broadband|solutions|telephone)\b',re.I)

def organization_label(name: str) -> str:
    """Conservative names from an institution-valued filer field only."""
    name=' '.join(str(name or '').split())
    if len(name)<5 or len(name)>110 or not ORG_TOKEN.search(name): return ''
    if canon(name) in {'school','schools','library','district','association','corporation','company','business'}:return ''
    # Permit a legal corporate suffix while rejecting people mixed with entities.
    suffix=re.search(r',\s*(?:LLC|Inc\.?|Incorporated|Ltd\.?|Corporation|Corp\.?)$',name,re.I)
    # Mixed personal and organizational fields are not institution labels.
    # Two distinctive institutional slash names in the source snapshot are
    # legitimate entity names, not person/organization combinations.
    known_institutional_slash = bool(re.fullmatch(
        r'(?:tel/logic inc\.? dba e[- ]rate central|c/w mars member libraries)',name,re.I))
    if SENSITIVE.search(name) or any(sep in name for sep in ('|',';',' - ')) or ('/' in name and not known_institutional_slash) or (',' in name and not suffix):return ''
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

# An industry focus never turns a trade association into a vendor, or assigns
# the association's stated claims to each of its corporate members.
INDUSTRY_RULES = [
    ('edtech_industry', re.compile(r'^software (?:and|&) information industry association$',re.I)),
    ('erate_consulting', re.compile(r'(?:funds for learning|e[- ]rate (?:central|complete|funding services|management professionals|consulting)|american e[- ]rate solutions)',re.I)),
    ('telecom_industry', re.compile(r'^(?:ncta|ustelecom|ntca[- ]|alaska telecom association|wta [-–]|.*broadband association)',re.I)),
]
def industry_focus(name: str, role: str) -> str:
    for industry,pattern in INDUSTRY_RULES:
        if pattern.search(name):return industry
    if role.startswith('edtech_'):return 'edtech_industry'
    if role in ('telecom_isp','network_technology_vendor'):return 'telecom_industry'
    if role in ('erate_consultant','procurement_adviser'):return 'erate_consulting'
    return 'unspecified'

def candidate_affiliation(raw: str) -> str:
    """Provisional second party in 'person | organization' metadata only.

    A listing is not proof of a person's legal power to speak for an entity.
    The person's name is never published in this derived registry.
    """
    parts=[x.strip() for x in str(raw or '').split('|')]
    if len(parts)!=2 or not parts[0] or not parts[1]:return ''
    if organization_label(parts[0]):return ''
    return organization_label(parts[1])

# A deliberately narrow list of distinctive legal submitter names appearing
# in this fixed source snapshot. The exact name establishes an *entity lead*;
# product-line classifications remain provisional until document review.
CURATED_FILER_ROLES = {
    'curriculum associates llc': ('edtech_learning_vendor', 'edtech_learning'),
    'stride inc': ('edtech_virtual_school_vendor', 'edtech_virtual_school'),
    'overdrive inc': ('edtech_digital_content_vendor', 'edtech_digital_content'),
    'rego payment architectures inc': ('edtech_age_privacy_vendor', 'child_privacy_technology'),
    'cisco systems inc': ('network_technology_vendor', 'network_equipment'),
    'extreme networks inc': ('network_technology_vendor', 'network_equipment'),
    'zayo group llc': ('telecom_isp', 'telecom_service'),
    'smith bagley inc': ('telecom_isp', 'telecom_service'),
    'space exploration holdings llc': ('telecom_isp', 'satellite_connectivity'),
    'first step internet llc': ('telecom_isp', 'telecom_service'),
    'metcomm net llc': ('telecom_isp', 'telecom_service'),
    'united data technologies inc': ('network_technology_vendor', 'network_equipment'),
    'csm consulting inc': ('erate_consultant', 'erate_consulting'),
    'grant consulting services llc': ('erate_consultant', 'erate_consulting'),
    'sutherland consulting group inc': ('erate_consultant', 'erate_consulting'),
    'educational funding group inc': ('erate_consultant', 'erate_consulting'),
    'rollins sumrall education group inc': ('erate_consultant', 'erate_consulting'),
    'kb associates llc': ('erate_consultant', 'erate_consulting'),
}
def curated_business(name: str):
    return CURATED_FILER_ROLES.get(canon(name))

def inferred_identity(meta: dict, base: str, text: str) -> dict:
    name=organization_label(meta.get('filer_raw',''))
    affiliated=candidate_affiliation(meta.get('filer_raw','')) if not name else ''
    if affiliated:name=affiliated
    person=base in PERSON_ROLES or (not name and base in ('unresolved', 'named_person_capacity_unstated'))
    self_role,self_quote=explicit_personal_role(text) if person else ('','')
    org_role,org_cue=first_rule(name,ORG_PATTERNS) if name else ('','')
    curated=curated_business(name) if name else None
    if curated:org_role,org_cue=curated[0],name
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
    basis = ('multi_party_metadata_affiliation_candidate' if affiliated else
             'curated_company_type_candidate' if curated else
             'author_self_description' if self_role else
             'filer_field_organization' if org_role else
             'signature_candidate' if signature else
             'letterhead_candidate' if letterhead else 'provisional_full_text_role')
    review = bool(curated) or bool(affiliated) or (not self_role and not org_role) or bool(candidate) or role in (
        'school_connected_unknown','named_person_capacity_unstated',
        'unresolved','other_vendor','advocacy_organization')
    proxy=bool(re.search(r'\b(?:on behalf of|representing (?:our|the|a)|counsel for|submitted for (?:our|the|a))\b',text[:2400],re.I))
    if proxy:review=True
    # A reviewer can reopen the FCC link. Do not republish a broad paragraph
    # of text from a private individual's letter as evidence.
    return {'role':role,'organization':name,
            'industry_focus':curated[1] if curated else industry_focus(name,role),
            'basis':basis,'evidence_cue':self_quote or org_cue or ('signature title' if signature else 'opening letterhead' if letterhead else ''),
            'speaker_is_proxy_possible':proxy,'needs_review':review,
            'identity_status':'candidate' if review else 'strong_source_cue'}

JOINT_ORGANIZATION_ALIASES = {
    'curriculum associates':'Curriculum Associates, LLC',
    'software & information industry association':'Software and Information Industry Association',
    'software and information industry association':'Software and Information Industry Association',
    'consortium for school networking':'Consortium for School Networking',
}
def identifiable_cofilers(raw: str) -> list[str]:
    """Conservatively extract institution-valued members of explicit '|' lists.

    This preserves co-signer leads without treating a person + employer as two
    organizations. Never publish private-person components.
    """
    parts=[x.strip() for x in str(raw or '').split('|') if x.strip()]
    seen=set();result=[]
    for p in parts:
        label=JOINT_ORGANIZATION_ALIASES.get(p.casefold()) or organization_label(p)
        if not label:continue
        key=canon(label)
        if key not in seen:
            seen.add(key);result.append(label)
    return result

def submitted_by_multiple_entities(raw: str) -> dict:
    """A joint institutional filing remains ONE FCC filing for statistics."""
    parts=[x.strip() for x in str(raw or '').split('|') if x.strip()]
    organizations=identifiable_cofilers(raw)
    return {'multi_submitter_metadata':len(organizations)>1,
            'submitter_field_components':len(parts) if parts else 1,
            'joint_institution_candidates':organizations if len(organizations)>1 else [],
            'requires_relationship_review':len(parts)>1}

def review_priority(identity: dict, body: str) -> dict:
    """Rank needs-human-review cases, never convert a candidate into a fact."""
    if not identity['needs_review']:return {'score':0,'level':'not_required','reasons':[]}
    score=5;reasons=[]
    if identity['organization']:
        score+=35;reasons.append('source_metadata_institution_or_candidate_affiliation')
    if identity['basis']=='curated_company_type_candidate':
        score+=30;reasons.append('business_sector_typing_requires_document_review')
    if identity['basis'] in ('signature_candidate','letterhead_candidate'):
        score+=30;reasons.append('letterhead_or_signature_needs_confirmation')
    if identity['basis']=='multi_party_metadata_affiliation_candidate':
        score+=25;reasons.append('potential_person_organization_relationship')
    if identity['speaker_is_proxy_possible']:
        score+=25;reasons.append('possible_representative_client_relationship')
    if identity['role'] in ('erate_consultant','procurement_adviser','other_vendor','trade_association','edtech_learning_vendor','edtech_safety_vendor','edtech_device_vendor','telecom_isp','network_technology_vendor'):
        score+=30;reasons.append('commercial_or_trade_stakeholder')
    if identity['role'] in ('unresolved','school_connected_unknown'):
        score+=15;reasons.append('role_unclear')
    if re.search(r'(?i)\b(?:respectfully submitted|sincerely|director of technology|superintendent|chief executive|vice president|on behalf of)\b',body[-2600:]):
        score+=12;reasons.append('possible_closing_or_signature_evidence')
    if re.search(r'(?i)\b(?:vendor incentives|e[- ]rate consultant|consultant registration|school screen time|education technology|procurement)\b',body[:3500]):
        score+=10;reasons.append('relevant_policy_stakeholder_language')
    score=min(100,score)
    return {'score':score,'level':'high' if score>=65 else 'medium' if score>=35 else 'low','reasons':reasons}

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
                # Only use institution names already vetted for public display by
                # the existing privacy-minimized corpus index, never raw filer names.
                # Screen raw metadata for organizational content only. Keep
                # individuals private; co-signer lists require separate review.
                safe_name=organization_label(by_id[sid].get('organization',''))
                raw_name=str(source_row.get('filer_raw') or '')
                source_org=organization_label(raw_name)
                source_affiliation=candidate_affiliation(raw_name)
                safe_meta={'filer_raw':safe_name or source_org or (raw_name if source_affiliation else '')}
                found=inferred_identity(safe_meta,base[sid],body)
                if sid in overrides:
                    v=overrides[sid]
                    if not isinstance(v,dict) or v.get('role') not in ROLE_LABELS or v.get('review_status')!='human_reviewed':
                        raise ValueError('Invalid manual override '+sid)
                    quote=str(v.get('evidence_quote') or '')
                    if len(quote)<12 or quote not in body:raise ValueError('Override lacks original source evidence '+sid)
                    org=organization_label(v.get('organization',''))
                    found.update(role=v['role'],organization=org,basis='human_source_review',
                                 evidence_cue='human reviewer checked source',
                                 identity_status='human_reviewed',needs_review=False,
                                 industry_focus=industry_focus(org,v['role']))
                review=review_priority(found,body)
                joint=submitted_by_multiple_entities(raw_name)
                filings.append({'id':sid,'base_role':base[sid],
                     'role':found['role'],'organization':found['organization'],
                     'industry_focus':found['industry_focus'],
                     'basis':found['basis'],'evidence_cue':found['evidence_cue'],
                     'identity_status':found['identity_status'],
                     'needs_review':found['needs_review'],
                     'review_priority':review['score'],'review_tier':review['level'],
                     'review_reasons':review['reasons'],
                     'proxy_possible':found['speaker_is_proxy_possible'],
                     'source_url':'https://www.fcc.gov/ecfs/filing/'+sid,
                     'text_sha256':source_row.get('text_sha256') or '',
                     'ocr_candidate':str(source_row.get('has_unreviewed_ocr','0'))=='1',
                     'multi_submitter_metadata':joint['multi_submitter_metadata'],
                     'submitter_field_components':joint['submitter_field_components'],
                     'joint_institution_candidates':joint['joint_institution_candidates']})
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
            'industry_focus_candidates':dict(Counter(r['industry_focus'] for r in rs)),
            'filing_ids':[r['id'] for r in rs],
            'disagreement_on_type':len({r['role'] for r in rs})>1})
    organizations.sort(key=lambda r:(-r['filings'],r['name']))
    counts=Counter(row['role'] for row in filings)
    payload={'schema_version':'player-registry-v1',
       'generated_utc':datetime.now(timezone.utc).isoformat(),
       'coverage':{'filings':len(filings),'readable_source_texts':manifest['records_with_text'],
             'named_organizations':len(organizations),
             'filings_requiring_identity_review':sum(r['needs_review'] for r in filings),
             'manually_reviewed_filings':sum(r['identity_status']=='human_reviewed' for r in filings),
             'filings_with_two_or_more_identifiable_institutions':sum(r['multi_submitter_metadata'] for r in filings)},
       'method':'Screened original FCC institution-valued filer metadata, two-party potential affiliation, and explicit opening self-description. Type and industry remain separate. Categories provisional until human reviewed.',
       'roles':ROLE_LABELS,'role_filing_counts':dict(counts),
       'review_tier_counts':dict(Counter(r['review_tier'] for r in filings)),
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
