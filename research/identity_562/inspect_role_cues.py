#!/usr/bin/env python3
"""Privacy-redacted diagnostic excerpts for independently detected author phrases.

Use only on the unpublished research branch. IDs identify already-public FCC
filings; redaction removes submitter name, email, postal address and phone.
"""
import gzip,json,re
from research.identity_562.analyze_individuals import SOURCE,OUTPUT
from research.identity_562.diagnose_model_leads import safe

PRIORITY=re.compile(
  r"(?i)(erate service provider|employed at|chair of the|professional genealogist|"
  r"retired kcls|retired nyc|unemployed|supervisor of network|telecommunications regulator|"
  r"public library employee|former high school|teaching high school|chapter leader|"
  r"in college|single mom|senior citizen|former employee of|library page|"
  r"unhoused|young person|private citizen|library as|rural public library|"
  r"responsible for network|resident)")

def run():
    report=json.loads((OUTPUT/"model_and_phrase_review.json").read_text())
    chosen={}
    for row in report["records"]:
        matches=[p for p in row["author_phrase_leads"]
                 if PRIORITY.search(p["generic_word_prefix"])]
        if matches:chosen[row["filing_id"]]=matches[:3]
    manifest=json.loads((SOURCE/"manifest.json").read_text())
    texts={}
    for shard in manifest["shards"]:
        with gzip.open(SOURCE/"shards"/shard["name"],"rt",encoding="utf8") as f:
            for line in f:
                if not line.strip():continue
                d=json.loads(line)
                fid=str(d["submission_id"])
                if fid in chosen:texts[fid]=d
    for fid,events in sorted(chosen.items()):
        row=texts[fid]
        print("##",fid, "file_length",len(row.get("text") or ""))
        for event in events:
            at=event["offset"]
            original=str(row.get("text") or "")
            excerpt=original[max(0,at-65):min(len(original),at+235)]
            print("SOURCE_CUE",event["cue"],safe(excerpt,row.get("filer_raw",""))[:280])
if __name__=="__main__":run()
