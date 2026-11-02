#!/usr/bin/env python3
"""Small, auditable metadata-only resolver for FCC submitter identities.

Known institution aliases have public corroboration; personal-name detection
does NOT claim that the filer speaks in a private rather than professional
capacity. No guesses are made from positions on E-Rate policy.
"""
from __future__ import annotations
import re
from typing import Callable

# Matched to metadata fields, not occurrences in quoted comment text.
KNOWN = {
    'selco': ('Southeastern Libraries Cooperating (SELCO)', 'library_institution'),
    'southeastern libraries cooperating': ('Southeastern Libraries Cooperating (SELCO)', 'library_institution'),
    'ateret torah center': ('Ateret Torah Center', 'individual_school'),
    'ladacin network': ('LADACIN Network', 'advocacy_organization'),
    'city forward collective': ('City Forward Collective', 'advocacy_organization'),
    'http': ('Hispanic Technology and Telecommunications Partnership', 'advocacy_organization'),
    'hispanic technology and telecommunications partnership': ('Hispanic Technology and Telecommunications Partnership', 'advocacy_organization'),
    'advanedge solutions': ('AdvanEdge Solutions Inc.', 'erate_consultant'),
    'advanedge solutions inc': ('AdvanEdge Solutions Inc.', 'erate_consultant'),
    'intelafunds': ('AdvanEdge Solutions Inc.', 'erate_consultant'),
    'advanedge solutions intelafunds': ('AdvanEdge Solutions Inc.', 'erate_consultant'),
    'north central independent living services': ('North Central Independent Living Services', 'advocacy_organization'),
    'zayo education': ('Zayo Group LLC', 'telecom_isp'),
    # Additional residual cases checked against primary institution websites,
    # state education agencies, college directories, and vendor descriptions.
    'sentinelone inc': ('SentinelOne, Inc.', 'other_vendor'),
    'ohio information technology centers': ('Ohio Information Technology Centers', 'education_network_consortium'),
    'missouri research and education network': ('Missouri Research and Education Network (MOREnet)', 'education_network_consortium'),
    'southwest kansas area cooperative district': ('Southwest Kansas Area Cooperative District', 'school_district'),
    'michigan statewide educational network misen': ('Michigan Statewide Educational Network (MiSEN)', 'education_network_consortium'),
    'michigan statewide educational network': ('Michigan Statewide Educational Network (MiSEN)', 'education_network_consortium'),
    'responsive education solutions': ('Responsive Education Solutions', 'school_district'),
    'mothers against media addiction': ('Mothers Against Media Addiction', 'advocacy_organization'),
    'family services of westchester': ('Family Services of Westchester', 'advocacy_organization'),
    'finkelstein memorial library': ('Finkelstein Memorial Library', 'library_institution'),
    'queensborough community college': ('Queensborough Community College', 'higher_education_institution'),
    'citizens against government waste': ('Citizens Against Government Waste', 'advocacy_organization'),
    'alabama leaders in educational technology': ('Alabama Leaders in Educational Technology', 'trade_association'),
    'california emerging technology fund': ('California Emerging Technology Fund', 'advocacy_organization'),
    'methodist healthcare ministries of south texas inc': ('Methodist Healthcare Ministries of South Texas, Inc.', 'advocacy_organization'),
    'infinity communications compliance': ('Infinity Communications & Compliance', 'erate_consultant'),
    'infinity communications and compliance': ('Infinity Communications & Compliance', 'erate_consultant'),

}

# Recognize canonical spellings after the institution name has been normalized.
KNOWN.update({re.sub(r'[^a-z0-9]+',' ',v[0].lower()).strip():v
              for v in tuple(KNOWN.values())})

def key(s: str) -> str:
    return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()

def institution(raw: str) -> tuple[str,str]:
    normalized=key(raw)
    if normalized in KNOWN:return KNOWN[normalized]
    # Two filing fields can be trade names for the SAME firm (rather than
    # separate co-signers); require both to resolve to the identical entity.
    fields=[p.strip() for p in str(raw).split('|')]
    if len(fields)==2 and all(key(p) in KNOWN for p in fields):
        resolved={KNOWN[key(p)] for p in fields}
        if len(resolved)==1:return next(iter(resolved))
    # The FCC's public metadata explicitly names both the company and title.
    if re.search(r'(?i)\bpresident of zayo education\b',str(raw)):
        return ('Zayo Group LLC','telecom_isp')
    return ('','')

def explicit_job_title(raw: str) -> str:
    """Professional titles exposed directly in FCC submitter metadata."""
    k=key(raw)
    return {
        'library assistant ii':'library_staff',
        'adult education educational technology specialist':'school_technology_staff',
    }.get(k,'')

def single_institution_pair(raw: str, institution_label: Callable[[str], str]) -> str:
    """Either person|institution or institution|person; not joint institutions."""
    raw=str(raw or '')
    parts=[s.strip() for s in raw.split('|')]
    if len(parts)==1 and raw.count('/')==1 and not re.search(r'(?i)https?://',raw):
        parts=[p.strip() for p in raw.split('/')]
    if len(parts)<2 or not all(parts):return ''
    orgs=[institution_label(p) for p in parts]
    # A single organization and several named signatories is an attribution
    # relationship, not an unknown entity. Multiple institutions are joint.
    if sum(bool(o) for o in orgs)!=1:return ''
    return next(o for o in orgs if o)

def multiple_person_names_only(raw: str) -> bool:
    """Multiple signatory names; does not imply a personal-capacity stance."""
    parts=[p.strip() for p in str(raw or '').split('|')]
    return 2<=len(parts)<=6 and all(personal_name_format(p) for p in parts)

def personal_name_format(raw: str) -> bool:
    """An apparently personal-name filer with unknown occupational capacity."""
    raw=' '.join(str(raw or '').split())
    if not raw or len(raw)>70 or len(raw.split())>4:return False
    if any(c in raw for c in ('|','/',';', '@', ':')):return False
    if re.search(r'\d|\b(?:center|network|school|library|county|district|inc|llc|association|corp|coalition|fund|services|solutions|college|university|group|technologies|collective|bureau)\b',raw,re.I):
        return False
    if raw.isupper() and len(raw.split())==1 and len(raw)>=3:return False
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,3}",raw))
