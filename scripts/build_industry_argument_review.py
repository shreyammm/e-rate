#!/usr/bin/env python3
"""Deterministic, source-linked industry ARGUMENT audit queue.

All known edtech/consultant candidates are a *review census*. Joint filing
metadata is screened without attributing the submission to every signatory.
Comparators include machine-positive and machine-negative controls to make
missed arguments visible. No result here is a human-verified position.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/data/stakeholder_argument_census.json"
OUTPUT = ROOT / "docs/data/industry_argument_review.csv"
SUMMARY = ROOT / "docs/data/industry_argument_review_summary.json"
SEED = "industry-argument-audit-v1-20261028"

# Keep each question conceptually narrow: presence, speaker, endorsement and
# requested policy action are four different human review judgments.
TOPICS = (
    "screen_harms", "screen_policy", "screen_use_distinctions",
    "learning_outcomes", "edtech_study_evidence", "adaptive_learning",
    "accessibility", "teacher_workload", "consultant_registration",
    "consultant_definition", "consultant_fees", "consultant_reporting",
    "consultant_independence", "consultant_value", "competitive_bidding",
    "consultant_firm_vs_individual", "consultant_percentage_fee_rules",
    "consultant_annual_training", "consultant_personal_data",
    "instructional_screen_exemptions",
    "alleged_misuse", "program_integrity", "program_continuity",
)
INDUSTRY = {
    "edtech_vendors", "edtech_trade_associations",
    "erate_consultants", "consultant_associations",
}
COMPARATORS = {
    "school_institutions", "school_professionals",
    "school_affiliation_uncertain", "libraries", "parents",
    "connectivity_and_network_vendors", "other_or_unidentified",
}
REVIEW_FIELDS = (
    "reviewer_id", "review_date", "verified_filer_category",
    "verified_represented_organization", "actual_speaker",
    "argument_present_in_complete_source", "filer_endorses_argument",
    "requested_fcc_action", "verified_fcc_provision_ids",
    "multiple_policy_options_explanation", "verified_argument_summary",
    "claimed_causal_mechanism", "cited_evidence_type",
    "factual_claim_independently_checked", "source_recheck_notes",
)
FIELDS = (
    "review_assignment", "sampling_stratum", "topic_id", "topic_name",
    "filing_id", "stakeholder_candidate", "specific_role_candidate",
    "organization_candidate", "joint_institutions_candidate",
    "model_candidate_status", "model_argument_unverified",
    "model_action_unverified", "redacted_source_quote",
    "quote_character_offset", "context_review_flags",
    "identity_review_required", "possible_representative",
    "source_text_read_scope", "ocr_candidate", "source_text_sha256",
    "source_url", "independent_review_required",
) + REVIEW_FIELDS


def sort_key(*parts: str) -> str:
    return hashlib.sha256((SEED + "|" + "|".join(map(str, parts))).encode()).hexdigest()


def machine_risk(f: dict, evidence: dict | None) -> bool:
    return bool(
        f.get("identity_review_required") or f.get("representative_possible")
        or f.get("joint_filing") or f.get("ocr_candidate")
        or f.get("quality_scope") != "full_text"
        or (evidence and evidence.get("needs_speaker_review"))
    )


def audit_row(f: dict, topic: dict, assignment: str, stratum: str) -> dict:
    hit = next((e for e in f.get("topics", []) if e.get("topic") == topic["id"]), None)
    row = {
        "review_assignment": assignment,
        "sampling_stratum": stratum,
        "topic_id": topic["id"],
        "topic_name": topic["label"],
        "filing_id": f["id"],
        "stakeholder_candidate": f["group"],
        "specific_role_candidate": f["role"],
        "organization_candidate": f.get("organization") or "",
        "joint_institutions_candidate": " | ".join(f.get("joint_institutions") or []),
        "model_candidate_status": "argument_extracted" if hit else "not_detected_by_model",
        "model_argument_unverified": (hit or {}).get("argument", ""),
        "model_action_unverified": (hit or {}).get("action", ""),
        "redacted_source_quote": (hit or {}).get("quote", ""),
        "quote_character_offset": (hit or {}).get("source_start", ""),
        "context_review_flags": " | ".join((hit or {}).get("context_flags") or []),
        "identity_review_required": bool(f.get("identity_review_required")),
        "possible_representative": bool(f.get("representative_possible")),
        "source_text_read_scope": f.get("quality_scope", "unknown"),
        "ocr_candidate": bool(f.get("ocr_candidate")),
        "source_text_sha256": f.get("text_sha256") or "",
        "source_url": "https://www.fcc.gov/ecfs/filing/" + str(f["id"]),
        "independent_review_required": "yes",
    }
    row.update({k: "" for k in REVIEW_FIELDS})
    return row


def verify_census(data: dict) -> None:
    filings = data["filings"]
    if data.get("schema") != "stakeholder-arguments-v1":
        raise ValueError("Unexpected census schema")
    if len(filings) != data["coverage"]["filings"] or len(filings) != 3231:
        raise ValueError("Incomplete source filing census")
    ids = [str(f["id"]) for f in filings]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate source filing ID")
    topic_ids = {t["id"] for t in data["topics"]}
    if not set(TOPICS).issubset(topic_ids):
        raise ValueError("Priority topics absent from census")
    roles = {g["id"]: g["filings"] for g in data["stakeholder_groups"]}
    if set(INDUSTRY | COMPARATORS | {"joint_institutional_filings"}) - set(roles):
        raise ValueError("Stakeholder group unavailable")
    if Counter(f["group"] for f in filings) != Counter(roles):
        raise ValueError("Published stakeholder denominators disagree with filing index")
    observed = defaultdict(lambda: defaultdict(set))
    for f in filings:
        for e in f.get("topics", []):
            if e["topic"] not in topic_ids:
                raise ValueError("Unknown argument topic in filing " + f["id"])
            if f["id"] in observed[e["topic"]][f["group"]]:
                raise ValueError("Duplicate filing/topic evidence " + f["id"])
            observed[e["topic"]][f["group"]].add(f["id"])
    for t in data["topics"]:
        n = 0
        for g, stats in t["by_stakeholder"].items():
            actual = len(observed[t["id"]][g])
            if actual != stats["filings"]:
                raise ValueError("Invalid filing count for " + t["id"] + " / " + g)
            n += actual
        if n != t["filings"]:
            raise ValueError("Invalid overall argument denominator " + t["id"])


def make_queue(data: dict, per_comparator_stratum: int = 3) -> tuple[list[dict], dict]:
    verify_census(data)
    if per_comparator_stratum < 1:
        raise ValueError("At least one comparator per stratum is required")
    topics = {x["id"]: x for x in data["topics"]}
    by_group = defaultdict(list)
    for f in data["filings"]:
        by_group[f["group"]].append(f)
    result = []
    population = []
    seen = set()

    def add(f: dict, topic_id: str, assignment: str, stratum: str) -> None:
        key = (f["id"], topic_id)
        if key in seen:
            raise ValueError("Duplicate review filing/topic assignment " + str(key))
        seen.add(key)
        result.append(audit_row(f, topics[topic_id], assignment, stratum))

    # Exhaust ALL known industry filing candidates plus ALL joint institutional
    # submissions as possible co-signer leads. A joint filing is not a separate
    # vendor or consultancy endorsement and is never reclassified as one.
    industry = [f for f in data["filings"]
                if f["group"] in INDUSTRY or f.get("joint_filing")]
    for f in sorted(industry, key=lambda x: str(x["id"])):
        scope = "industry_complete_census" if f["group"] in INDUSTRY else "joint_filing_screen_only"
        for topic_id in TOPICS:
            add(f, topic_id, scope, "all_in_group")

    for group in sorted(COMPARATORS):
        for topic_id in TOPICS:
            groups = defaultdict(list)
            for f in by_group[group]:
                hit = next((e for e in f.get("topics", []) if e.get("topic") == topic_id), None)
                status = "extracted" if hit else "not_detected"
                uncertainty = "risk" if machine_risk(f, hit) else "lower_risk"
                groups[(status, uncertainty)].append(f)
            for (status, uncertainty), pool in sorted(groups.items()):
                # Stratified pseudo-random sample of filing RECORDS, without
                # dropping duplicated/template text. Excluding duplicates
                # destroys known inclusion probabilities and can conceal
                # campaigns. Distinct-text sensitivity is reported separately.
                ordered = sorted(pool, key=lambda f: sort_key(group, topic_id, status, uncertainty, f["id"]))
                chosen = ordered[:per_comparator_stratum]
                population.append({
                    "group": group, "topic": topic_id,
                    "model_candidate_status": status, "risk_stratum": uncertainty,
                    "filing_population": len(pool),
                    "distinct_texts_in_population": len({x.get("text_sha256") or x["id"] for x in pool}),
                    "selected_filings": len(chosen),
                    "distinct_texts_selected": len({x.get("text_sha256") or x["id"] for x in chosen}),
                    "selection": "sha256_seeded_pseudorandom_filing_record_sample_without_replacement",
                    "sampling_fraction": round(len(chosen) / len(pool), 8) if pool else None,
                    "weight_after_adjudication": len(pool) / len(chosen) if chosen else None,
                    "reviewed_estimate_available": False,
                })
                for f in chosen:
                    add(f, topic_id, "comparator_quality_control",
                        status + "_" + uncertainty)

    result.sort(key=lambda r: (r["review_assignment"], r["stakeholder_candidate"],
                               r["topic_id"], r["sampling_stratum"], r["filing_id"]))
    counts = Counter(r["review_assignment"] for r in result)
    summary = {
        "schema": "industry-argument-review-queue-v1",
        "seed": SEED, "source_filings": len(data["filings"]),
        "priority_topics": list(TOPICS),
        "known_industry_and_joint_filings_in_census": len(industry),
        "industry_filings": sum(f["group"] in INDUSTRY for f in industry),
        "joint_filings_screened": sum(f.get("joint_filing") for f in industry),
        "assignments": len(result), "assignment_types": dict(counts),
        "unique_filings": len({r["filing_id"] for r in result}),
        "comparison_strata": population,
        "status": "UNREVIEWED_SOURCE_CHECK_ASSIGNMENTS",
        "interpretation": (
            "Machine extraction is a retrieval aid. A not-detected row is not a "
            "negative conclusion, and a detected row is not an endorsed stance. "
            "Review every industry candidate against the full original filing. "
            "Joint filings are separate screening leads, not attributed industry "
            "positions. Comparator strata use seeded pseudo-random sampling of "
            "filing records including repeated text, with N/n design weights. "
            "No accuracy, stance or prevalence estimates exist until independent "
            "source adjudication; filing counts never estimate public opinion."
        ),
    }
    return result, summary


def safe_csv_value(value) -> str:
    s = str(value if value is not None else "")
    # Prevent formula injection when a reviewer opens the CSV in Excel.
    return "'" + s if s.lstrip().startswith(("=", "+", "-", "@")) else s


def build(source=INPUT, destination=OUTPUT, summary_file=SUMMARY,
          per_comparator_stratum=3) -> dict:
    source = Path(source)
    data = json.loads(source.read_text(encoding="utf-8"))
    rows, summary = make_queue(data, per_comparator_stratum)
    summary["input_census_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: safe_csv_value(r.get(k, "")) for k in FIELDS})
    summary_file = Path(summary_file)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    return {k: summary[k] for k in (
        "source_filings", "industry_filings", "joint_filings_screened",
        "assignments", "assignment_types", "status")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--summary", type=Path, default=SUMMARY)
    parser.add_argument("--per-comparator-stratum", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(build(args.input, args.output, args.summary,
                           args.per_comparator_stratum), indent=2))


if __name__ == "__main__":
    main()
