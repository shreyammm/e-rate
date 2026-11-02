#!/usr/bin/env python3
"""Find cross-filing occupational role leads without treating name matches as proof.

The public output contains only FCC filing IDs and role category candidates.
No original submitter names, email addresses, or extracted text are republished.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from scripts.build_player_registry import ROOT
from scripts.identity_metadata_resolver import personal_name_format

REGISTRY = ROOT / "docs/data/player_registry.json"
CORPUS = ROOT / "data/fcc_corpus"
OUTPUT = ROOT / "docs/data/cross_filing_identity_leads.json"

STRONG_BASES = {
    "author_self_description",
    "signed_role",
    "signed_role_and_organization",
    "terminal_signature_job_title",
}
PROFESSIONS = {
    "school_technology_staff", "school_administrator", "school_educator",
    "library_staff", "library_affiliated", "school_connected_unknown",
    "erate_consultant", "procurement_adviser", "researcher", "government",
    "parent_guardian", "student",
}


def personal_key(raw: str) -> str:
    """Compare conservative exact personal-name forms, not fuzzy names."""
    raw = " ".join(str(raw or "").split())
    if not personal_name_format(raw) or len(raw.split()) < 2:
        return ""
    return raw.casefold()


def audit(registry=REGISTRY, source=CORPUS, output=OUTPUT) -> dict:
    rows = json.loads(Path(registry).read_text(encoding="utf8"))["filings"]
    byid = {str(x["id"]):x for x in rows}
    names = defaultdict(list)
    manifest = json.loads((Path(source)/"manifest.json").read_text(encoding="utf8"))
    for shard in manifest["shards"]:
        path = Path(source)/"shards"/shard["name"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != shard["sha256"]:
            raise ValueError("Source shard hash mismatch " + shard["name"])
        with gzip.open(path, "rt", encoding="utf8") as stream:
            for line in stream:
                if not line.strip():continue
                r = json.loads(line)
                fid = str(r["submission_id"])
                if fid not in byid:raise ValueError("Foreign filing ID "+fid)
                name = personal_key(r.get("filer_raw",""))
                if name:
                    names[name].append(fid)

    leads = []
    for _,ids in names.items():
        if len(ids) < 2:continue
        supporting = [
            byid[i] for i in ids
            if byid[i].get("basis") in STRONG_BASES
            and byid[i].get("role") in PROFESSIONS
            and byid[i].get("identity_confidence") in ("high","medium")
        ]
        roles = {r["role"] for r in supporting}
        if len(roles) != 1:continue
        role = next(iter(roles))
        for fid in ids:
            target = byid[fid]
            if target.get("identity_status") != "capacity_not_stated":
                continue
            proofs = [r for r in supporting if r["id"] != fid
                      and r.get("text_sha256") != target.get("text_sha256")]
            if not proofs:continue
            leads.append({
                "id": fid,
                "source_url": target["source_url"],
                "role_candidate": role,
                "evidence_kind": "same_exact_normalized_personal_name_other_filing",
                "corroborating_filing_ids": sorted(x["id"] for x in proofs),
                "confidence": "unconfirmed_name_match",
                "automatic_reclassification": False,
                "reason": "The same FCC filer-name string described this role in another filing. This does not establish a unique person, current occupation, or authority on this submission.",
            })
    leads.sort(key=lambda x:x["id"])
    result = {
        "schema":"cross-filing-identity-leads-v1",
        "source_filings":len(rows),
        "distinct_personal_name_strings":len(names),
        "person_name_strings_with_multiple_filings":sum(len(x)>1 for x in names.values()),
        "capacity_unstated_targets":sum(x.get("identity_status")=="capacity_not_stated" for x in rows),
        "potential_cross_filing_leads":len(leads),
        "role_lead_counts":dict(Counter(x["role_candidate"] for x in leads)),
        "limitations":"Same-name links are provisional; no unverified role is automatically applied to the stakeholder census. The person's different submissions may be in different capacities.",
        "records":leads,
    }
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return result


if __name__=="__main__":
    d=audit()
    print("Cross-filing candidates:",d["potential_cross_filing_leads"])
    print("Capacity-unstated:",d["capacity_unstated_targets"])
