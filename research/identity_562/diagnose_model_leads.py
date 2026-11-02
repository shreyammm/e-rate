#!/usr/bin/env python3
"""Diagnostic only: redact model-lead FCC source snippets for rule debugging.

No names/emails/phones are exported or logged. This is not a public website
endpoint and does not change identity classifications.
"""
import gzip,json,re
from collections import defaultdict
from pathlib import Path
from scripts.build_player_registry import ROOT
from research.identity_562.analyze_individuals import REGISTRY,SOURCE,TARGET_ROLE

EMAIL=re.compile(r"(?i)[\w.+-]+@[\w.-]+\.[a-z]{2,}")
PHONE=re.compile(r"(?<!\d)(?:\+1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}(?!\d)")
FULL_NAME=re.compile(r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b")
STREET=re.compile(r"\b\d{1,6}\s+(?:\w+\s+){1,4}(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Boulevard|Ln|Lane|Dr|Drive)\b",re.I)
URL=re.compile(r"https?://\S+")
CUE=re.compile(r"(?i)(?:\b(?:librar|school|district|parent|educat|teacher|"
               r"public school|our school|our students|student|k12|e-rate|"
               r"government|we at|our library|principal|staff)\b)")

def safe(s,name=""):
    s=str(s or "")
    if name and name.strip():
        s=re.sub(re.escape(name.strip()),"[FILER]",s,flags=re.I)
    s=EMAIL.sub("[EMAIL]",s)
    s=PHONE.sub("[PHONE]",s)
    s=STREET.sub("[STREET]",s)
    s=URL.sub("[URL]",s)
    s=FULL_NAME.sub("[PROPER-NAME]",s)
    s=re.sub(r"\b\d{7,}\b","[NUMBER]",s)
    return " ".join(s.split())

def main():
    target={f["id"] for f in json.loads(REGISTRY.read_text())["filings"]
            if f["role"]==TARGET_ROLE}
    model={}
    for fid in target:
        p=ROOT/"data/llm_census_kaggle/filings"/(fid+".json")
        if p.exists():
            r=json.loads(p.read_text())
            model[fid]=str(r.get("stakeholder_role") or "unknown")
    by=defaultdict(list)
    manifest=json.loads((SOURCE/"manifest.json").read_text())
    for shard in manifest["shards"]:
        with gzip.open(SOURCE/"shards"/shard["name"],"rt",encoding="utf8") as f:
            for line in f:
                if not line.strip():continue
                r=json.loads(line)
                fid=str(r["submission_id"])
                if fid not in target:continue
                label=model.get(fid,"missing")
                if label not in {"library","school_district","school_staff","parent_guardian",
                                 "advocacy_group","unknown"}:continue
                text=str(r.get("text") or "")
                if not text.strip():continue
                opener=safe(text[:min(len(text),600)],r.get("filer_raw",""))[:230]
                # Cue candidates in original prose, not LLM inventions.
                lines=[safe(x,r.get("filer_raw","")) for x in text[:2500].splitlines()]
                cues=[x[:220] for x in lines if CUE.search(x) and 15<len(x)<360][:3]
                tail=safe(text[-450:],r.get("filer_raw",""))[:210]
                by[label].append({"id":fid,"length":len(text),"opening":opener,
                                  "source_cue_lines":cues,"tail":tail})
    for key in ["library","school_district","school_staff","parent_guardian",
                "advocacy_group","unknown"]:
        entries=sorted(by[key],key=lambda x:x["length"])
        picks=[]
        if entries:
            for q in (0,.08,.25,.5,.75,.95):
                e=entries[int((len(entries)-1)*q)]
                if e["id"] not in {x["id"] for x in picks}:
                    picks.append(e)
        print("##",key,"count",len(entries))
        for e in picks:
            print(json.dumps(e,ensure_ascii=False))
if __name__=="__main__":main()
