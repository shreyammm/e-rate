#!/usr/bin/env python3
"""Privately validate two independent coders' FCC industry argument reviews.

Input: two separately completed copies of the published review queue CSV.
Output: local (gitignored) quality report and disagreements, NOT public stance
statistics. Human agreement is necessary, not sufficient, for fact-checking.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from scripts.build_industry_argument_review import FIELDS, REVIEW_FIELDS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs/data/industry_argument_review.csv"
DEFAULT_OUTPUT = ROOT / "private_data/industry_review_qa"
PRESERVE_FIELDS = tuple(x for x in FIELDS if x not in REVIEW_FIELDS)
JUDGMENTS = (
    "actual_speaker", "argument_present_in_complete_source",
    "filer_endorses_argument", "requested_fcc_action",
)
OPTIONS = {
    "actual_speaker": {"filer", "third_party_reported", "fcc_question_or_quote", "unclear"},
    "argument_present_in_complete_source": {"yes", "no", "unclear"},
    "filer_endorses_argument": {"yes", "no", "unclear", "not_applicable"},
    "requested_fcc_action": {
        "support", "oppose", "amend_or_condition", "alternative",
        "discussion_no_position", "not_addressed", "unclear",
    },
}


def read_rows(path: Path) -> list[dict]:
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(FIELDS).issubset(reader.fieldnames):
            raise ValueError("Missing expected review columns in " + str(path))
        return list(reader)


def key(row: dict) -> tuple[str, str]:
    return str(row["filing_id"]), str(row["topic_id"])


def index_rows(rows: list[dict], name: str) -> dict:
    by = {}
    for row in rows:
        k = key(row)
        if k in by:
            raise ValueError("Duplicate filing/topic in " + name + ": " + str(k))
        by[k] = row
    return by


def validate_review_row(expected: dict, actual: dict, name: str) -> bool:
    for field in PRESERVE_FIELDS:
        if str(actual.get(field, "")) != str(expected.get(field, "")):
            raise ValueError(name + " edited source/assignment data at " +
                             str(key(expected)) + ": " + field)
    filled = any(str(actual.get(x, "")).strip() for x in REVIEW_FIELDS)
    if not filled:
        return False
    if not actual.get("reviewer_id", "").strip():
        raise ValueError(name + ": missing reviewer ID at " + str(key(expected)))
    for field, valid in OPTIONS.items():
        if actual.get(field, "").strip() not in valid:
            raise ValueError(name + ": missing/invalid " + field + " at " + str(key(expected)))
    present = actual["argument_present_in_complete_source"].strip()
    endorsed = actual["filer_endorses_argument"].strip()
    action = actual["requested_fcc_action"].strip()
    if present == "no" and (endorsed != "not_applicable" or action != "not_addressed"):
        raise ValueError(name + ": a confirmed absent argument cannot be endorsed " +
                         str(key(expected)))
    if present == "yes" and action == "not_addressed":
        raise ValueError(name + ": present argument marked as unaddressed " + str(key(expected)))
    if len(actual.get("source_recheck_notes", "").strip()) < 12:
        raise ValueError(name + ": describe the full-source check at " + str(key(expected)))
    return True


def analyze(queue: list[dict], first: list[dict], second: list[dict]) -> tuple[dict, list[dict]]:
    ground = index_rows(queue, "generated queue")
    a = index_rows(first, "first review")
    b = index_rows(second, "second review")
    if set(a) != set(ground) or set(b) != set(ground):
        raise ValueError("Both reviewer files must preserve ALL queue assignments")
    totals = Counter()
    per_group = defaultdict(Counter)
    disagreements = []
    for k, source in sorted(ground.items()):
        ra, rb = a[k], b[k]
        done_a = validate_review_row(source, ra, "first reviewer")
        done_b = validate_review_row(source, rb, "second reviewer")
        totals["assignments"] += 1
        if source["review_assignment"] == "industry_complete_census":
            totals["industry_assignments"] += 1
        if done_a: totals["first_completed"] += 1
        if done_b: totals["second_completed"] += 1
        if not (done_a and done_b):
            totals["awaiting_double_coding"] += 1
            continue
        if ra["reviewer_id"].strip().casefold() == rb["reviewer_id"].strip().casefold():
            raise ValueError("Two independent reviews must have different reviewer IDs " + str(k))
        totals["double_coded"] += 1
        diffs = [col for col in JUDGMENTS if ra[col] != rb[col]]
        if diffs:
            totals["judgment_disagreements"] += 1
            disagreements.append({
                "filing_id": k[0], "topic_id": k[1],
                "stakeholder_candidate": source["stakeholder_candidate"],
                "review_assignment": source["review_assignment"],
                "differing_fields": " | ".join(diffs),
                "first_judgments": json.dumps({col: ra[col] for col in JUDGMENTS}),
                "second_judgments": json.dumps({col: rb[col] for col in JUDGMENTS}),
                "source_url": source["source_url"],
            })
            continue
        totals["concordant_double_coded"] += 1
        group = source["stakeholder_candidate"]
        per_group[group]["concordant_reviewed"] += 1
        if ra["argument_present_in_complete_source"] == "unclear":
            totals["still_unclear"] += 1
        if ra["actual_speaker"] != "filer":
            totals["other_or_unclear_speaker"] += 1
        present = ra["argument_present_in_complete_source"] == "yes"
        machine = source["model_candidate_status"] == "argument_extracted"
        if present and not machine:
            totals["reviewed_machine_misses"] += 1
            per_group[group]["reviewed_machine_misses"] += 1
        elif machine and not present and ra["argument_present_in_complete_source"] == "no":
            totals["reviewed_machine_false_candidates"] += 1
            per_group[group]["reviewed_machine_false_candidates"] += 1
        if present and ra["actual_speaker"] == "filer" and ra["filer_endorses_argument"] == "yes":
            per_group[group]["concordant_endorsed_arguments"] += 1
    ready = totals["awaiting_double_coding"] == 0 and totals["judgment_disagreements"] == 0
    summary = {
        "status": "INTERNAL_REVIEW_ONLY_NOT_APPROVED_FOR_PUBLIC_STANCE_COUNTS",
        "method": "Two separately completed human full-source reviews; no automatic adjudication.",
        "counts": dict(totals),
        "group_review_observations": {k: dict(v) for k,v in sorted(per_group.items())},
        "all_assignments_double_coded_without_disagreement": ready,
        "claims_not_authorized": [
            "No general-public opinion percentages",
            "No extrapolation of reviewed samples to all comments without documented design weights and adjudication",
            "No named misconduct claim is verified by two people agreeing the filing said it",
            "A source-exact quote is not independent validation of the factual claim",
            "No claim of FCC-policy support from argument presence alone",
        ],
    }
    return summary, disagreements


def run(queue_path=DEFAULT_QUEUE, first=None, second=None, out=DEFAULT_OUTPUT) -> dict:
    if not first or not second:
        raise ValueError("Specify both independently coded reviewer CSV files")
    summary, issues = analyze(read_rows(Path(queue_path)),
                              read_rows(Path(first)), read_rows(Path(second)))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "quality_report.json").write_text(json.dumps(summary, indent=2) + "\n",
                                              encoding="utf-8")
    headers = ("filing_id", "topic_id", "stakeholder_candidate", "review_assignment",
               "differing_fields", "first_judgments", "second_judgments", "source_url")
    with (out / "disagreements.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(issues)
    return {"output": str(out), "status": summary["status"],
            "counts": summary["counts"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.queue, args.first, args.second, args.out), indent=2))


if __name__ == "__main__":
    main()
