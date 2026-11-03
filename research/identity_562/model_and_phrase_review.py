#!/usr/bin/env python3
"""Unpublished independent-model adjudication and unscripted author cue inventory.

Only retain LLM roles supported by the model's original-source evidence flag
and matching SHA256, and treat other model tags as hypotheses, not labels.
Search all original text for unanticipated author-title phrasing without
converting mere policy discussion into employment.
"""
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from research.identity_562.analyze_individuals import ROOT, SOURCE, OUTPUT, normalize_template, QUOTED

MODEL_DIR=ROOT/"data/identity_llm/filings"
AUTHOR_CUES=[
 ("i_am",re.compile(r"\bi (?:am|'m|was|have been) (?:also )?(?:an? |the )?([a-z][\w -]{2,75})",re.I)),
 ("as_a",re.compile(r"\bas (?:an? |the )([a-z][\w -]{2,75})",re.I)),
 ("i_work",re.compile(r"\bi (?:work|worked|am employed|have worked) (?:for|at|as|in) ([a-z][\w -]{2,75})",re.I)),
 ("my_role",re.compile(r"\b(?:my (?:role|job|position|career)|in my professional capacity) (?:as|is|involves?) ([a-z][\w -]{2,75})",re.I)),
 ("we_at",re.compile(r"\bwe (?:at|with|represent|work for) ([a-z][\w -]{2,75})",re.I)),
 ("signed_title",re.compile(r"(?im)^\s*(?:title|role|position|occupation)\s*[:\-]\s*([a-z][\w -]{2,75})\s*$",re.I)),
]
NEGATIVE=set(("concerned citizen","concerned parent","citizen","taxpayer","person",
"strong supporter","member of the public","someone who","former student",
"resident of","long time","little girl","member","a parent","opponent",
"supporter of the e rate program","user of the internet"))
CUT=re.compile(r"\b(?:and|but|because|so that|who|which|when|where|with|without|"
               r"regarding|about|in support|in opposition|to ensure|for more than)\b",re.I)

def cue_phrases(text):
    text=str(text or "")
    hits=[]
    for code,rx in AUTHOR_CUES:
        for m in rx.finditer(text):
            line=text.rfind("\n",0,m.start())
            prefix=text[line+1:m.start()]
            if QUOTED.match(prefix):continue
            raw=m.group(1)
            phrase=CUT.split(raw,1)[0].strip(" \n.,:;!?")
            # No names, addresses or organization tokens are shared from this
            # probe. Only first two generic lower-case words are retained.
            words=re.findall(r"[a-z]+",phrase.lower())
            if not 1<=len(words)<=9:continue
            if words and (words[0] in ("fcc","federal","national","commission")):continue
            normalized=" ".join(words[:3])
            if normalized not in NEGATIVE:
                hits.append({"cue":code,"generic_word_prefix":normalized,
                             "offset":m.start()})
            if len(hits)>=15: return hits
    return hits

def run():
    deep=json.loads((OUTPUT/"deep_full_document_evidence.json").read_text())
    target={r["filing_id"] for r in deep["records"] if r["status"]=="profession_not_evidenced"}
    verified=Counter(); counts=Counter(); leads=[]; phrases=Counter()
    manifest=json.loads((SOURCE/"manifest.json").read_text())
    seen=set()
    for shard in manifest["shards"]:
        with gzip.open(SOURCE/"shards"/shard["name"],"rt",encoding="utf8") as f:
            for line in f:
                if not line.strip():continue
                src=json.loads(line);fid=str(src["submission_id"])
                if fid not in target:continue
                seen.add(fid)
                file=MODEL_DIR/(fid+".json")
                model={}
                if file.exists():
                    model=json.loads(file.read_text())
                rawhash=hashlib.sha256(str(src.get("text","")).encode()).hexdigest()
                # Different pipelines sometimes hash source text differently:
                # disallow promotion of a model claim unless source evidence
                # is validated and the source hash exactly matches.
                validated=bool(model.get("source_evidence_verified"))
                hash_ok=bool(model.get("source_sha256")==rawhash)
                role=model.get("role") or ""
                counts["model_found" if model else "model_absent"]+=1
                if validated:counts["model_evidence_verified_flag"]+=1
                if hash_ok:counts["model_exact_text_hash_match"]+=1
                if validated and hash_ok and role not in ("","unresolved","unknown",
                                                          "named_person_capacity_unstated"):
                    verified[role]+=1
                    status="model_explicit_evidence_requires_review"
                elif role and role not in ("unresolved","unknown"):
                    counts["unvalidated_model_specific_role"]+=1
                    status="model_role_no_matching_source_verification"
                else:
                    status="no_model_identification"
                cues=cue_phrases(src.get("text",""))
                for x in cues:phrases[(x["cue"],x["generic_word_prefix"])]+=1
                leads.append({"filing_id":fid,
                              "source_url":"https://www.fcc.gov/ecfs/filing/"+fid,
                              "independent_model_role":role or None,
                              "model_verified_source_evidence":validated,
                              "model_matches_original_plaintext":hash_ok,
                              "status":status,
                              "author_phrase_leads":cues})
    assert seen==target, f"missing {len(target-seen)} original source records"
    # generic phrase inventory allows us to see overlooked role types
    freq=[{"cue":a,"start_words":b,"filings":n}
           for ((a,b),n) in phrases.most_common(140)]
    output={"schema":"unpublished-independent-adjudication-v1",
            "target":len(target),
            "independent_model_counts":dict(counts),
            "model_source_verified_specific_roles":dict(verified),
            "generalized_author_phrase_inventory":freq,
            "records":sorted(leads,key=lambda x:x["filing_id"])}
    (OUTPUT/"model_and_phrase_review.json").write_text(
        json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:output[k] for k in (
        "target","independent_model_counts","model_source_verified_specific_roles",
        "generalized_author_phrase_inventory")},indent=2)[:21000])
    return output
if __name__=="__main__":run()
