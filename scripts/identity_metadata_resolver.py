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
}

def key(s: str) -> str:
    return re.sub(r'[^a-z0-9]+',' ',str(s).lower()).strip()

def institution(raw: str) -> tuple[str,str]:
    normalized=key(raw)
    if normalized in KNOWN:return KNOWN[normalized]
    # The FCC's public metadata explicitly names both the company and title.
    if re.search(r'(?i)\bpresident of zayo education\b',str(raw)):
        return ('Zayo Group LLC','telecom_isp')
    return ('','')

def single_institution_pair(raw: str, institution_label: Callable[[str], str]) -> str:
    """Either person|institution or institution|person; not joint institutions."""
    parts=[s.strip() for s in str(raw or '').split('|')]
    if len(parts)!=2 or not all(parts):return ''
    orgs=[institution_label(p) for p in parts]
    if sum(bool(o) for o in orgs)!=1:return ''
    return next(o for o in orgs if o)

def personal_name_format(raw: str) -> bool:
    """An apparently personal-name filer with unknown occupational capacity."""
    raw=' '.join(str(raw or '').split())
    if not raw or len(raw)>70 or len(raw.split())>4:return False
    if any(c in raw for c in ('|','/',';', '@', ':')):return False
    if re.search(r'\d|\b(?:center|network|school|library|county|district|inc|llc|association|corp|coalition|fund|services|solutions|college|university|group|technologies|collective|bureau)\b',raw,re.I):
        return False
    if raw.isupper() and len(raw.replace(' ',''))>=3:return False
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,3}",raw))
