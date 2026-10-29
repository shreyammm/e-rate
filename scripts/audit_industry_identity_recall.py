#!/usr/bin/env python3
"""Look for industry speakers missed by the provisional FCC player registry.

Source-linked RECALL leads only: no automatic reclassification, no transfer of
a joint filing to its signatories, and no attribution from mere issue mentions.
Source corpus hashes are checked. The public output contains no raw filer names,
personal signatures, email/phone fields, or scraped source excerpts.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/fcc_corpus"
REGISTRY = ROOT / "docs/data/player_registry.json"
DEST = ROOT / "docs/data/industry_identity_recall.json"

INDUSTRY_ROLES = {
    "erate_consultant", "procurement_adviser", "trade_association",
    "edtech_learning_vendor", "edtech_digital_content_vendor",
    "edtech_virtual_school_vendor", "edtech_age_privacy_vendor",
    "edtech_safety_vendor", "edtech_device_vendor",
    "telecom_isp", "network_technology_vendor",
}
# Do not describe *all* trade associations as edtech or consultant groups.
KNOWN_INDUSTRY_GROUPS = {
    "erate_consultant", "procurement_adviser",
    "edtech_learning_vendor", "edtech_digital_content_vendor",
    "edtech_virtual_school_vendor", "edtech_age_privacy_vendor",
    "edtech_safety_vendor", "edtech_device_vendor",
}
# These patterns indicate why a human should inspect an *institution-valued
# submitter label*. They are not sector classification rules.
ORG_SIGNALS = {
    "named_erate_service_or_consultancy": re.compile(
        r"\b(?:e[\s-]?rate|universal service)\b.{0,40}"
        r"\b(?:consult|advis|management|service|solution|funding)|"
        r"\b(?:consult|advis|management)\b.{0,35}\be[\s-]?rate\b", re.I),
    "named_education_software_or_content": re.compile(
        r"\b(?:ed[\s-]?tech|education(?:al)? (?:software|technolog|platform|app)|"
        r"(?:learning|instructional|classroom) (?:software|platform|technolog)|"
        r"(?:digital|online) (?:learning|curriculum|instruction)|"
        r"student (?:safety|monitoring|privacy) (?:software|platform))\b", re.I),
    "named_generic_consulting_firm": re.compile(
        r"\b(?:consult(?:ing|ants?)|advis(?:ory|ers?)|grant management)\b", re.I),
    "named_technology_or_network_business": re.compile(
        r"\b(?:technology|technologies|software|networking|telecom|"
        r"broadband|internet|communications|digital solutions)\b", re.I),
}
# Reading the first-person filing introduction is less error-prone than
# finding words like "consultant" in the FCC questions the filing quotes.
INTRO_SIGNALS = {
    "first_person_erate_consultant": re.compile(
        r"\b(?:i am|i'm|we are|our firm is|our company is|"
        r"i serve as|i work as|my firm is)\s+(?:an?\s+|the\s+)?"
        r"(?:independent\s+)?e[\s-]?rate\s+(?:consultant|advisor|adviser|consulting firm)\b", re.I),
    "first_person_edtech_business": re.compile(
        r"\b(?:we are|our company is|our firm is|i represent)\s+"
        r"(?:an?\s+|the\s+)?(?:education(?:al)? technology|ed[\s-]?tech|"
        r"education software|instructional software|digital learning)"
        r"(?:\s+(?:company|vendor|provider|business|developer))?\b", re.I),
    "first_person_erate_advisory_service": re.compile(
        r"\b(?:we|our firm|our company)\s+(?:provide|provides|speciali[sz]e in|"
        r"assist schools with|support districts with)\s+.{0,75}"
        r"\be[\s-]?rate\s+(?:consulting|advisory|application|compliance)\b", re.I),
}
NONINDUSTRY = {"school_district", "individual_school", "school_technology_staff",
               "school_educator", "school_administrator", "library_institution",
               "library_staff", "government", "parent_guardian", "student"}
SAFE_COMPANY = re.compile(r"\b(?:inc\.?|llc|ltd\.?|corporation|corp\.?|company|"
                          r"technologies|software|consulting|consultants?|services)\b", re.I)


def source_leads(row: dict, text: str) -> list[str]:
    """Strict false-negative leads, never a category assignment."""
    role = str(row.get("role") or "")
    org = str(row.get("organization") or "")
    signals = []
    # Only metadata names previously vetted for institutional display.
    if org:
        for label, pattern in ORG_SIGNALS.items():
            if pattern.search(org):
                # "District Technology Services" is not commercial evidence.
                if role in NONINDUSTRY and label in {
                    "named_generic_consulting_firm", "named_technology_or_network_business"
                }:
                    continue
                # Vague institutional "School Technology" isn't an edtech vendor.
                signals.append("metadata_" + label)
    # Intro should be attributable first-person statement, not FCC proposal,
    # bibliography, or a last-page signatory unrelated to the filer.
    intro = str(text or "")[:1600]
    intro = re.split(r"(?im)^\s*(?:references|works cited|bibliography|appendix)\s*:?\s*$",
                     intro, maxsplit=1)[0]
    for label, pattern in INTRO_SIGNALS.items():
        if pattern.search(intro):
            signals.append("author_intro_" + label)
    if row.get("proxy_possible"):
        signals.append("possible_proxy_or_client_relationship")
    if row.get("multi_submitter_metadata"):
        signals.append("joint_institutional_metadata")
    return sorted(set(signals))


def rank_lead(row: dict, signals: list[str]) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    if any(s.startswith("author_intro_first_person_") for s in signals):
        score += 55
        reasons.append("explicit_first_person_industry_capacity")
    if "metadata_named_erate_service_or_consultancy" in signals:
        score += 45
        reasons.append("industry_specific_institution_label")
    if "metadata_named_education_software_or_content" in signals:
        score += 45
        reasons.append("industry_specific_institution_label")
    if "metadata_named_generic_consulting_firm" in signals:
        score += 15
        reasons.append("generic_consulting_name_ambiguous")
    if "metadata_named_technology_or_network_business" in signals:
        score += 10
        reasons.append("technology_name_not_specific_to_edtech")
    if "possible_proxy_or_client_relationship" in signals:
        score += 12
        reasons.append("representation_requires_inspection")
    if "joint_institutional_metadata" in signals:
        score += 12
        reasons.append("joint_party_requires_separate_attribution")
    if row.get("needs_review"):
        score += 8
        reasons.append("registry_identity_uncertain")
    if row.get("role") in NONINDUSTRY and not any(
        s.startswith("author_intro_first_person_") for s in signals
    ):
        # A school's IT department or librarian is not a commercial vendor.
        score = min(score, 15)
        reasons.append("existing_school_library_public_capacity")
    return min(100, score), reasons


def build(source=SOURCE, registry=REGISTRY, output=DEST) -> dict:
    source = Path(source)
    registry = Path(registry)
    data = json.loads(registry.read_text(encoding="utf-8"))
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("records") != 3231 or len(data.get("filings", [])) != 3231:
        raise ValueError("Source coverage does not match registry")
    by_id = {str(r["id"]): r for r in data["filings"]}
    if len(by_id) != 3231:
        raise ValueError("Duplicate registry filing IDs")
    seen = set()
    leads = []
    relationship_leads = []
    counts = Counter()
    for shard in manifest["shards"]:
        filename = source / "shards" / shard["name"]
        if hashlib.sha256(filename.read_bytes()).hexdigest() != shard["sha256"]:
            raise ValueError("Untrusted source shard checksum: " + shard["name"])
        with gzip.open(filename, "rt", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                sid = str(item["submission_id"])
                if sid in seen or sid not in by_id:
                    raise ValueError("Duplicate/missing source ID " + sid)
                seen.add(sid)
                body = str(item.get("text") or "")
                if hashlib.sha256(body.encode()).hexdigest() != item.get("text_sha256"):
                    if body or item.get("text_sha256"):
                        raise ValueError("Source text hash mismatch " + sid)
                r = by_id[sid]
                raw_signals = source_leads(r, body)
                # Industry records are already in the player inventory. Do not
                # call them *missed*, but retain their counts as audit context.
                known = r.get("role") in KNOWN_INDUSTRY_GROUPS or (
                    r.get("role") == "trade_association"
                    and r.get("industry_focus") in {"edtech_industry", "erate_consulting"})
                if known:
                    counts["currently_industry_coded"] += 1
                elif raw_signals:
                    score, reasons = rank_lead(r, raw_signals)
                    # A generic "on behalf of" is a relationship-audit signal,
                    # NEVER a credible indication of being an industry filer.
                    industry_signals = [s for s in raw_signals
                        if s.startswith("metadata_named_") or s.startswith("author_intro_first_person_")]
                    if industry_signals and score >= 20:
                        leads.append({
                            "id": sid, "role_candidate": r.get("role", ""),
                            "organization_candidate": r.get("organization", ""),
                            "industry_focus_candidate": r.get("industry_focus", ""),
                            "identity_status": r.get("identity_status", ""),
                            "needs_identity_review": bool(r.get("needs_review")),
                            "source_cues_not_conclusions": raw_signals,
                            "review_priority_score": score,
                            "review_reasons": reasons,
                            "joint_filing": bool(r.get("multi_submitter_metadata")),
                            "source_url": "https://www.fcc.gov/ecfs/filing/" + sid,
                        })
                        counts["possible_missed_industry_leads"] += 1
                    if "possible_proxy_or_client_relationship" in raw_signals or "joint_institutional_metadata" in raw_signals:
                        relationship_leads.append({
                            "id": sid, "role_candidate": r.get("role", ""),
                            "organization_candidate": r.get("organization", ""),
                            "representation_uncertain": "possible_proxy_or_client_relationship" in raw_signals,
                            "joint_institutional_metadata": "joint_institutional_metadata" in raw_signals,
                            "source_url": "https://www.fcc.gov/ecfs/filing/" + sid,
                        })
                        counts["separate_relationship_review_leads"] += 1
                if r.get("multi_submitter_metadata"):
                    counts["joint_institutional_filings"] += 1
    if seen != set(by_id) or len(seen) != manifest["records"]:
        raise ValueError("Incomplete source scan")
    leads.sort(key=lambda x: (-x["review_priority_score"], x["id"]))
    relationship_leads.sort(key=lambda x: x["id"])
    result = {
        "schema": "industry-identity-recall-leads-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "registry_sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
        "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "coverage": {"checked_filing_records": len(seen), **counts},
        "status": "UNREVIEWED_INDUSTRY_CANDIDATES",
        "method": ("Only public institution-valued registry labels and attributable"
                   " first-person introductions are screened. A proxy or joint"
                   " filing is never credited to a client or co-signer by default."),
        "limitations": [
            "Review leads are not confirmed companies or consultant employers.",
            "A name mentioning technology may identify an applicant school or nonprofit; review the original FCC source.",
            "Absence from the lead queue is not proof that no other industry source exists.",
            "First-person excerpts may still contain attributed or quoted language.",
            "Representation-only or joint-party cues are segregated from industry candidates.",
            "No raw individual submitter names, email addresses, phone numbers or source paragraphs are republished.",
        ],
        "leads": leads,
        "relationship_leads_not_industry_candidates": relationship_leads,
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":"))+"\n", encoding="utf-8")
    return {"coverage": result["coverage"], "lead_count": len(leads),
            "relationship_lead_count": len(relationship_leads), "output": str(output)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=SOURCE)
    p.add_argument("--registry", type=Path, default=REGISTRY)
    p.add_argument("--output", type=Path, default=DEST)
    a = p.parse_args()
    print(json.dumps(build(a.source, a.registry, a.output), indent=2))


if __name__ == "__main__":
    main()
