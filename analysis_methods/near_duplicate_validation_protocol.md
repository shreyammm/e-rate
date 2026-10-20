# Repeated language and near-duplicate families

The October 20, 2026 topic-model comparison of 3,231 filings found 3,060 topic-eligible texts in the OCR-augmented view. The independently fitted baseline and augmented topic models retain 78% matched-topic assignments across 2,864 shared filings. This is **not** a validated theme/stance classification. Boilerplate and near-identical form letters may distort prevalence estimates.

## Run on the private, immutable research snapshot

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 -m scripts.snapshot_near_duplicate_families --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view augmented --threshold 0.87
```

The outputs are under `fcc_complete_corpus/analysis_observatory/research_snapshot_ocr_candidate_v1/templates_augmented/` and include candidate pairs, connected families, one row per family member with FCC source links, and a JSON methods report. They remain on the user's Mac and are not published or committed to GitHub.

**Method:** Five-word shingle hash sets; approximate 32-hash MinHash in eight four-hash LSH bands generates candidates, followed by observed shingle-Jaccard validation at the stated threshold. Candidate retrieval is not exhaustive. Family grouping is a connected component of candidate links, **not** a complete similarity clique. Two comments in one family may have different positions or be independently authored. Similarity alone is not evidence of coordination, astroturfing, or bad faith.

The source text and its SHA-256 normalization are checked against the immutable snapshot. Candidate OCR transcripts are labeled not human-verified. The code excludes provisional agency-record candidates and very short texts, so denominators are not the full 3,231. Name keys are normalized exact filer fields, not verified distinct people or organizations.

## Validation and final prevalence measures

1. Review the largest candidate families and at least a stratified sample of smaller families, following source links and comparing actual source passages.
2. Re-run sensitivity at thresholds 0.80, 0.87 and 0.95 on separate output paths or preserve each result before rerunning (the current script overwrites output inside a view). Record false positives and missed examples; thresholds cannot be directly interpreted as model accuracy.
3. Report counts by **filings**, **verified source-text units**, **candidate families**, and (once adjudicated) **distinct filer entities**. State a family represents shared language, not necessarily a shared policy stance.
4. Human-code positions *within* a family when comments have edited text, may take different positions on separate FCC proposals, or rely on quotations to argue against the quoted statement.
5. For public reporting, do not extrapolate a comment pool into population-level public opinion. These are self-selected ECFS filings.

## Findings and cautions from exploratory topics

Preliminary augmented lexical themes include broad E-Rate connectivity and school access (T12, 825 top assignments), public education/program modernization rhetoric (T01, 604), screen time and eligibility language (T03, 526), libraries and program cuts (T06/T07), as well as concentrated RFR/EMF and research citations (T02/T04/T10). These are only keyword-based names for human review. The topic matching has problematic splits: 1,071 baseline T03 filings split 602 to augmented T12 and 440 to augmented T03; the one-to-one match for baseline T11 to augmented T11 has zero shared filings and zero term overlap. Those pairs must **not** be described as equivalent themes.
