# Versioned research-text snapshots

## Why this exists

Our audited corpus includes 3,231 indexed ECFS filings and 3,268 original document records. All 206 PDFs requiring recovery now have locally staged nonempty Apple Vision OCR (the initial 194 plus 12 further PDFs). Those candidate transcripts are **not equivalent to independently checked source text**. A robust analysis must be able to compare conclusions with and without OCR candidates and trace each included passage to its original FCC filing.

Run once per immutable version:

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 scripts/build_research_snapshot.py \
  --corpus ~/Downloads/fcc_complete_corpus \
  --run-id ocr_candidate_v1
```

Outputs stay locally at `~/Downloads/fcc_complete_corpus/analysis_observatory/research_snapshot_ocr_candidate_v1/`:

- `baseline_text/{submission_id}.txt`: ECFS direct text and the **non-OCR** existing attachment extraction.
- `ocr_augmented_text/{submission_id}.txt`: baseline plus staged, hash-verified OCR candidate text, without re-adding short/empty original extraction for the same attachment.
- `research_inventory.csv`: filing metadata, status, baseline/augmented text lengths, hashes, source links, and OCR inclusion flags.
- `source_segments.csv`: source-document and segment-level provenance including original SHA-256, transcript SHA-256, document ID, review status, and inclusion in each view.
- `snapshot_summary.json`: aggregate coverage and exact-duplicate figures **for each view separately**, manifest hashes and caveats.

Existing snapshots are never overwritten. Rerun with another `--run-id` after substantive corrections or an updated corpus. Original `filings_manifest.csv`, `documents_manifest.csv`, `combined_text`, originals and OCR evidence are never changed.

## Analysis rules

- An `ocr_candidate_not_human_verified` passage **may be explored** as provisional thematic material, but it must not be described as a validated transcript or used to publish definitive proposal support/opposition percentages.
- An OCR candidate replaces, **within the augmented analysis view only**, the same document's old short/placeholder extraction; it is not appended to it. This prevents duplicated source text and artificial template similarity.
- Each source segment has an original source link and source/transcript hashes. A file-hash mismatch or missing OCR evidence aborts the build instead of silently excluding text.
- Filings remain distinct records even if texts match. Normalized filer strings are not verified identities; the agency/type proxy is provisional and may exclude miscategorized public letters.
- Explicitly retain the known link-only filing `26110077815` in the metadata-only group. Do not invent a comment.
- Distinct content percentages depend on baseline versus augmented view and on how repeated filers and template families are counted; show sensitivity, not one universal percentage.
- These are self-selected public comments, not a representative poll. The source corpus is a **dated ECFS snapshot**, not a final docket population.
- The research snapshot contains filer names and potentially sensitive extracted text; keep the entire output directory on your Mac and **do not commit to the public repository**.

## Research next gates

1. Verify a documented sample of OCR transcripts against original pages, including high-risk negations/numbers and the four documents with empty OCR pages; preserve the review CSV separately.
2. Confirm that the snapshot contains 3,231 filings and that exactly one or another documented number remains metadata-only. Do not assume the count in advance; compare local output.
3. Identify agency-origin documents by provenance, not submission type alone.
4. Stratify and review a human-coded gold sample for stakeholder identity, FCC issue-specific positions and rationale; record **verbatim supporting evidence**.
5. Use exploratory topic models to discover repeated language before naming policy narratives, and report template/repeated-filer sensitivity. Build a publication-quality dashboard only after validation.
