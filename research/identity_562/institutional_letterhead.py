#!/usr/bin/env python3
"""Find organizational letterheads and direct author statements among leftover FCC files.

URL/brand signals are analyst leads, NOT an inferred employer or authorized
representative. Only names of *organizations* explicitly in original source
are retained. Person names, signatures, addresses and emails are never output.
"""
import json
import re
from collections import Counter
from research.identity_562.deep_investigation import load
from research.identity_562.analyze_individuals import OUTPUT

WEB=re.compile(r"(?i)(?<!@)(?<!\w)(?:https?://)?(?:www\.)?"
               r"([a-z0-9][a-z0-9.-]{2,90}\.(?:org|edu|net|com|us))\b")
SKIP=("fcc.gov","ecfs.fcc.gov","github.com","gmail.com","google.com",
      "outlook.com","yahoo.com","doi.org","youtube.com","facebook.com")
AUTHORS=re.compile(
    r"(?im)^\s*([A-Z][A-Za-z0-9 &,.'\-\(\)]{6,125}?"
    r"(?:School District|Public Library|Library System|Community Library|"
    r"University|Educational Foundation|Education Association|"
    r"Coalition|Foundation|Association|Institute|Network|Nonprofit))"
    r"\s+(?:respectfully\s+)?(?:submits?|files?|offers?)\s+"
    r"(?:its|their|these|this|our|the)\s+(?:comments|filing|statement)\b")
AUTHORIZATION=re.compile(
    r"(?im)\b(?:i (?:write|submit|comment) (?:on behalf of|for)|"
    r"we (?:submit|write|comment) on behalf of)\s+"
    r"((?:(?:[A-Z][\w&.,'\-]+)\s*){2,10})")
ORG_END=re.compile(r"(?i)\b(?:Association|Foundation|Institute|Coalition|"
                   r"Library|Libraries|School District|Network|Corporation|"
                   r"Public Schools|Inc|LLC)\b")
def safe_org_name(s):
    s=" ".join(str(s or "").split()).strip(" ,.;:-")
    if len(s)>130 or len(s.split())<2 or not ORG_END.search(s):
        return ""
    if re.search(r"(?i)\b(?:fcc|federal communications commission|"
                 r"the commission|please|dear|would|should|these comments)\b",s):
        return ""
    return s

def scan(text):
    text=str(text or "")
    intro=text[:min(len(text),2000)]
    first_lines="\n".join(intro.splitlines()[:12])[:1200]
    hosts=sorted({m.group(1).lower() for m in WEB.finditer(first_lines)
                  if not any(m.group(1).lower().endswith(z) for z in SKIP)})
    submit=[]
    for match in AUTHORS.finditer(intro):
        n=safe_org_name(match.group(1))
        if n:submit.append(n)
    behalf=[]
    for match in AUTHORIZATION.finditer(intro):
        n=safe_org_name(match.group(1))
        if n:behalf.append(n)
    return hosts,list(dict.fromkeys(submit)),list(dict.fromkeys(behalf))

def run():
    earlier=json.loads((OUTPUT/"model_and_phrase_review.json").read_text())
    unresolved={x["filing_id"] for x in earlier["records"]}
    selected={str(x["submission_id"]):x for x in load()
              if str(x["submission_id"]) in unresolved}
    assert set(selected)==unresolved
    records=[]; counters=Counter()
    for fid,rec in selected.items():
        domains,submitted,behalf=scan(rec.get("text",""))
        if not (domains or submitted or behalf):continue
        if submitted or behalf:
            kind="explicit_institutional_author_lead"
        else:
            kind="letterhead_website_only"
        counters[kind]+=1
        records.append({
            "filing_id":fid,
            "source_url":"https://www.fcc.gov/ecfs/filing/"+fid,
            "review_type":kind,
            "first_page_organization_websites":domains,
            "explicit_institution_names":submitted,
            "on_behalf_of_names":behalf,
            "automatic_employer_or_representative_attribution":False,
        })
    result={"schema":"unpublished-org-letterhead-v1",
            "checked_filings":len(unresolved),
            "organization_clue_count":len(records),
            "types":dict(counters),
            "records":sorted(records,key=lambda x:x["filing_id"])}
    (OUTPUT/"institutional_letterhead_leads.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(result,indent=2,ensure_ascii=False)[:14000])
    return result
if __name__=="__main__":run()
