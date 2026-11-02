#!/usr/bin/env python3
"""Conservative FCC submitter-and-represented-organization entity resolution.

Counting unit is a submitter acting in a documented capacity. An institution
submitting in its own name is one institutional voice; a named individual
associated with an institution is a separate person-in-capacity identity.
Do not infer two people from matching prose or collapse two affiliations.
All raw names are used only in memory; published IDs are opaque ordinals.
"""
from __future__ import annotations
import re
import unicodedata

from scripts.identity_metadata_resolver import (
    institution, personal_name_format, personal_name_with_postnominals,
)
from scripts.build_player_registry import organization_label


UNINFORMATIVE={
    '', 'anonymous', 'unknown', 'not available', 'n a', 'na', 'none',
    'individual', 'public comment', 'commenter', 'private citizen', 'citizen',
    'parent', 'school', 'district', 'library', 'unidentified', 'n a n a',
}
BAD_ORG_PREFIX=re.compile(
    r'(?i)^(?:submitted to|comments? (?:on|to|regarding)|in (?:response|support)|'
    r'my children|the following|dear |to the |please |subject:|re:|'
    r'this (?:letter|comment|document)|\W)',
)
BAD_ORG_CONTEXT=re.compile(r'[\n\r•●]|(?:https?://)|(?:\b(?:pays|a year for access|dear commission)\b)',re.I)
PERSON_TITLE=re.compile(r'(?i)^(?:(?:ms|mrs|mr|miss|dr|prof)\.?\s+)+')
INSTITUTION_ROLES={
    'advocacy_organization','nonprofit_service_provider','trade_association',
    'government','individual_school','school_district','library_institution',
    'higher_education_institution','education_network_consortium',
    'other_vendor','edtech_learning_vendor','edtech_device_vendor',
    'edtech_safety_vendor','edtech_virtual_school_vendor',
    'telecom_isp','network_technology_vendor','erate_consultant',
}
# Source-based affiliation and representation leads. These do not establish
# authority to submit on an institution's behalf.
ORG_BASIS={
    'filer_field_organization','multi_party_metadata_affiliation_candidate',
    'signed_role_and_organization','signed_role','signature_candidate',
    'letterhead_candidate','human_source_review','author_self_description',
    'curated_company_type_candidate','joint_institutional_metadata',
}

def normalize(value):
    value=unicodedata.normalize('NFKC',str(value or '')).casefold()
    return re.sub(r'[^\w]+',' ',value,flags=re.UNICODE).strip()

def canonical_org(org):
    """Known corroborated aliases share a key; unknown names match conservatively."""
    name=str(org or '').strip()
    if not name or len(name)>110 or BAD_ORG_PREFIX.search(name) or BAD_ORG_CONTEXT.search(name):
        return ''
    known,_role=institution(name)
    if known:return normalize(known)
    label=organization_label(name)
    return normalize(label) if label else ''

def person_name(raw):
    """Allow titles on otherwise recognizable personal-name metadata only."""
    value=PERSON_TITLE.sub('',str(raw or '').strip()).strip()
    return normalize(value) if (personal_name_format(value) or personal_name_with_postnominals(value)) else ''

def parts_of(raw):
    """Only split explicit person/institution composite fields."""
    text=str(raw or '').strip()
    for delimiter in ('|',';',' / '):
        if delimiter not in text:continue
        parts=[p.strip() for p in text.split(delimiter)]
        if 2<=len(parts)<=6 and all(parts):return parts
    if text.count(',')==1 and not re.search(r'(?i)\b(?:inc|llc|ltd|corp)\b',text):
        parts=[p.strip() for p in text.split(',')]
        if sum(bool(canonical_org(p)) for p in parts)==1 and any(person_name(p) for p in parts):
            return parts
    return [text]

def resolve_submitter(raw, filing_id, entry=None):
    """Return (ephemeral identity key, evidence basis, review warning)."""
    e=entry or {}
    field=str(raw or '').strip()
    norm=normalize(field)
    if norm in UNINFORMATIVE or not 4<=len(norm)<=220 or not re.search(r'[a-z0-9]',norm):
        return ('filing:'+str(filing_id),'unidentifiable_filer',True)
    if e.get('multi_submitter_metadata'):
        joint=sorted({canonical_org(x) for x in e.get('joint_institution_candidates',[])})
        joint=[x for x in joint if x]
        if len(joint)>1:
            return ('joint:'+'|'.join(joint),'joint_institutional_submission',True)
        # Unresolved joint signers: never arbitrarily make one signer the coalition.
        return ('joint_raw:'+norm,'joint_relationship_needs_review',True)

    # Distinguish named people from their represented or affiliated institution.
    # The FCC filer field takes precedence over a company mention in prose.
    parts=parts_of(field)
    names=[person_name(p) for p in parts]
    names=[n for n in names if n]
    raw_institutions=[canonical_org(p) for p in parts]
    raw_institutions=[x for x in raw_institutions if x]
    org=canonical_org(e.get('organization',''))
    # Known institutions can have human-like names. Recognized institutional
    # metadata outranks a generic personal-name pattern.
    raw_org=canonical_org(field) if len(parts)==1 else ''
    if raw_org:
        if org and org!=raw_org:
            return ('organization:'+raw_org,'organization_metadata_conflict',True)
        return ('organization:'+(org or raw_org),'institution_filer_metadata',
                bool(e.get('needs_review') or e.get('proxy_possible')))
    if len(parts)>1 and len(names)==1 and (raw_institutions or org):
        orgs=sorted(set(raw_institutions+([org] if org else [])))
        if len(orgs)>1:
            return ('composite_raw:'+norm,'conflicting_institutions_in_metadata',True)
        return ('person:'+names[0]+'|org:'+orgs[0],
                'named_person_in_metadata_with_institution',False)
    if len(parts)>1 and len(raw_institutions)>1:
        return ('joint_raw:'+norm,'potential_joint_submission',True)
    if len(parts)==1 and len(names)==1:
        if org:
            return ('person:'+names[0]+'|org:'+org,
                    'named_person_with_source_affiliation',
                    bool(e.get('needs_review') or e.get('proxy_possible')))
        return ('person:'+names[0]+'|org:unstated',
                'named_person_capacity_not_established',
                bool(e.get('needs_review')))
    # Filer field itself is an organization; canonicalize aliases.
    if org and e.get('role') in INSTITUTION_ROLES and e.get('basis') in ORG_BASIS:
        # Institution detected in signature/letterhead, but the raw field is
        # a title or unclear identifier. Do not merge different unnamed people
        # solely because they work for the same organization.
        return ('raw:'+norm+'|org:'+org,'source_identified_institution_with_unparsed_filer',True)
    if org:
        return ('raw:'+norm+'|org:'+org,'affiliation_candidate_unparsed_filer',True)
    return ('raw:'+norm,'unparsed_named_filer_field',True)
