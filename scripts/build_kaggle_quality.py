#!/usr/bin/env python3
"""Build transparent per-filing QA diagnostics from the completed Kaggle census.

This is deterministic quality triage, not human validation and not automatic
correction of machine-coded stances. No source quotes or interpretations are
changed in the original model JSON.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTINUATION=re.compile(
    r"\b(?:continu(?:e|ation)|maintain|preserv(?:e|ation)|fully fund|keep|protect|"
    r"reject (?:any )?(?:cut|sunset|eliminat)|oppose (?:any )?(?:cut|sunset|eliminat))\b",re.I)
FUNDING=re.compile(r"\b(?:e[\s-]?rate|funding|subsid|program)\b",re.I)

def build(files:Path,index:Path,output:Path):
    records=json.loads(index.read_text(encoding="utf-8"))["filings"]
    by_id={str(r["id"]):r for r in records}
    audit={}
    full=selective=no_claim=ocr=polarity=0
    for path in sorted(files.glob("*.json")):
        d=json.loads(path.read_text(encoding="utf-8"))
        if d.get("status")!="complete":
            continue
        sid=str(d["submission_id"])
        if sid not in by_id:
            raise ValueError(f"Missing source metadata for {sid}")
        claims=d.get("claims",[])
        scope=str(d.get("semantic_scope") or "unknown")
        full += scope=="full_text"
        selective += scope!="full_text"
        no_claim += not bool(claims)
        ocrflag=str(d.get("has_unreviewed_ocr","0"))=="1"
        ocr += ocrflag
        mistakes=[]
        for i,c in enumerate(claims):
            if c.get("provision_id")!="erate_sunset" or c.get("position")!="support":
                continue
            action=str(c.get("requested_action") or "")
            argument=str(c.get("argument") or "")
            if (CONTINUATION.search(action) and
                (FUNDING.search(action) or FUNDING.search(argument))):
                mistakes.append(i)
        polarity += bool(mistakes)
        meta=by_id[sid]
        audit[sid]={
            "filing_id":sid,
            "filer":str(d.get("filer_raw") or meta.get("organization") or ""),
            "verified_role_crosswalk":str(meta.get("role") or "unresolved"),
            "semantic_scope":scope,
            "source_windows_available":int(d.get("source_windows_total") or 0),
            "source_windows_model_analyzed":int(d.get("source_windows_model_analyzed") or 0),
            "number_claims":len(claims),
            "number_policy_issues":len(d.get("positions") or {}),
            "ocr_candidate":bool(ocrflag or meta.get("ocr")),
            "suspected_sunset_polarity_claim_indices":mistakes,
            "known_interpretation_risks":(
                ["partial_original_text_model_reading"] if scope!="full_text" else [])+
                (["no_source_grounded_claims_extracted"] if not claims else [])+
                (["possible_sunset_support_direction_reversal"] if mistakes else [])+
                (["unreviewed_ocr_candidate"] if ocrflag or meta.get("ocr") else []),
            "model_output_url":"https://github.com/shreyammm/e-rate/blob/main/data/llm_census_kaggle/filings/"+sid+".json",
            "original_source_url":"https://www.fcc.gov/ecfs/filing/"+sid,
        }
    if len(audit)!=3230:
        raise ValueError(f"Expected 3230 complete Kaggle filings, found {len(audit)}")
    if full+selective!=len(audit):
        raise ValueError("Semantic scope rows do not reconcile with model-processed filings")
    payload={
        "version":"kaggle-filing-quality-v1",
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "publication_status":"AUTOMATIC_QA_FLAGS_NOT_HUMAN_VALIDATION",
        "coverage":{"processed_readable_filings":len(audit),"full_text":full,
                    "prioritized_windows":selective,"no_source_grounded_claims":no_claim,
                    "unreviewed_ocr":ocr,
                    "filings_with_action_direction_suspected_sunset_reversal":polarity},
        "interpretation":"These are candidate error flags only. Never recode direction or publish support/opposition totals as human validated.",
        "filings":audit,
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    return payload

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--filings",type=Path,default=ROOT/"data/llm_census_kaggle/filings")
    p.add_argument("--index",type=Path,default=ROOT/"docs/data/corpus_index.json")
    p.add_argument("--output",type=Path,default=ROOT/"docs/data/kaggle/filing_quality.json")
    a=p.parse_args()
    out=build(a.filings,a.index,a.output)
    print(json.dumps(out["coverage"],indent=2))
if __name__=="__main__":main()
