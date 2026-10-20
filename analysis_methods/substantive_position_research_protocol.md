# Substantive policy-position and argument analysis — FCC 26-41

**Status:** research protocol and draft codebook, not a completed study. No percentages supporting or opposing proposed rules are validated yet. This workflow runs on the October 20, 2026 local research snapshot and retains individual source evidence on the user's Mac.

## Core research questions

1. **Requested outcome:** For each specific FCC option, do commenters want the FCC to adopt it, reject it, narrow it, amend it, expand it, substitute another rule, or refrain from acting? Record the action using original language.
2. **Reasons and mechanisms:** What consequences do they predict—costs, broadband access, classroom learning, student safety, parent choice, censorship/privacy, legal authority, consultant misconduct, procurement burdens—and *why*?
3. **Alternatives and implementation:** Are commenters asking for a different threshold, exemption, definition, timetable, federal versus local discretion, conditional rule, or stakeholder consultation?
4. **Evidence and uncertainty:** Do they cite surveys, studies, statutes, local budgets, experiences, provider contracts, anecdotes or unsupported claims? Distinguish evidence mentioned from independently validated evidence.
5. **Who advocates each change?** Identify the role in which a filer submitted (school/district, library, telecom carrier, parent, vendor, consultant, NGO, etc.) and whether they speak officially for that organization, as an individual, or ambiguously.
6. **Independent viewpoints versus repeated text:** Describe results by filings, source-distinct texts, near-duplicate candidate families, and adjudicated distinct filer entities. A letter with many signatures is not necessarily many independent submissions.
7. **Disagreements:** Highlight counterarguments within each issue, areas of conditional support, legal disagreements, and claims requiring outside verification. Never infer support from a generic positive/negative tone.

## Source authority and paragraph specificity

Primary notice: https://docs.fcc.gov/public/attachments/FCC-26-41A1.pdf

`provision_codebook_v1.json` is a **draft taxonomy** of 29 individually actionable questions/changes across the FCC 26-41 NPRM/FNPRM. The section/paragraph groups are broad navigational ranges, NOT yet verified exact paragraphs for each option. Some are explicit regulatory proposals and others merely ask for comment. Before publishing, review each entry against the full PDF, quote the *exact paragraph* and distinguish proposed text from questions, background and historical policy.

## Research workflow

1. **Keep original evidence and provenance.** Use the immutable `research_snapshot_ocr_candidate_v1`; source segments distinguish direct ECFS text, historical extraction and candidate OCR. The known link-only record remains metadata-only. Coding is on substantive source text, not filename or filer identity.
2. **Retrieve evidence candidates without classifying them.** Run `python3 -m scripts.prepare_policy_analysis --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view augmented`. This creates locally stored source-exact excerpts, the FCC filing link, matching policy option and a *generated, editable-looking but disposable* review queue. Terms indicate retrieval, not stance.
3. **Review relevant and keyword-negative cases.** Run `python3 -m scripts.build_policy_review_packet --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1`. Open the generated offline HTML file; review text against linked originals, choose a position, type what action the filer asks for, give the reason, select reason/stakeholder classes, paste one exact supporting quote, and export a reviewer CSV. Negative controls are important: otherwise claims without the codebook's keywords could be missed.
4. **Validate before counting.** Run `python3 -m scripts.validate_position_annotations --corpus ~/Downloads/fcc_complete_corpus --annotations ~/Downloads/fcc_policy_human_reviews.csv --snapshot-id ocr_candidate_v1 --view augmented`. The validator rejects nonmanual labels, unknown provisions, duplicate filing/provision pairs, missing actions/reasons, and quotes that do not occur exactly once in the source text. Review error CSVs; do not automatically convert missing keyword matches into `not_addressed`.
5. **Investigate generalizability.** The pilot is deliberately diverse, NOT probability-weighted. Use a separate random sample to estimate false negatives and per-provision error rates, ideally two blind coders on overlapping records. Compare full-text review, keyword hits and human codings; adjudicate disagreements and preserve all annotations.
6. **Export a conservative site preview.** Run `python3 -m scripts.export_public_site_data --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view augmented`. This writes a private preview JSON to the local snapshot, not GitHub. Explicit `--publish-reviewed` is required to write a public file into `docs/data`, and publication requires a privacy and codebook review.

## Position labels and operational definitions

- `support`: explicitly advocates adopting the particular option as directionally specified in the codebook.
- `oppose`: explicitly argues against that particular option.
- `conditional_or_amend`: favors the option only under stated conditions or with specific amendments; describe them.
- `alternative_proposal`: proposes a different regulatory approach to the same question; do not count automatically as either yes or no.
- `discussion_no_position`: substantively discusses effects without saying what the FCC should decide.
- `unclear`: excerpt, OCR quality, ambiguity or contradictory passages prevent a defensible position.
- `not_addressed`: a coder actually reviewed the relevant filing (not just a keyword lookup) and found no relevant discussion. A review note is required.

**The unit of classification is filing × provision.** Multiple reasons and counterarguments may appear under a single position; record the main requested action and rationale and preserve additional details in notes. A future argument-level one-to-many table should retain each distinct reason and each cited outside authority without duplicating a filing's stance count.

## Quality gates

- **Accuracy:** A supporting quotation must be a contiguous, exact passage from the stored source version; record its source hash and position. OCR exactness in a local transcription does not by itself establish that the OCR matches the scanned original.
- **Identity:** Normalize the filer field only for exploratory concentration; verify organizational identity manually when publishing comparisons.
- **Selection:** Counts on a human-selected pilot have the denominator `human-reviewed filing/provision pairs`, NOT all filings or people. A census or probability-sampled evaluation is necessary to estimate proportions reliably.
- **Citation:** Link the public original ECFS source; minimize unnecessary republication of individual's details and contact information.
- **False equivalence:** A keyword-matched excerpt can quote and reject the very position named in the excerpt. Never classify a stance based on keyword or topic assignment alone.
- **Source-type exclusion:** The 80 agency-type candidates are unverified: a filing typed `NPRM` might be a public letter. Manual provenance review precedes deleting or categorizing it.
- **Template families:** Repeated language may indicate campaign templates, but not fraudulent coordination. Compare both filing-weighted and unique-text/family-weighted patterns.
- **Publication:** Site should show a clear `Research preview` and no claimed consensus until source, issue and position validation is documented.

## Commands (run locally from repository root)

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 -m scripts.prepare_policy_analysis --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view augmented
python3 -m scripts.build_policy_review_packet --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1
open ~/Downloads/fcc_complete_corpus/analysis_observatory/research_snapshot_ocr_candidate_v1/policy_analysis_augmented/private_review_packet.html
# After a reviewer exports the CSV:
python3 -m scripts.validate_position_annotations --corpus ~/Downloads/fcc_complete_corpus --annotations ~/Downloads/fcc_policy_human_reviews.csv
python3 -m scripts.export_public_site_data --corpus ~/Downloads/fcc_complete_corpus
```

Never commit any of the local generated excerpts, comment transcripts or reviewer CSVs to the public GitHub repo.
