#!/usr/bin/env python3
"""Unseeded document-level topic discovery across ALL recovered FCC filing text.

Unlike build_argument_map's debate-sentence candidate selection, this scans the
complete extracted text of every readable document without filtering passages
through policy/advocacy term lists. It fits on balanced exact-text-distinct
documents to reduce template and prolific-filer domination, then scores every
filing. Topics are exploratory vocabularies, never validated positions.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "fcc_corpus"
OUTPUT = ROOT / "docs" / "data" / "open_topics.json"
STOP_EXTRA = set("""
    fcc commission commissioners federal communications commission's notice
    comment comments commented submitted submission docket e-rate erate rate
    rates program programs proposed proposal rulemaking pursuant paragraph
    pursuant hereby respectfully shall amended proceedings herein appendix
    page pages attachment attachments
""".split())
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n\s*\n")
SIMPLE = re.compile(r"[a-z][a-z-]{2,}", re.I)


def read_corpus(root: Path):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    rows = []
    count = 0
    readable = 0
    for spec in manifest["shards"]:
        path = root / "shards" / spec["name"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != spec["sha256"]:
            raise ValueError("Checksum mismatch: " + path.name)
        shard_count = 0
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                text = str(row.get("text") or "")
                checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if text and checksum != row.get("text_sha256"):
                    raise ValueError("Text checksum mismatch: " + str(row.get("submission_id")))
                rows.append({
                    "id": str(row["submission_id"]), "text": text,
                    "sha": checksum, "filer": str(row.get("filer_raw") or ""),
                    "date": str(row.get("date_submission") or ""),
                    "ocr": str(row.get("has_unreviewed_ocr", "0")) == "1"
                })
                count += 1
                shard_count += 1
                readable += bool(text.strip())
        if shard_count != spec["records"]:
            raise ValueError("Shard count mismatch " + path.name)
    if count != manifest["records"] or readable != manifest["records_with_text"]:
        raise ValueError("Source population mismatch")
    if len({x["id"] for x in rows}) != count:
        raise ValueError("Duplicate filing IDs")
    return manifest, rows


def select_fit_indices(rows, max_per_filer=9):
    """Every unique exact text gets at most one fit vote; cap same-filer fits.

    The source population is still fully scored and reported after fitting.
    """
    seen_text = set()
    filer_count = Counter()
    indices = []
    for i, row in enumerate(rows):
        if not row["text"].strip() or row["sha"] in seen_text:
            continue
        key = row["filer"].strip().lower()
        if key and filer_count[key] >= max_per_filer:
            continue
        indices.append(i)
        seen_text.add(row["sha"])
        if key:
            filer_count[key] += 1
    return indices


def extract_excerpt(text, terms):
    """Evidence quote must be a contiguous original-text substring."""
    if not text:
        return ""
    terms = {w for phrase in terms for w in SIMPLE.findall(str(phrase).lower())}
    best = None
    # Source text is already fully processed for vectorization; sample
    # sentence windows here only to choose illustrative, exact-span evidence.
    for candidate in SENTENCE_SPLIT.split(text[:60000]):
        s = candidate.strip()
        if not 70 <= len(s) <= 850:
            continue
        found = set(SIMPLE.findall(s.lower()))
        score = len(found.intersection(terms))
        if score < 2:
            continue
        if best is None or score > best[0]:
            best = (score, s)
    if best is None:
        return ""
    # Return an exact substring, not a space-normalized or invented quote.
    quote = best[1]
    return quote if quote in text else ""


def fit_model(rows, fit_indices, seed=1106, min_components=10, max_components=24):
    import numpy as np
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
    from sklearn.decomposition import NMF

    if len(fit_indices) < 15:
        raise ValueError("Insufficient independent readable texts to fit topics")
    stop = sorted(set(ENGLISH_STOP_WORDS) | STOP_EXTRA)
    vec = TfidfVectorizer(
        stop_words=stop, lowercase=True, strip_accents="unicode",
        max_features=9500, min_df=3, max_df=.8,
        ngram_range=(1, 2), sublinear_tf=True, norm="l2",
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z-]{2,}\b"
    )
    fit_text = [rows[i]["text"] for i in fit_indices]
    matrix = vec.fit_transform(fit_text)
    n = min(max_components, max(min_components, int(round(math.sqrt(len(fit_indices)) / 2.6))))
    n = min(n, matrix.shape[0] - 1, matrix.shape[1] - 1)
    if n < 2:
        raise ValueError("Not enough source vocabulary for clustering")
    model = NMF(n_components=n, init="nndsvda", random_state=seed, max_iter=160)
    model.fit(matrix)
    all_scores = []
    # Transform batches rather than constructing an unnecessary dense matrix.
    for start in range(0, len(rows), 90):
        batch = [row["text"] for row in rows[start:start+90]]
        all_scores.append(model.transform(vec.transform(batch)))
    score_matrix = np.vstack(all_scores)
    vocab = vec.get_feature_names_out()
    return model, vocab, score_matrix, n


def make_output(manifest, rows, fit_indices, model, terms, score_matrix, n_topics):
    family_sizes = Counter(row["sha"] for row in rows if row["text"].strip())
    topics = []
    total = len(rows)
    import numpy as np
    highest = np.max(score_matrix, axis=1)
    filer_names = [row["filer"].strip().lower() for row in rows]
    for topic_id in range(n_topics):
        ranked = np.argsort(model.components_[topic_id])[-14:][::-1]
        keywords = [str(terms[i]) for i in ranked]
        # Assignment is intentionally nonexclusive; it is a vector-weight
        # threshold rather than a count of literal phrase occurrences.
        membership = [i for i in range(total)
            if rows[i]["text"].strip() and highest[i] > 0
            and score_matrix[i,topic_id] >= .42 * highest[i]
            and score_matrix[i,topic_id] > 1e-8]
        if not membership:
            continue
        sorted_ids = sorted(membership, key=lambda i: -score_matrix[i,topic_id])
        top_filers = Counter(filer_names[i] for i in membership if filer_names[i])
        examples = []
        seen_text = set()
        seen_filer = Counter()
        for i in sorted_ids:
            row = rows[i]
            if row["sha"] in seen_text or (row["filer"] and seen_filer[row["filer"].lower()] >= 2):
                continue
            excerpt = extract_excerpt(row["text"], keywords[:10])
            if not excerpt:
                continue
            if excerpt not in row["text"]:
                raise ValueError("Source excerpt mismatch")
            examples.append({
                "id": row["id"], "date": row["date"], "filer": row["filer"],
                "ocr": row["ocr"], "quote": excerpt,
                "source_url": "https://www.fcc.gov/ecfs/filing/" + row["id"]
            })
            seen_text.add(row["sha"])
            seen_filer[row["filer"].lower()] += 1
            if len(examples) >= 10:
                break
        unique_texts = len({rows[i]["sha"] for i in membership})
        largest_name = max(top_filers.values(), default=0)
        topics.append({
            "id": "open_topic_" + str(topic_id+1),
            "top_terms": keywords,
            "working_label": ", ".join(keywords[:3]),
            "assigned_filings": len(membership),
            "unique_exact_texts": unique_texts,
            "filings_with_repeated_exact_text": sum(family_sizes[rows[i]["sha"]] > 1 for i in membership),
            "largest_filer_name_share": round(largest_name / len(membership), 4),
            "illustrative_quotes": examples,
            "scope_note": "Nonexclusive NMF component assignment, not stance or all possible discussion of a topic."
        })
    topics.sort(key=lambda x: -x["assigned_filings"])
    return {
        "schema_version": "open-document-topics-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_archive_sha256": manifest["source_archive_sha256"],
        "source_filings_scanned": len(rows),
        "readable_filings": sum(bool(r["text"].strip()) for r in rows),
        "fit_documents_after_exact_duplicate_and_filer_cap": len(fit_indices),
        "topics_count": len(topics),
        "method": {
            "approach": "Unseeded complete-text TF-IDF 1-2 gram + NMF",
            "fit_population": "One vote per exact-text hash and maximum 9 fit votes per normalized filer field",
            "all_filing_scoring": "Every filing transformed against the same topic model; nonexclusive topic membership at >=42% of its maximum topic score",
            "candidate_selection": "No preselected advocacy sentence filter or fixed regulatory keywords. All extracted text used for fitting/scoring.",
            "evidence": "Ten automatically chosen quotes per topic at most, contiguous in original extracted source; not representative.",
            "validity": "Topics describe lexical similarity, not independent stances, verified topic proportions or consensus."
        },
        "topics": topics
    }


def run(source=SOURCE, output=OUTPUT):
    manifest, rows = read_corpus(source)
    fit_indices = select_fit_indices(rows)
    model, terms, weights, n_topics = fit_model(rows, fit_indices)
    result = make_output(manifest, rows, fit_indices, model, terms, weights, n_topics)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temp.replace(output)
    return {key: result[key] for key in
            ("source_filings_scanned", "readable_filings",
             "fit_documents_after_exact_duplicate_and_filer_cap", "topics_count")}


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=SOURCE)
    p.add_argument("--out",type=Path,default=OUTPUT)
    opts=p.parse_args()
    print(json.dumps(run(opts.source, opts.out), indent=2))
