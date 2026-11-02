#!/usr/bin/env python3
"""Resolve the FCC author's *capacity* from first-person source language.

Evidence comes only from a short opening and closing/signature neighborhood;
policy argument vocabulary, quotations of the FCC NPRM and bibliographies
must never be mistaken for an author identity. All contextual inferences
remain machine predictions, not verified representative authority.

This module intentionally does not handle names or contact details.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Capacity:
    role: str = ""
    basis: str = ""
    cue: str = ""
    confidence: str = "medium"

# Prioritized, mutually exclusive when possible. Use first-person local context,
# NOT the occurrence of generic 'teachers', 'parents', 'consultants' or 'libraries'.
PATTERNS = [
    ("parent_guardian", "self_declared_parent", "first_person_parent",
     r"\b(?:as (?:an? |the |a concerned |a working |a (?:taxpayer|taxpaxer) and a )"
     r"(?:parent|mother|father|guardian|caregiver)|i am (?:a |an |the |also a )?"
     r"(?:parent|mother|father|guardian)|i (?:have|am raising) (?:\d+ |two |three |four )?"
     r"(?:children|kids|school[- ]age children)|my (?:son|daughter|child|children|kids) "
     r"(?:is|are|was|were|attends?|go(?:es)? to|has|have|uses?|go))\b"),
    ("school_technology_staff", "author_technical_capacity", "first_person_school_IT",
     r"\b(?:i (?:am|serve as|work as|have served as) (?:the |an? )?"
     r"(?:district |school )?(?:it director|tech(?:nology)? director|network administrator|"
     r"technology coordinator|chief technology officer)|i (?:manage|administer|oversee) "
     r"(?:our|the|my) (?:school|district).{0,55}(?:network|it systems|technology infrastructure))\b"),
    ("school_administrator", "author_school_leadership", "first_person_school_administrator",
     r"\b(?:i (?:am|serve as|work as|have served as) (?:the |an? )?"
     r"(?:superintendent|principal|school administrator|school board (?:member|president)|"
     r"district administrator)|as (?:the |a )?(?:superintendent|principal|"
     r"school administrator|school board member)|i (?:lead|oversee) "
     r"(?:our|the|my) (?:school district|district))\b"),
    ("school_educator", "author_teaching_capacity", "first_person_teacher",
     r"\b(?:i (?:am|have been|work as|serve as) (?:an? |the )?"
     r"(?:teacher|educator|classroom instructor|schoolteacher)|"
     r"i teach (?:at|in|for|students|children|elementary|middle|high)|"
     r"in my classroom|my students (?:use|need|learn|have|are|receive))\b"),
    ("library_staff", "author_library_staff_capacity", "first_person_librarian",
     r"\b(?:i (?:am|serve as|work as|have worked as) (?:an? |the )?"
     r"(?:librarian|library director|library manager|library employee)|"
     r"i work (?:at|for|in) (?:the |a |our )?(?:public |school |community )?library|"
     r"i (?:manage|direct|run|lead) (?:our|a|the) (?:public |school |community )?library)\b"),
    ("erate_consultant", "author_consulting_capacity", "first_person_erate_consultant",
     r"\b(?:i (?:am|work as|serve as|have worked as) (?:an? |the )?"
     r"e[- ]?rate (?:consultant|advisor|adviser)|"
     r"as (?:an? |the )?e[- ]?rate (?:consultant|advisor|adviser)|"
     r"our (?:e[- ]?rate )?consulting (?:firm|business|practice) (?:helps|serves|works|assists))\b"),
    ("library_affiliated", "author_library_affiliation", "first_person_library_affiliation",
     r"\b(?:our library (?:is|serves|provides|offers|depends|relies|has|uses|connects|operates|supports)|"
     r"at our library[, ]|we (?:at|here at) (?:the |our )?library\b|"
     r"the library (?:where|at which) i (?:work|volunteer|serve))\b"),
    ("school_connected_unknown", "author_school_affiliation", "first_person_school_affiliation",
     r"\b(?:our (?:school district|district|schools?|classrooms?) "
     r"(?:is|are|has|have|serves|serve|uses|use|depends|relies|needs|need|provides|provide|"
     r"operates|operate|would|could|will)|"
     r"at our (?:school|district)[, ]|we (?:as|at) (?:a|our|the) (?:school|district)\b)\b"),
]

COMPILED = [(r,b,c,re.compile(p,re.I)) for r,b,c,p in PATTERNS]
STOP = re.compile(r"(?im)^\s*(?:references|bibliography|works cited|endnotes|appendix|footnotes)\b\s*[:.]?")
QUOTE_PREFIX = re.compile(r"^\s*(?:>|“|\"|[•*]|\d{1,2}[.)]\s+)")

def author_intro(text: str) -> str:
    t=text[:min(len(text), 4500)]
    stop=STOP.search(t)
    if stop:t=t[:stop.start()]
    # Text extraction can concatenate a bibliography heading onto the same
    # line as the preceding paragraph. Once past the opening, strip those.
    inline_refs=re.search(r"(?i)\b(?:references|bibliography|works cited)\s*:",t[800:])
    if inline_refs:t=t[:800+inline_refs.start()]
    # Quoted policy excerpts are not an author introduction. Keep normal prose.
    lines=[s for s in t.splitlines() if not QUOTE_PREFIX.match(s)]
    return "\n".join(lines)[:3700]

def context_capacity(text: str) -> Capacity:
    t=author_intro(text)
    # The first occurrence of a credible first-person context signal wins
    # within each specificity tier; generic library/school follows explicit jobs.
    for role,basis,cue,rx in COMPILED:
        m=rx.search(t)
        if m:
            return Capacity(role,basis,cue,"high" if basis in {
                "self_declared_parent","author_technical_capacity",
                "author_school_leadership","author_teaching_capacity",
                "author_library_staff_capacity","author_consulting_capacity"}
                else "medium")
    return Capacity()

def known_subjective_capacity(text: str) -> bool:
    """Personal-name filer with explicit capacity signal, even if role is broad."""
    return bool(context_capacity(text).role)
