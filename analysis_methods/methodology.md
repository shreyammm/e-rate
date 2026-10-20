# Methods and research protocol — FCC E-Rate Comment Observatory

**Status: version 0.1.0; descriptive/quality-control analysis implemented, issue coding not yet validated.**

## Source and scope

The source is the FCC ECFS record for WC Dockets 26-133, 13-184, 21-93, 21-455, particularly the June 26, 2026 NPRM/FNPRM, **FCC 26-41**. Filing metadata and text were collected through ECFS and original attachments; analyses operate on the local audited snapshot. The October 13, 2026 initial-comment deadline has passed, but **reply comments run through November 12, 2026**. This snapshot is not necessarily the entire future docket or an all-time census. Report the retrieval cutoff and ECFS query predicates before making completeness claims.

Primary sources:

- [FCC 26-41 full notice](https://docs.fcc.gov/public/attachments/FCC-26-41A1.pdf)
- [Federal Register 91 FR 52626](https://www.govinfo.gov/content/pkg/FR-2026-08-14/pdf/2026-16590.pdf)
- [Comment and reply deadlines — DA-26-865](https://docs.fcc.gov/public/attachments/DA-26-865A1.pdf)

## Unit of analysis

1. **Filing** = one ECFS submission ID (including non-comment FCC documents). All IDs preserved, even if identical texts or a link-only attachment.
2. **Attachment** = one `(submission_id, document_number)` tuple. One filing may contain multiple documents.
3. **Raw filer field** = what ECFS reports, possibly a composite name and organization; not equivalent to a verified person.
4. **Filer key** = casefolded/Unicode-normalized complete filer string, without fuzzy identity merging. A person who files as “Jane Doe” and “Jane Doe | District” may be counted twice. Two people with exactly the same name may be merged. We report this explicitly as an **approximation** and plan adjudicated entity resolution.
5. **Unique text** = Unicode NFKC, casefolded, collapsed-whitespace exact SHA-256; not the same as a unique opinion.
6. **Near-duplicate candidate** = 5-word-shingle MinHash LSH candidate with verified Jaccard above configurable threshold. Non-exhaustive, with uncertainty and no claim of coordination unless separately verified.
7. **Policy position** = one stance on one issue, not general positive/negative sentiment. A filer may hold opposing positions on distinct provisions.
8. **Argument** = one evidence-supported reason or causal claim. A single filing may invoke several argument families.

## Source provenance, privacy, and collection integrity

Store original attachments, retrieval URL, FCC ID, SHA-256 hash and extracted text separately; never silently overwrite raw originals. Report absent/unreadable attachments and the link-only filing (`26110077815`). Report the collection cutoff, extraction tools and version, OCR attempts, and whether scans were human-checked. Generated local filing/filer tables may include personally identifying metadata, so **do not commit them to the public GitHub repository** by default. The repository distributes code and methods, not a mass republication of personally identifiable metadata.

Collection status `complete` is **not** evidence that scanned PDFs were successfully read. The quality gate flags any PDF with ≤100 extracted characters, empty text, placeholder strings, broken original hashes, missing files, or text/metadata length mismatches. Inspect flagged PDFs visually and perform OCR on confirmed scans. Save corrected text as a separate version, record page coverage/confidence and document hashes; do not change summary measures until reconciliation. The PDF-QC queue can be generated with `python3 -m scripts.ocr_triage` (or `python3 scripts/ocr_triage.py`).

## Descriptive analytics that can currently be computed

- Submission counts over time and by ECFS type.
- Exact-normalized filer submission counts, top 1/5/10% share and repeated participation.
- Exact duplicate-text clusters without removing filing records.
- Distribution of text lengths and documents requiring manual/OCR review.
- Optional near-duplicate candidate pairs (requires human labeling before calling them template campaigns).

**Do not report yet:** proportions favoring a proposal, stakeholder group contrasts, topic maps, or campaign coordination as established findings. These need validated coding and complete text.

## Policy taxonomy and positions: review before use

`issue_taxonomy.json` lists broad **provisional** issue families anchored to the FCC NPRM/FNPRM. Before coding, read the full primary source and split these families into operationally specific proposals, quote numbered FCC paragraphs for each definition, define positive/negative directions consistently, and note when the FCC merely seeks comment rather than makes a concrete proposal.

Allowed position values: `support`, `oppose`, `mixed_or_conditional`, `descriptive_only`, `unclear`, `not_addressed`. Every affirmative classification needs a **verbatim evidence quote** that appears in the source text and a coder ID, method and confidence. 'Not addressed' and 'unclear' are different. Mentioning a keyword or belonging to an advocacy group is not sufficient evidence of support/opposition. Non-comments (FCC notices, NPRMs) should not be classified as positions from the public.

Stakeholder types for **evidenced self-identification**: parent/guardian, student, teacher/staff, school/district, library, industry/vendor, consultant, advocacy nonprofit, government agency, elected official, other individual, other organization, and unknown. An “as a parent” sentence does not prove the filer submitted in an official organizational capacity. Code the role **in which they participate**, with uncertainty and multiple roles where needed.

## Two-stage annotation and validation plan

1. Run the quality gate and correct PDFs with little or missing text before position inference.
2. Select a **stratified pilot** of at least 120 readable filings, including duplicates and long submissions, and manually code all relevant issues, plus random negatives. The script generates a deterministic starter sample; its strata are convenience categories, not a population-weighted sample.
3. Have two independent coders label a common subset (e.g., 50 filings), blind to model suggestions. Calculate per-issue inter-coder agreement and investigate disagreements; adjudicate into a separate gold-standard table. Correct evidence offsets and ambiguity rules.
4. If LLM-assisted classification is used, store model version, prompt checksum, output schema, generation date and settings. Retain an unmodified raw model response, structured label, confidence, exact evidence passage, and reason for abstention. Inspect all invalid quotes and uncertain cases.
5. Validate on **held-out filings and held-out template families**, so copies of the same campaign template cannot inflate accuracy. Report per-issue precision, recall, F1, coverage, and confusion between `not_addressed` and `unclear`, plus performance by length, PDF/OCR quality, source type and stakeholder group. No percentage is published without denominators and validation notes.
6. Use separate **filing-weighted**, **filer-key-weighted** and **unique-text-weighted** tables; show sensitivity to repeated prolific filers and identical campaigns. Do not call these statistically representative public opinion.
7. Human review of edge cases: filings with multiple positions, indirect language, citations to others' positions, sarcasm, long appendices, and arguments about unrelated dockets.

## Interpreting temporal trends and organized comments

Do not assume that repeated text proves deceptive activity. Compare exact-copy families with near-duplicate templates, identify public campaign links when documented, and separately describe distinct filer counts and the share of comments using a template. All template assignments remain candidate labels until reviewed. Cross-docket filings and multiple attachments must not double-count one submission.

## Reproducibility and publication

Report the corpus SHA manifest, `summary.json`, date/version of extraction, analysis source revision, taxonomy version, model/prompt version if any, annotation sampling seed and full validation tables. Publish code and aggregate charts; reconsider publishing raw filer names, text and contact information at scale. Provide original FCC hyperlinks for drill-down. User-facing charts must label their unit and denominator. **No causal or representative-population inference from self-selected comments.**
