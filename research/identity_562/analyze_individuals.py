#!/usr/bin/env python3
"""Independent, unpublished investigation of individual FCC E-Rate submitters.

Reads original text from all immutable, SHA256-checked source shards.
Does NOT modify stakeholder labels, official registry, census or website.
Never exports personal names, raw email addresses or comment text.

A professional capacity must be evidenced in the comment; a topic, same-name
match, and inferred employer alone do NOT prove representative authority.
Broad, explicitly self-declared *civic* capacities remain separate from jobs.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from scripts.build_player_registry import ROOT, organization_label, first_rule, ORG_PATTERNS
from scripts.identity_context_resolver import context_capacity
from scripts.identity_signature_resolver import signature_signal, domain_sector
from scripts.identity_metadata_resolver import personal_name_format

SOURCE = ROOT / "data/fcc_corpus"
REGISTRY = ROOT / "docs/data/player_registry.json"
OUTPUT = ROOT / "research/identity_562/results"
TOPIC_LEDGER = ROOT / "docs/data/stakeholder_argument_census.json"
TARGET_ROLE = "named_person_capacity_unstated"

# Anchor all evidence to a *self* statement and keep it out of scholarly
# references, quoted testimony, copy-pasted sample letters and FCC prompts.
AUTHOR_PATTERNS = [
    ("parent_guardian", "parent_self_description",
     r"\b(?:i(?:'m| am) (?:a |an |the )?(?:parent|mum|mom|mother|dad|father|guardian|grandparent|grandmother|grandfather|foster parent|adoptive parent)|as (?:a |an |the )?(?:parent|mother|father|guardian|grandparent|caregiver)|i (?:have|am raising) (?:a |an |my |two |three |four |five |\d+ )?(?:school.age )?(?:children|kids|sons?|daughters?)|my (?:son|daughter|child|children|kids|grandson|granddaughter|grandchildren|stepchild|stepchildren|grandkids)(?:['’]s)?\b|(?:our|my) (?:\w+ ){0,2}child(?:ren)? attend(?:s)? (?:a |the |our )?school|my (?:\d+(?:st|nd|rd|th)[- ]?grader|kindergartener|teenager)\b)"),
    ("school_technology_staff", "school_it_explicit",
     r"\b(?:i(?:'m| am) (?:a |an |the )?(?:(?:school|district) )?(?:technology|it|information technology|network|systems) (?:director|coordinator|administrator|manager|specialist|technician|officer|lead)|as (?:a |an |the )?(?:school|district) (?:it|technology|network|systems) (?:director|coordinator|administrator|manager|specialist)|i (?:work|serve|have worked) (?:as|in the role of) (?:a |an |the )?(?:technology director|it director|technology coordinator|network administrator|technology specialist|school cio)|i (?:manage|maintain|administer) (?:the|our|my) (?:school|district) (?:network|technology|it|systems)\b)"),
    ("school_administrator", "school_leadership_explicit",
     r"\b(?:i(?:'m| am) (?:a |an |the )?(?:superintendent|assistant principal|principal|school board (?:member|trustee|president)|school administrator|district administrator|head of school)|as (?:a |an |the )?(?:school board (?:member|trustee|president)|superintendent|principal|school administrator)|i (?:serve|sit) on (?:the|our|a) (?:school|district) board|i (?:lead|run|oversee) (?:a |the |our |my )?(?:public )?(?:school district|school system)\b)"),
    ("school_educator", "teacher_self_description",
     r"\b(?:i(?:'m| am) (?:a |an |the )?(?:teacher|educator|school counselor|school librarian|paraprofessional|teaching assistant|substitute teacher|instructional aide)|i (?:teach|have taught|taught|used to teach) (?:in |at |for |my )?(?:a |the |our |my )?(?:public |elementary |middle |high |local |charter )?(?:school|classroom|students)|i have (?:been )?(?:a |an )?(?:teacher|educator) for\b|as (?:an? |the )?(?:teacher|educator|school counselor|school librarian|classroom aide|school paraprofessional)\b|in my (?:classroom|teaching career)\b)"),
    ("library_staff", "library_employee_self_description",
     r"\b(?:i(?:'m| am) (?:a |an |the )?(?:librarian|library employee|library assistant|library manager|library director|library technician|library worker|library staff member)|i (?:work|am employed|have worked) (?:at|for|in|by) (?:our |a |the |my )?(?:public |school |county |community )?library(?: system)?|as (?:a |an |the )?(?:librarian|library employee|library director|library worker|library assistant))\b"),
    ("erate_consultant", "consultant_self_description",
     r"\b(?:i(?:'m| am) (?:a |an |the )?e[- ]?rate (?:consultant|advisor|adviser|specialist)|i (?:advise|assist|support|consult for|provide consulting to) (?:schools|school districts|libraries|e[- ]?rate applicants) (?:on|with) (?:their )?e[- ]?rate|i (?:run|own|operate|founded) (?:a |an |my |our )?e[- ]?rate (?:consulting|advisory) (?:firm|company|business)|our e[- ]?rate consulting (?:firm|practice|business)\b)"),
    ("student", "current_student_self_description",
     r"\b(?:i(?:'m| am) (?:a |an |the )?(?:student|high[- ]schooler|college student|high school student|middle school student|university student|grad student|graduate student)|as (?:a |an |the )?(?:student|high[- ]schooler|college student|high school student|university student)|i (?:attend|go to|study at) (?:a |the |my )?(?:public |local |nearby )?(?:high school|middle school|community college|university)|i am in (?:middle school|high school|college|the \d+(?:st|nd|rd|th) grade)\b)"),
    ("researcher", "researcher_self_description",
     r"\b(?:i(?:'m| am) (?:a |an |the )?(?:researcher|scientist|pediatrician|medical doctor|public health professional|physician|child development specialist|academic researcher)|as (?:a |an |the )?(?:researcher|scientist|physician|pediatrician|public health professional)|my research (?:investigates|focuses|examines|studies)|i (?:conduct|have conducted) research (?:on|about|into) (?:education|children|student|school|learning)\b)"),
    ("government", "government_official_self_description",
     r"\b(?:i (?:serve|work) as (?:a |an |the )?(?:city |county |state )?(?:councilmember|commissioner|elected official|legislator|representative|government official)|i (?:am|'m) (?:a |an |the )?(?:city councilmember|state legislator|county commissioner)|as (?:a |an |the )?(?:government official|elected representative|city councilmember)\b)"),
    ("library_board_member", "library_board_explicit",
     r"\b(?:i (?:serve|sit|volunteer) on (?:our |the |a )?(?:local |public )?library (?:board|board of trustees)|as (?:a |the )?(?:library trustee|member of (?:our |the )?library board)\b)"),
    ("school_family_member", "family_connection_not_parent",
     r"\b(?:my (?:niece|nephew|younger sibling|brother|sister|grandchild|grandkids) (?:attend|go|uses|needs)|as (?:an |a )?(?:aunt|uncle|sibling) of (?:a |an )?(?:school|student|child))\b"),
    ("school_alumnus", "former_student_declared",
     r"\b(?:i (?:graduated from|am an alum(?:na|nus)? of|went to|attended) (?:a |my |the )?(?:public |local |high )?school|when i was a student (?:at|in) (?:a |the |my )?(?:public )?(?:school|district))\b"),
    ("library_patron", "library_user_declared",
     r"\b(?:i (?:use|visit|rely on|depend on|frequent) (?:our |my |the |a )?(?:local |public |county |community )?library(?:'s)?|as (?:a |the )?(?:library user|library patron|frequent library visitor)|my (?:local |public )?library (?:helps|allows|provides me|is where i|is how i)\b)"),
    ("school_employee_general", "school_employee_self_description",
     r"\b(?:i (?:work|am employed|have worked|serve|volunteer) (?:for|at|in|with) (?:the |our |a |my )?(?:local |public |private |charter )?(?:school district|school system|school|school board)|i work (?:in|for) (?:the |our |a )?(?:school|district) (?:office|staff|administration|department)|as (?:a |an |the )?school (?:employee|staff member|volunteer|worker))\b"),
    ("taxpayer", "taxpayer_self_description",
     r"\b(?:as (?:a |an |the )?(?:concerned |local |american )?taxpayer|i(?:'m| am) (?:a |an )?(?:concerned |local )?taxpayer|my tax dollars (?:are|should|fund|pay))\b"),
    ("community_resident", "resident_self_description",
     r"\b(?:as (?:a |an |the )?(?:concerned |local |longtime |lifelong )?(?:resident|community member|neighbor|citizen|constituent|voter)|i (?:am|have been) (?:a |an )?(?:resident|community member|citizen|voter) (?:of|in|for)|i live in (?:a |the |our )?(?:rural |small |local )?(?:community|town|district)|as someone who lives in (?:a |the |our )?(?:rural |local )?community)\b"),
    ("retired_educator", "retired_teacher_explicit",
     r"\b(?:i(?:'m| am) (?:a |an |the )?(?:retired|former) (?:teacher|educator|principal|school administrator|superintendent)|as (?:a |an |the )?(?:retired|former) (?:teacher|educator|principal|school administrator)|i taught (?:school|students) for (?:over |more than )?\d+ years)\b"),
    ("education_advocacy_member", "advocacy_organization_membership",
     r"\b(?:i(?:'m| am) (?:a |an )?(?:member|volunteer|organizer) (?:of|with) (?:our |the |a )?(?:parent|school|education|student|library) (?:advocacy |community )?(?:organization|association|coalition|group)|as (?:an |a )?(?:member|volunteer|organizer) of (?:the |our )?(?:parent|school|education|library) (?:advocacy |community )?(?:organization|association|coalition|group))\b"),
]

# Additional identity *facets* for groups that clearly use an authorial
# school/library/family voice without proving a particular job or mandate.
AUTHOR_PATTERNS += [
    ("parent_guardian", "parents_plural_self_description",
     r"\b(?:as parents(?: of (?:students|school children|children))?|"
     r"we (?:are|remain) parents(?: of (?:school|young) children)?|"
     r"our (?:own )?(?:kids|children|sons|daughters) (?:attend|use|need|go|have|are|will|depend)|"
     r"our (?:own )?(?:kids|children|sons|daughters)['’] (?:education|school|future)|"
     r"my (?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth) grader)\b"),
    ("school_community_connection", "first_person_school_connection",
     r"\b(?:at (?:our|my) school|for (?:our|my) school|"
     r"our school's (?:students|teachers|network|budget|technology|internet|library)|"
     r"my school (?:uses|depends|relies|needs|provides|is|has)|"
     r"we (?:at|in) (?:our|the) (?:local |public |rural )?(?:school|district))\b"),
    ("library_community_connection", "first_person_library_connection",
     r"\b(?:our library (?:needs|relies|depends|uses|offers|supports|provides|serves|has)|"
     r"our library's (?:services|patrons|funding|wifi|internet|broadband)|"
     r"at our (?:public |local )?library|"
     r"we (?:at|in) (?:our|the) (?:public |local )?library)\b"),
    ("erate_applicant_voice", "self_identified_erate_applicant",
     r"\b(?:as (?:an? |the )?e[- ]?rate applicant|"
     r"i (?:apply|have applied|am applying) for e[- ]?rate (?:funding|discounts|support)|"
     r"we (?:apply|have applied) for e[- ]?rate (?:funding|discounts|support))\b"),
    ("community_volunteer", "volunteer_self_description",
     r"\b(?:i (?:volunteer|have volunteered) (?:at|for|with) (?:our |the |a )?"
     r"(?:school|district|public library|community center)|"
     r"as (?:a |an )?(?:school|library|community) volunteer)\b"),
]
# Targeted additions derived from individually inspected FCC examples. We keep
# broad roles for self-described schooling and healthcare professionals without
# inventing a named employer or organization-level authority.
AUTHOR_PATTERNS += [
    ("school_educator", "teacher_level_or_subject",
     r"\b(?:as (?:a |an |the )?(?:(?:public|elementary|middle|high|secondary|special education|pre[- ]?k|kindergarten|science|math|english|history) )+(?:school )?teacher|"
     r"i (?:teach|taught) (?:elementary|middle|high) school|"
     r"being (?:a |an )?(?:teacher|school educator)|"
     r"(?:my|our) (?:special education|classroom|high school|middle school|elementary) students)\b"),
    ("retired_educator", "retirement_from_teaching",
     r"\b(?:i (?:have )?(?:just |recently )?retired (?:in \w+ )?(?:from )?teaching|"
     r"i retired (?:in \w+ )?(?:from )?(?:teaching|my teaching career)|"
     r"i was a (?:school |classroom |elementary |high school )?teacher for \d+ years|"
     r"i (?:taught|have taught) (?:elementary|middle|high) school for \d+ years)\b"),
    ("library_staff", "professional_librarian",
     r"\b(?:as (?:a |an |the )?(?:professional |public |school |retired )?librarian|"
     r"i (?:am|'m) (?:a |an |the )?(?:professional |public |school |retired )?librarian|"
     r"i have worked in librar(?:y|ies) for \d+ years)\b"),
    ("school_technology_staff", "it_professional_at_school",
     r"\b(?:as (?:a |an |the )?(?:it|information technology|network|technology) "
     r"professional at (?:a |an |the |our )?(?:[\w&.'-]+ ){0,6}school|"
     r"i (?:am|'m) (?:an? |the )?(?:it|technology|network|information technology) "
     r"professional (?:at|for) (?:a |an |the |our )?(?:[\w&.'-]+ ){0,6}school|"
     r"i (?:manage|coordinate|oversee) e[- ]?rate (?:at|for) (?:our|the|my) district)\b"),
    ("school_board_member", "boe_or_board_member",
     r"\b(?:i (?:am|'m) (?:currently )?(?:a |an |the )?(?:member of (?:the|our) (?:boe|board of education)|"
     r"(?:school|district) board member|board of education member)|"
     r"as (?:a |an |the )?(?:member of (?:the|our) (?:boe|board of education)|"
     r"(?:school|district) board member|board of education member)|"
     r"i (?:serve|sit) on (?:the |our )?(?:board of education|boe)|"
     r"as chair of (?:the |our )?(?:[\w&.'-]+ ){0,9}board of directors,"
     r" (?:a |the )?(?:small |rural |public )*(?:school )?district)\b"),
    ("education_professional", "education_career_declared",
     r"\b(?:i (?:have been|have worked|work|am working) in education for "
     r"(?:over|more than|about|approximately)? ?\d+ years|"
     r"i (?:have worked|work) in (?:public |k[- ]?12 )?education (?:for|since)|"
     r"my \d+(?:st|nd|rd|th)? year (?:working )?in education)\b"),
    ("health_professional", "licensed_child_professional",
     r"\b(?:i (?:am|'m) (?:a |an |the )?(?:licensed |clinical |practicing )?"
     r"(?:psychologist|psychotherapist|mental health clinician|mental health counselor|"
     r"pediatrician|child psychiatrist|social worker|school psychologist)|"
     r"as (?:a |an |the )?(?:licensed |clinical )?(?:psychologist|pediatrician|"
     r"child psychiatrist|mental health clinician))\b"),
]
# A further source-specific pass for user/parent relationships and a filing
# signer's own connection to a school or library. These are not job titles.
AUTHOR_PATTERNS += [
    ("parent_guardian", "homeschool_or_our_children",
     r"\b(?:as (?:a |an |the )?(?:home[- ]?school|homeschooling|home schooling) parent|"
     r"i (?:have been|am|'m) (?:a |an )?(?:home[- ]?school|homeschooling) parent|"
     r"our children(?:[, ]+(?:in|aged|age|who))?[\w ,0-9-]{0,45}"
     r"\b(?:are|have|need|use|spend|attend|go|were|should|require|must|will|depend|struggle|learn|benefit)\b|"
     r"we (?:entrust|are raising|refuse to allow) (?:our|my) (?:children|kids)|"
     r"our children (?:to|from|with) (?:\w+ ){0,7}(?:school|online|screen|device))\b"),
    ("library_patron", "family_uses_library_service",
     r"\b(?:my (?:family|household) (?:has |have )?(?:used|relied on|depended on|visited) "
     r"(?:the |our |a )?(?:public |local |community )?library|"
     r"we (?:need|use|depend on|rely on) (?:wifi|wi[- ]fi|internet) "
     r"(?:at|in|from) (?:the |our |my |a )?(?:public |local )?library|"
     r"we (?:go|come|visit) (?:to )?(?:the |our |my |a )?(?:public |local )?library "
     r"(?:to|for) (?:do )?(?:homework|research|internet))\b"),
    ("library_community_connection", "my_library_service_voice",
     r"\b(?:my library (?:saves|serves|provides|has|uses|depends|relies|offers)|"
     r"my library's (?:budget|internet|e[- ]?rate|funding|patrons|services)|"
     r"(?:program|funding) saves my library (?:money|costs|time))\b"),
]
# In source text, stakeholder words in a copied sample question or bibliography
# are not evidence of *the author*. The regexes above require self-reference.
PATTERNS = [(role, pid, re.compile(rx, re.I)) for role,pid,rx in AUTHOR_PATTERNS]
STRONG_ROLES = {
    "parent_guardian", "school_technology_staff", "school_administrator",
    "school_educator", "library_staff", "erate_consultant", "student",
    "researcher", "government", "library_board_member", "school_family_member",
    "school_alumnus", "library_patron", "school_employee_general",
    "retired_educator", "education_advocacy_member",
    "school_board_member", "education_professional", "health_professional",
}
GENERAL_CIVIC = {"taxpayer","community_resident","school_community_connection",
                 "library_community_connection","erate_applicant_voice","community_volunteer"}
ROLE_PRIORITY = {
    "school_technology_staff": 10, "school_administrator": 11,
    "school_board_member": 12, "health_professional": 16,
    "education_professional": 28,
    "school_educator": 12, "retired_educator": 13,
    "library_staff": 15, "erate_consultant": 16, "researcher": 17,
    "government": 18, "student": 19, "parent_guardian": 20,
    "library_board_member": 25, "school_employee_general": 27,
    "education_advocacy_member": 30, "school_alumnus": 35,
    "school_family_member": 40, "library_patron": 42,
    "school_community_connection": 46,
    "library_community_connection": 47,
    "erate_applicant_voice": 48,
    "community_volunteer": 49,
    "taxpayer": 60, "community_resident": 65,
}
NON_AUTHOR = re.compile(
    r"(?im)^\s*(?:references|bibliography|works cited|endnotes|"
    r"exhibits?|appendices|appendix|additional sources|"
    r"frequently asked questions)\b\s*[:.]?\s*$"
)
QUOTED = re.compile(r"(?m)^\s*(?:>|[“\"]|(?:\d{1,3}[.)]|[-*•])\s)")
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
HAS_ALPHABET = re.compile(r"[a-zA-Z]")


@dataclass(frozen=True)
class Candidate:
    role: str
    pattern_id: str
    confidence: str = "high"
    channel: str = "first_person"


def author_windows(text: str) -> list[tuple[str,str]]:
    text = str(text or "")
    if not text.strip():
        return []
    # Author introduction is allowed to include the opening 5K chars but
    # removes appendices/references and leading quotation lines.
    front = text[:min(5200,len(text))]
    stop = NON_AUTHOR.search(front)
    if stop:
        front = front[:stop.start()]
    front = "\n".join(line for line in front.splitlines()
                      if not QUOTED.match(line))[:4500]
    out = [("intro",front)]
    # Closing region is used for occupational *signatures*, not every
    # first-person quotation in the last 2500 characters of a long filing.
    end = text[-min(len(text),2300):]
    closings = list(re.finditer(
        r"(?im)^[ \t]*(?:respectfully(?: submitted)?|sincerely(?: yours)?|"
        r"best regards|regards|signed|submitted by|with appreciation)"
        r"[ \t]*[,.:]?[ \t]*$",end))
    if closings:
        candidate = end[closings[-1].end():][:750]
        if not NON_AUTHOR.search(candidate):
            out.append(("closing",candidate))
    return out


def declared_roles(text: str) -> list[Candidate]:
    found = {}
    for region,window in author_windows(text):
        for role,pid,rx in PATTERNS:
            if rx.search(window):
                cand = Candidate(role,pid,
                    "medium" if role in GENERAL_CIVIC or region=="closing"
                    else "high", region)
                if role not in found or found[role].confidence == "medium" and cand.confidence == "high":
                    found[role] = cand
    return sorted(found.values(),key=lambda x:ROLE_PRIORITY.get(x.role,999))


def normalize_template(text: str) -> str:
    text = str(text or "")
    # The FCC filing may contain auto-inserted title/footer identifiers.
    # Template discovery is ONLY for identifying coordinated text, not
    # claiming an organizer or assigning individual occupational roles.
    text = EMAIL.sub(" EMAIL ",text).casefold()
    text = re.sub(r"https?://\S+"," URL ",text)
    text = re.sub(r"\b\d[\d\s,./:-]{2,}\b"," NUMBER ",text)
    text = re.sub(r"[^a-z]+"," ",text)
    return " ".join(text.split())[:28000]


def shingles(normalized: str) -> set[int]:
    """Short comments get four-word shingles; long documents use seven."""
    words = normalized.split()
    if len(words)<22:
        return set()
    width = 7 if len(words)>=65 else 4
    chunks = (" ".join(words[i:i+width]) for i in range(len(words)-width+1))
    return {int.from_bytes(hashlib.blake2b(x.encode(),digest_size=8).digest(),"little")
            for x in chunks}


def cluster_templates(records: list[dict], all_source: dict[str,dict]) -> dict[str,dict]:
    # Candidate shortlist via stable minhash banding, then strong Jaccard
    # validation. A common form letter must have >=3 different filer fields.
    sigs = {}
    fingerprints = defaultdict(list)
    exact_texts = defaultdict(list)
    meta_names = {}
    for r in records:
        fid=r["id"]
        source=all_source[fid]
        raw = str(source.get("filer_raw") or "").strip().casefold()
        name = re.sub(r"[^a-z0-9]+"," ",raw).strip()
        meta_names[fid] = name or fid
        normalized=normalize_template(source.get("text",""))
        if len(normalized.split())>=7:
            exact_texts[hashlib.sha256(normalized.encode()).hexdigest()].append(fid)
        sig = shingles(normalized)
        sigs[fid]=sig
        if not sig:
            continue
        mins=sorted(sig)[:12]
        # 3-value bands reduce accidental long boilerplate matches.
        for i in range(0,len(mins)-2,3):
            fingerprints[(i,tuple(mins[i:i+3]))].append(fid)
    parent={r["id"]:r["id"] for r in records}
    def root(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    def merge(x,y):
        a,b=root(x),root(y)
        if a!=b:
            parent[max(a,b)]=min(a,b)
    # Exact short notes can be identical even when too short for robust
    # minhash. Same exact text from >=3 distinct filer fields is an
    # observed template cluster, not proof of organizational coordination.
    for ids in exact_texts.values():
        if len({meta_names[x] for x in ids})>=3:
            for other in ids[1:]:
                merge(ids[0],other)
    seen=set()
    for ids in fingerprints.values():
        if len(ids)>150:
            continue
        for i in range(len(ids)):
            for j in range(i+1,len(ids)):
                a,b=ids[i],ids[j]
                pair=tuple(sorted((a,b)))
                if pair in seen:
                    continue
                seen.add(pair)
                x,y=sigs[a],sigs[b]
                if not x or not y:continue
                overlap=len(x&y)
                sim=overlap/(len(x)+len(y)-overlap)
                is_short=min(len(x),len(y))<60
                minimum=12 if is_short else 40
                threshold=.90 if is_short else .83
                if sim>=threshold and min(len(x),len(y))>=minimum:
                    merge(a,b)
    clusters=defaultdict(list)
    for fid in parent:
        clusters[root(fid)].append(fid)
    result={}
    sizes=Counter()
    for group in clusters.values():
        distinct_filers=len({meta_names[x] for x in group})
        if distinct_filers<3:
            continue
        # A source-text cluster groups similar letters and is NOT a
        # verified organization or political affiliation.
        digest=hashlib.sha256("|".join(sorted(group)).encode()).hexdigest()[:12]
        for fid in group:
            result[fid]={"cluster_id":digest,"filings_in_cluster":len(group),
                         "distinct_filer_fields":distinct_filers}
        sizes[len(group)]+=1
    cluster_templates.stats=dict(sizes)
    return result


def is_personal_filer(raw: str) -> bool:
    raw = " ".join(str(raw or "").split())
    return personal_name_format(raw) and len(raw.split())>=2


def explicitly_submitting_institution(text: str) -> tuple[str,str]:
    """Read only author-title / author-submission statements in opening lines.

    Merely mentioning a school or library as a topic is not an authorship cue.
    A named entity claim is a *provisional source lead*, never verification of
    the individual's legal authority to represent that institution.
    """
    lines=[re.sub(r"\s+"," ",x.strip()) for x in str(text or "")[:2300].splitlines()[:45]]
    for line in lines:
        if not line or len(line)>210:continue
        proposed=""
        matches=(
            re.search(r"(?i)^(?:comments|filing|reply comments|statement) of\s+(.{5,125})$",line),
            re.search(r"(?i)^(.{5,130}?)\s+(?:respectfully\s+)?(?:submits?|files?)\s+"
                      r"(?:these|this|its|our|the)\s+(?:comments|filing|statement)\b",line),
            re.search(r"(?i)^(?:submitted|filed|prepared) (?:on behalf of|by)\s+(.{5,125})$",line),
        )
        for m in matches:
            if m:
                proposed=m.group(1).strip(" .,-:")
                break
        if not proposed:continue
        # Clear corporate/institutional name in an AUTHOR label only.
        name=organization_label(proposed)
        if not name:continue
        role=first_rule(name,ORG_PATTERNS)[0]
        if role and role!="other_vendor":
            return role,name
    # PDFs sometimes concatenate a heading, organization and statement on
    # the same long extracted line; the strict standalone-line matcher above
    # misses these explicit institutional submitter declarations.
    head=re.sub(r"\s+"," ",str(text or "")[:2300])
    for m in re.finditer(
        r"(?i)([A-Za-z][A-Za-z&.' -]{7,100}?"
        r"(?:school district|public schools|public library|library system|"
        r"unified high school district|school corporation|county school board))"
        r"\s*(?:\([A-Z]{2,12}\))?\s+(?:respectfully )?"
        r"(?:submits?|files?)\s+(?:these|its|the|our)\s+(?:comments|filing|statement)\b",
        head,
    ):
        candidate=m.group(1).strip(" .,:;-")
        # Trim preceding title / salutation text, keeping only up to 12 words.
        parts=candidate.split()
        candidate=" ".join(parts[-12:])
        label=organization_label(candidate)
        if label:
            role=first_rule(label,ORG_PATTERNS)[0]
            if role and role!="other_vendor":
                return role,label
    return "",""


def inspect(source=SOURCE, registry=REGISTRY, output=OUTPUT) -> dict:
    source = Path(source)
    registry = json.loads(Path(registry).read_text())
    targets = {r["id"]:r for r in registry["filings"] if r["role"]==TARGET_ROLE}
    manifest=json.loads((source/"manifest.json").read_text())
    raw={}
    for shard in manifest["shards"]:
        p=source/"shards"/shard["name"]
        if hashlib.sha256(p.read_bytes()).hexdigest()!=shard["sha256"]:
            raise ValueError("Source checksum mismatch: "+shard["name"])
        with gzip.open(p,"rt",encoding="utf8") as f:
            for line in f:
                if not line.strip():continue
                row=json.loads(line)
                fid=str(row["submission_id"])
                if fid in targets:
                    raw[fid]=row
    if set(raw)!=set(targets):
        raise ValueError("Source missing target IDs "+str(sorted(set(targets)-set(raw))[:4]))
    template = cluster_templates(list(targets.values()),raw)
    # Argument interests are a *separate axis*, never an inferred identity.
    # Only retain topics from preexisting source-linked claim retrieval.
    topic_by_id={}
    if TOPIC_LEDGER.exists():
        ledger=json.loads(TOPIC_LEDGER.read_text(encoding="utf8"))
        for filing in ledger.get("filings",[]):
            topic_by_id[str(filing["id"])]=sorted({
                str(e.get("topic")) for e in filing.get("topics",[])
                if e.get("topic")})
    rows=[]
    pattern_counts=Counter()
    primary_counts=Counter()
    role_unique_names=defaultdict(set)
    all_name_tokens=set()
    reason_counts=Counter()
    model_hint_counts=Counter()
    interests=Counter()
    for fid,target in sorted(targets.items()):
        r=raw[fid];text=str(r.get("text") or "")
        # Private counting key is never exported. Exact metadata strings may
        # collide or differ, so this remains an approximation of individuals.
        raw_filer=re.sub(r"[^a-z0-9]+"," ",str(r.get("filer_raw") or "").casefold()).strip() or ("filing:"+fid)
        all_name_tokens.add(raw_filer)
        # A pre-existing model is a *search lead*, not proof of capacity.
        # Do not use it to set the source-backed primary role.
        model_path=ROOT/"data/llm_census_kaggle/filings"/(fid+".json")
        model_hint=""
        model_summary=""
        if model_path.exists():
            model=json.loads(model_path.read_text(encoding="utf8"))
            model_hint=str(model.get("stakeholder_role") or "unknown")
            model_summary=str(model.get("summary") or "")
        model_hint_counts[model_hint or "missing"]+=1
        # An organizational contact domain can be a useful manual-review
        # lead even when the original signature is incomplete; do not turn
        # the domain into an occupation or representative mandate.
        domains={m.group(1).lower() for m in re.finditer(
            r"(?i)\b[\w.+-]+@([a-z0-9.-]+\.[a-z]{2,})\b",
            text[-1600:])}
        domain_sectors=sorted({domain_sector(d) for d in domains if domain_sector(d)})
        institutional_role,institutional_name=explicitly_submitting_institution(text)
        signatures=signature_signal(text,str(r.get("filer_raw") or ""))
        roles=declared_roles(text)
        existing=context_capacity(text)
        if existing.role and existing.role not in {c.role for c in roles}:
            # Existing author intro classifier has narrower, source-grounded
            # labels; contradictions are analyst-review flags.
            reason_counts["legacy_context_ambiguity"]+=1
        for c in roles:pattern_counts[c.pattern_id]+=1
        ordered=sorted(roles,key=lambda c:ROLE_PRIORITY[c.role])
        declared_specific=[c for c in ordered if c.role in STRONG_ROLES]
        civic=[c for c in ordered if c.role in GENERAL_CIVIC]
        main=(declared_specific or civic or [None])[0]
        cluster=template.get(fid)
        # Separate occupational identity, self-declared civic identity, and
        # campaign participation; none can substitute for each other.
        if declared_specific:
            status="explicit_non_occupational_or_sector_identity"
            if main.role in {"school_technology_staff","school_administrator","school_educator",
                             "library_staff","erate_consultant","researcher","government","student",
                             "retired_educator","school_employee_general","school_board_member",
                             "education_professional","health_professional"}:
                status="explicit_professional_or_school_role"
        elif civic:
            status="explicit_civic_capacity"
        elif cluster:
            status="no_self_declared_role__template_participant"
        elif not text.strip():
            status="no_readable_source"
        else:
            status="no_source_supported_capacity"
        primary_counts[(main.role if main else "none")]+=1
        role_unique_names[main.role if main else "none"].add(raw_filer)
        reason_counts[status]+=1
        topics=topic_by_id.get(fid,[])
        interests.update(topics)
        rows.append({
            "filing_id":fid,
            "source_url":"https://www.fcc.gov/ecfs/filing/"+fid,
            "current_role":target["role"],
            "identity_status":target["identity_status"],
            "new_primary_role_candidate":main.role if main else None,
            "identity_basis":main.pattern_id if main else None,
            "evidence_window":main.channel if main else None,
            "confidence":main.confidence if main else "none",
            "independent_capacity_kind":status,
            "all_self_declared_capacity_candidates":[
                {"role":c.role,"pattern_id":c.pattern_id,"confidence":c.confidence}
                for c in ordered],
            "suspected_template_cluster":cluster,
            "readable_source":bool(text.strip()),
            "ocr_candidate":str(r.get("has_unreviewed_ocr","0"))=="1",
            "source_chars":len(text),
            "detected_argument_themes":topics,
            "source_length_band":("missing" if not text.strip()
                else "very_brief" if len(text)<150 else "brief" if len(text)<500
                else "medium" if len(text)<2000 else "long"),
            "has_personal_name_metadata":is_personal_filer(r.get("filer_raw","")),
            "signature_occupation_candidate":signatures.role or None,
            "institutional_submission_role_lead":institutional_role or None,
            "institutional_submission_name_lead":institutional_name or None,
            "contact_domain_sector_leads":domain_sectors,
            "independent_model_role_lead":model_hint or None,
            "independent_model_specificity_lead":bool(model_hint and model_hint not in ("unknown","individual_other")),
            "cross_filing_review":bool(target.get("attribution_review")),
            "automatic_reclassification":False,
        })
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    report={
        "schema_version":"identity-562-experimental-v1",
        "scope":"Entire existing named_person_capacity_unstated filing cohort on local research branch",
        "publication_status":"EXPERIMENTAL_UNPUBLISHED__NOT_SITE_DATA",
        "filing_target_count":len(rows),
        "distinct_normalized_filer_fields":len(all_name_tokens),
        "unique_filer_fields_by_primary_role":{k:len(v) for k,v in role_unique_names.items()},
        "distinct_filing_ids":len({x["filing_id"] for x in rows}),
        "primary_role_counts":dict(primary_counts),
        "pattern_counts":dict(pattern_counts),
        "independent_model_role_leads":dict(model_hint_counts),
        "cases_with_contact_domain_sector_lead":sum(bool(x["contact_domain_sector_leads"]) for x in rows),
        "cases_with_explicit_institutional_submission_lead":sum(bool(x["institutional_submission_role_lead"]) for x in rows),
        "cases_with_specific_independent_model_lead":sum(x["independent_model_specificity_lead"] for x in rows),
        "disposition_counts":dict(reason_counts),
        "template_cluster_sizes":getattr(cluster_templates,"stats",{}),
        "source_length_distribution":dict(Counter(x["source_length_band"] for x in rows)),
        "detected_argument_theme_counts":dict(interests.most_common()),
        "template_participant_filings":len(template),
        "readable_targets":sum(x["readable_source"] for x in rows),
        "remaining_without_occupational_or_self_declared_civic_capacity":
            sum(x["new_primary_role_candidate"] is None for x in rows),
        "limitations":[
          "Counts reflect source-text evidence rules, not verified occupations or employer authority.",
          "A person may be a parent, taxpayer and educator simultaneously. Primary role prioritizes specificity; all evidence candidates are retained.",
          "Matched form letters indicate similar source text, not an organizer, a paid campaign, or a shared policy preference.",
          "No outside employer lookup has been performed. Same-name matches require separate corroboration.",
          "We cannot infer missing careers for people who do not say what they do. An unclassified occupation is not an unidentified person.",
        ],
    }
    (output/"summary.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    (output/"review_queue.json").write_text(json.dumps({"summary":report,"records":rows},
                                                     indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:report[k] for k in (
        "filing_target_count","primary_role_counts","disposition_counts",
        "template_participant_filings",
        "remaining_without_occupational_or_self_declared_civic_capacity")},indent=2))
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=SOURCE)
    p.add_argument("--registry",type=Path,default=REGISTRY)
    p.add_argument("--output",type=Path,default=OUTPUT)
    args=p.parse_args()
    inspect(args.source,args.registry,args.output)
