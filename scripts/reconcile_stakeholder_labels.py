#!/usr/bin/env python3
"""Compare source-grounded deterministic FCC speaker identities with model candidates.

This does NOT declare either system ground truth. Identity taxonomy is independent
of stance/arguments, and unknown is an abstention rather than a wrong sector.
Never publish personal names, original source paragraphs, or employment guesses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/data/player_registry.json"
QUALITY = ROOT / "docs/data/kaggle/filing_quality.json"
SECOND_PASS = ROOT / "data/identity_llm/filings"
OUTPUT = ROOT / "docs/data/stakeholder_label_audit.json"

OLD_LLM_ROLES = {
    "school_district", "school_staff", "advocacy_group", "library",
    "consultant", "parent_guardian", "individual_other", "researcher",
    "government", "unknown",
}
# These are mapping rules for COMPARISON only. They do not overwrite
# the detailed deterministic role or force the LLM to agree.
DET_TO_OLD = {
    "school_district": "school_district", "individual_school": "school_district",
    "school_technology_staff": "school_staff", "school_educator": "school_staff",
    "school_administrator": "school_staff", "school_connected_unknown": "unknown",
    "library_institution": "library", "library_staff": "library",
    "erate_consultant": "consultant", "procurement_adviser": "consultant",
    "trade_association": None,  # LLM has no trade-association label.
    "advocacy_organization": "advocacy_group",
    "parent_guardian": "parent_guardian", "student": "individual_other",
    "government": "government", "researcher": "researcher",
    "other_vendor": None,  # LLM has no vendor type at all.
    "named_person_capacity_unstated": "unknown", "unresolved": "unknown",
}
EDTECH_TYPES = {
    "edtech_learning_vendor", "edtech_digital_content_vendor",
    "edtech_virtual_school_vendor", "edtech_age_privacy_vendor",
    "edtech_safety_vendor", "edtech_device_vendor",
}
VENDOR_TYPES = EDTECH_TYPES | {"telecom_isp", "network_technology_vendor"}
MODEL_ROLES = set(DET_TO_OLD) | VENDOR_TYPES
INDUSTRY_TYPES = VENDOR_TYPES | {"erate_consultant", "procurement_adviser", "trade_association", "other_vendor"}

def old_category(role: str) -> str | None:
    if role in VENDOR_TYPES:
        return None
    if role not in DET_TO_OLD:
        raise ValueError("Unexpected deterministic role: " + role)
    return DET_TO_OLD[role]

def sector(role: str) -> str:
    if role in {"school_district", "school_staff"}:
        return "school"
    if role in {"library"}:
        return "library"
    if role in {"consultant"}:
        return "consultant"
    return role

def comparison(det: str | None, model: str) -> str:
    if det is None:
        return "unmapped_taxonomy"
    if det == "unknown" and model == "unknown":
        return "both_unknown"
    if det != "unknown" and model == "unknown":
        return "deterministic_specific_model_unknown"
    if det == "unknown" and model != "unknown":
        return "model_specific_deterministic_unknown"
    if det == model:
        return "same_specific_label"
    if sector(det) == sector(model):
        return "school_institution_vs_staff"
    return "cross_sector_conflict"

def priority(row: dict) -> int:
    status = row["comparison"]
    base = {
        "cross_sector_conflict": 100,
        "model_specific_deterministic_unknown": 82,
        "school_institution_vs_staff": 65,
        "deterministic_specific_model_unknown": 38,
        "unmapped_taxonomy": 32,
        "both_unknown": 12,
        "same_specific_label": 0,
    }[status]
    role = row["deterministic_role"]
    if role in INDUSTRY_TYPES and status != "same_specific_label":
        base += 25
    if row["proxy_possible"] or row["joint_institutional"]:
        base += 15
    if row["ocr_candidate"]:
        base += 8
    if row["identity_status"] != "human_reviewed" and row["needs_review"]:
        base += 5
    return min(150, base)

def validate_second_pass(path: Path, filing: dict) -> dict | None:
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    if str(d.get("submission_id")) != filing["id"]:
        raise ValueError("Second pass ID mismatch: " + filing["id"])
    if str(d.get("source_sha256")) != str(filing.get("text_sha256")):
        raise ValueError("Second pass source changed: " + filing["id"])
    role = str(d.get("role", "unresolved"))
    if role not in MODEL_ROLES:
        raise ValueError("Invalid second-pass role: " + role)
    return {
        "role": role,
        "basis": str(d.get("basis") or "unclear"),
        "source_evidence_verified": bool(d.get("source_evidence_verified")),
        "source_model": str(d.get("model") or "unknown"),
        "status": str(d.get("status") or "candidate"),
    }

def build(registry_path=REGISTRY, quality_path=QUALITY, second_pass=SECOND_PASS,
          output_path=OUTPUT) -> dict:
    reg_bytes = Path(registry_path).read_bytes()
    quality_bytes = Path(quality_path).read_bytes()
    reg = json.loads(reg_bytes)
    quality = json.loads(quality_bytes)
    filings = reg["filings"]
    qa = quality["filings"]
    ids = [str(f["id"]) for f in filings]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate registry filing ID")
    if not set(qa).issubset(set(ids)):
        raise ValueError("LLM quality has unknown filing IDs")
    counts = Counter()
    matrix = defaultdict(Counter)
    by_det = defaultdict(Counter)
    second_counts = Counter()
    rows = []
    for f in filings:
        fid = str(f["id"])
        if fid not in qa:
            counts["no_old_model_result"] += 1
            continue
        old = str(qa[fid].get("machine_inferred_role") or "unknown")
        if old not in OLD_LLM_ROLES:
            raise ValueError("Unrecognized old LLM label " + old)
        d = old_category(str(f["role"]))
        status = comparison(d, old)
        counts[status] += 1
        matrix[d if d is not None else "unmapped_taxonomy"][old] += 1
        by_det[str(f["role"])][status] += 1
        new = validate_second_pass(Path(second_pass) / (fid + ".json"), f)
        if new:
            second_counts["completed"] += 1
            if new["source_evidence_verified"]:
                second_counts["evidence_supported"] += 1
            if new["role"] == f["role"]:
                second_counts["agrees_detailed_role"] += 1
            elif new["role"] not in {"unresolved", "named_person_capacity_unstated"}:
                second_counts["proposes_different_role"] += 1
        row = {
            "id": fid,
            "deterministic_role": f["role"],
            "deterministic_comparison_role": d,
            "old_llm_role": old,
            "comparison": status,
            "organization": f.get("organization") or "", # public institution label only
            "classification_basis": f.get("basis") or "",
            "identity_status": f.get("identity_status") or "candidate",
            "needs_review": bool(f.get("needs_review")),
            "industry_focus": f.get("industry_focus") or "unspecified",
            "proxy_possible": bool(f.get("proxy_possible")),
            "joint_institutional": bool(f.get("multi_submitter_metadata")),
            "ocr_candidate": bool(f.get("ocr_candidate")),
            "source_url": f["source_url"],
        }
        if new:
            row["second_pass"] = new
            if (new["role"] != f["role"]
                and new["role"] not in {"unresolved", "named_person_capacity_unstated"}):
                row["second_pass_conflict"] = True
        row["priority"] = priority(row)
        rows.append(row)
    total = len(rows)
    both_specific = counts["same_specific_label"] + counts["school_institution_vs_staff"] + counts["cross_sector_conflict"]
    old_comparable = total - counts["unmapped_taxonomy"]
    assert total == len(qa)
    assert sum(counts[k] for k in (
        "same_specific_label", "school_institution_vs_staff", "cross_sector_conflict",
        "both_unknown", "deterministic_specific_model_unknown",
        "model_specific_deterministic_unknown", "unmapped_taxonomy")) == total
    # Full queue is published only with institutional names; no personal names
    # or source excerpts. A high-priority slice is also exposed for convenience.
    rows.sort(key=lambda r: (-r["priority"], r["id"]))
    result = {
        "schema_version": "stakeholder-identity-reconciliation-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "MACHINE_CANDIDATES_UNADJUDICATED",
        "inputs": {
            "registry_sha256": hashlib.sha256(reg_bytes).hexdigest(),
            "kaggle_quality_sha256": hashlib.sha256(quality_bytes).hexdigest(),
        },
        "coverage": {
            "filings_in_registry": len(ids),
            "filings_with_old_llm_labels": total,
            "filings_without_old_llm_labels": len(ids) - total,
            "old_llm_taxonomy_comparable": old_comparable,
            "old_llm_taxonomy_unmapped": counts["unmapped_taxonomy"],
            "both_specific_comparable": both_specific,
            "second_pass_completed": second_counts["completed"],
            "second_pass_pending": total - second_counts["completed"],
        },
        "summary": {
            "comparison_counts": dict(counts),
            "raw_disagreements_among_comparable": (
                counts["deterministic_specific_model_unknown"]
                + counts["model_specific_deterministic_unknown"]
                + counts["school_institution_vs_staff"]
                + counts["cross_sector_conflict"]
            ),
            "raw_disagreement_denominator": old_comparable,
            "cross_sector_conflict_both_specific": counts["cross_sector_conflict"],
            "cross_sector_conflict_denominator": both_specific,
            "second_pass": dict(second_counts),
            "human_adjudicated": reg["coverage"].get("manually_reviewed_filings", 0),
        },
        "confusion_matrix": {k: dict(v) for k,v in sorted(matrix.items())},
        "by_detailed_deterministic_role": {k:dict(v) for k,v in sorted(by_det.items())},
        "high_priority_review": [r for r in rows if r["priority"] >= 65][:650],
        "filings": rows,
        "limitations": [
            "Disagreement is not error rate; neither automated source is human ground truth.",
            "Unknown is an LLM abstention; compare denominators carefully.",
            "The old LLM could not express edtech, telecom, trade-association or other-vendor categories.",
            "School institution and employee labels refer to different capacities, not necessarily different sectors.",
            "Second-pass labels are supplementary machine candidates, never human-confirmed or silently promoted.",
            "Filer organizations, signatories, and represented clients must be distinguished before attribution.",
            "Personal submitter names and raw source passages are excluded from this report.",
        ],
    }
    output_path=Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry",type=Path,default=REGISTRY)
    parser.add_argument("--quality",type=Path,default=QUALITY)
    parser.add_argument("--second-pass",type=Path,default=SECOND_PASS)
    parser.add_argument("--out",type=Path,default=OUTPUT)
    args=parser.parse_args()
    data=build(args.registry,args.quality,args.second_pass,args.out)
    print(json.dumps({"coverage":data["coverage"],"summary":data["summary"]},indent=2))

if __name__ == "__main__":
    main()
