#!/usr/bin/env python3
"""Unpublished full-document E-Rate stakeholder investigation.

Adds source-backed role evidence from *all* of the original comment text,
and compares repeated policy letters against ALL 3,231 original filings.
Never guesses an occupation from a model or topic, and never changes the site.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from research.identity_562.analyze_individuals import (
    SOURCE, REGISTRY, OUTPUT, TARGET_ROLE, normalize_template, QUOTED
)

# New rules are explicitly grounded in commenters' own statements.
ROLE_RULES=[
 ("school_educator","school_staff_teaching",
  r"\b(?:i (?:am|'m|was) (?:an? |the )?(?:current |former )?"
  r"(?:school|classroom|special education|high school|elementary) (?:teacher|educator)|"
  r"my (?:students|classroom|pupils) (?:use|need|benefit|rely|depend)|"
  r"i (?:teach|taught|have taught) (?:at|in) (?:an? |the |our )?"
  r"(?:elementary|middle|high|public|rural) school)\b"),
 ("school_administrator","school_administrator",
  r"\b(?:i (?:am|'m|serve|work) as (?:a |the |an )?"
  r"(?:principal|superintendent|assistant principal|school administrator)|"
  r"as (?:a |the )?(?:principal|superintendent|assistant principal))\b"),
 ("school_technology_staff","school_network_staff",
  r"\b(?:i (?:manage|maintain|administer|oversee|run) (?:our|the|my)"
  r" (?:district|school) (?:network|technology|it systems)|"
  r"as (?:an? |the )?(?:school |district )?(?:it|network|technology)"
  r" (?:director|coordinator|administrator|manager|specialist))\b"),
 ("library_staff","library_employee",
  r"\b(?:i (?:work|am employed|have worked) (?:at|in|for)"
  r" (?:our |the |a )?(?:(?:local|public|school|county) ){0,3}library|"
  r"as (?:a |the )?(?:public |school )?(?:librarian|library director|library worker)|"
  r"my job (?:at|in) (?:our |the |a )?library)\b"),
 ("parent_guardian","parent_child_school",
  r"\b(?:my (?:child|children|son|daughter|kids) (?:attend|attends|uses|use|"
  r"are|is|were|was|have|has|need|needs) (?:[a-z'-]+ ){0,7}"
  r"(?:school|classroom|internet|device|schoolwork|technology|library|screens?)|"
  r"i (?:send|have sent) (?:my|our) (?:child|children|son|daughter|kids)"
  r" to (?:a |the |our )?(?:public |private )?school)\b"),
 ("school_board_member","school_board_voice",
  r"\b(?:i (?:serve|sit) on (?:the |our )?(?:school board|board of education)|"
  r"as (?:a |the )?(?:school board|board of education) (?:member|trustee))\b"),
 ("library_patron","library_user",
  r"\b(?:i (?:rely on|depend on|use|visit) (?:our |my |the |a )?"
  r"(?:public |local |community )?library|"
  r"my family (?:uses|relies on|depends on|visits) (?:our |the |a )?"
  r"(?:public |local )?library)\b"),
 ("health_professional","health_professional",
  r"\b(?:i (?:am|'m) (?:a |an )?(?:licensed |clinical )?"
  r"(?:psychologist|pediatrician|psychotherapist)|"
  r"as (?:a |an )?(?:licensed |clinical )?"
  r"(?:psychologist|pediatrician|psychotherapist))\b"),
 ("erate_consultant","erate_professional",
  r"\b(?:i (?:am|'m|work as) (?:a |an )?e[- ]?rate (?:consultant|advisor)|"
  r"as (?:an? |the )?e[- ]?rate (?:consultant|advisor))\b"),
 ("school_community_connection","our_school",
  r"\b(?:our (?:school district|school|district) (?:relies|depends|needs|"
  r"receives|would lose|is|has)|we (?:at|in) (?:the |our )?"
  r"(?:school|district))\b"),
 ("library_community_connection","our_library",
  r"\b(?:our (?:public |local )?library (?:relies|needs|provides|receives|"
  r"serves|would lose|is)|we (?:at|in) (?:the |our )?(?:public )?library)\b"),
]
COMPILED=[(role,signal,re.compile(p,re.I)) for role,signal,p in ROLE_RULES]
SECTIONS=re.compile(r"(?im)^\s*(?:references|bibliography|works cited|"
                    r"table of contents|appendices|exhibits)\s*[:.]?\s*$")

def inspect_entire_source(text):
    text=str(text or "")
    stop=SECTIONS.search(text)
    if stop:text=text[:stop.start()]
    matches=[]
    for role,signal,rx in COMPILED:
        for m in rx.finditer(text):
            line=text[text.rfind("\n",0,m.start())+1:m.start()]
            if QUOTED.match(line):continue
            matches.append({"role":role,"evidence_code":signal,
                            "char_offset":m.start(),"source":"full_original_text"})
            break
    return matches

def load():
    manifest=json.loads((SOURCE/"manifest.json").read_text())
    for shard in manifest["shards"]:
        path=SOURCE/"shards"/shard["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=shard["sha256"]:
            raise RuntimeError("FCC corpus SHA mismatch")
        with gzip.open(path,"rt",encoding="utf8") as f:
            for line in f:
                if line.strip():yield json.loads(line)

def run():
    original=json.loads((OUTPUT/"review_queue.json").read_text())["records"]
    unresolved={r["filing_id"] for r in original
                if not r["new_primary_role_candidate"]}
    all_source=list(load())
    source={str(r["submission_id"]):r for r in all_source}
    registry={x["id"]:x["role"] for x in json.loads(REGISTRY.read_text())["filings"]}
    assert all(fid in source for fid in unresolved)
    fingerprints=defaultdict(list)
    for rec in all_source:
        norm=normalize_template(rec.get("text",""))
        if len(norm.split())>=7:
            fingerprints[hashlib.sha256(norm.encode()).hexdigest()].append(
                str(rec["submission_id"]))
    templates={}
    for ids in fingerprints.values():
        if len(ids)<2:continue
        outside=set(ids)-unresolved
        if not outside:continue
        for fid in set(ids)&unresolved:
            templates[fid]={
                "same_text_filing_count":len(ids),
                "outside_cohort_role_distribution":dict(
                    Counter(registry.get(x,"unknown") for x in outside)),
                "caution":"shared text proves no shared employment or authority"
            }
    result=[]
    counts=Counter()
    for fid in sorted(unresolved):
        comment=source[fid]
        matches=inspect_entire_source(comment.get("text",""))
        if matches:status="new_full_document_self_identity"
        elif fid in templates:status="matched_full_corpus_text_only"
        else:status="profession_not_evidenced"
        counts[status]+=1
        for m in matches:counts["role:"+m["role"]]+=1
        result.append({"filing_id":fid,
                       "source_url":"https://www.fcc.gov/ecfs/filing/"+fid,
                       "status":status,
                       "new_source_roles":matches,
                       "text_match":templates.get(fid),
                       "auto_published":False})
    report={"schema":"unpublished-full-document-v1",
            "source_filing_count":len(all_source),
            "unresolved_filing_count":len(unresolved),
            "dispositions":dict(counts),
            "records":result}
    (OUTPUT/"deep_full_document_evidence.json").write_text(
        json.dumps(report,indent=2)+"\n")
    print(json.dumps({"source":len(all_source),"unresolved":len(unresolved),
                      "dispositions":dict(counts)},indent=2))
    return report

if __name__=="__main__":run()
