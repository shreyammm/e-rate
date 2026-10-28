# How to validate the industry-versus-school argument map

**Status:** This is a research workflow. As of October 28, 2026, the exported queue contains **unreviewed assignments**, not human-confirmed labels or verified positions. Automated machine frequencies remain exploratory.

## Scope and sampling

Run `python3 -m scripts.build_industry_argument_review` after the source-aligned stakeholder census has been built. The script verifies each published filing-by-topic frequency against its underlying filing IDs before producing:

- `docs/data/industry_argument_review.csv`: source-linked review assignments with intentionally blank human judgment fields.
- `docs/data/industry_argument_review_summary.json`: group-by-topic population sizes, reproducible sampling details, and checksum of the exact input census.

**Industry census:** Every provisional edtech company, edtech association, E-Rate consultancy, consultant association, and every *joint institution* submission is assigned to each of 18 distinct argument topics. A joint filing remains a joint filing; being named as a co-submitter does not make that argument the separate opinion of every participating firm. These are known/provisionally identified organizations, **not proof of exhaustive recall of industry participants** hidden in other metadata.

**Comparator sample:** School/district, school staff, school affiliation uncertain, library, parent, network vendor and unknown-group filings are stratified independently by topic, whether the model detected the argument, and evidence/identity risk. A SHA-256 seeded, reproducible pseudo-random sample of filing **records** is taken within each stratum, without dropping duplicate/template submissions. The summary records population `N`, selected `n`, and `N/n` for each nonempty stratum. Sampling is for later classification-performance analysis, not an opinion poll. Deduplicate only as a separate sensitivity analysis.

**Not detected by model** is a retrieval state and never means the original filing did not discuss or endorse the argument. The purpose of negative controls is to uncover missed themes.

## Independent coding

Make two separate private copies of the generated queue. Do not look at the other person's coding before filling your own. For every reviewed row, open the `source_url`, read the **complete original comment**, and inspect relevant PDF pages where OCR was used. Do not rely on the provided paraphrase or short quote. Examine whether the author is speaking, quoting a critic, summarizing an FCC question, acting for a client, or speaking for a joint group.

Only fill the review columns; do not edit original filing IDs, categories, hashes, machine propositions or source URLs. The required review fields are:

| Field | Allowed values | What it measures |
| --- | --- | --- |
| `reviewer_id` | Reviewer-specific identifier | Distinguishes independent human coders |
| `actual_speaker` | `filer`, `third_party_reported`, `fcc_question_or_quote`, `unclear` | Who asserts the argument |
| `argument_present_in_complete_source` | `yes`, `no`, `unclear` | Whether the *topic* is actually present |
| `filer_endorses_argument` | `yes`, `no`, `unclear`, `not_applicable` | Whether the filer takes ownership of that argument |
| `requested_fcc_action` | `support`, `oppose`, `amend_or_condition`, `alternative`, `discussion_no_position`, `not_addressed`, `unclear` | Requested action on the *specific* FCC question, not attitude toward technology |
| `source_recheck_notes` | Text with at least 12 characters | Trace of what was checked in the full source |

For `argument_present_in_complete_source=no`, set endorsement to `not_applicable` and action to `not_addressed`. For a topic that is present but has no clear policy ask, use `discussion_no_position` or `unclear`, **not** `not_addressed`. Fill the optional rationale, verification and represented-organization fields. A quoted external study is not independently checked merely because the source cited it. Named misconduct allegations require a separate fact check.

For each completed row, write what in the full source justifies the decision, especially if it differs from the machine candidate. For source windows or OCR candidates, explicitly record inspecting the full source. Unreviewed rows must remain entirely blank in the human-judgment fields.

## Check agreement before analysis

Place both completed CSV copies **outside the public repository** (for example under `private_data/`, which is gitignored), then run:

```bash
python3 -m scripts.validate_industry_argument_reviews \
  --queue docs/data/industry_argument_review.csv \
  --first private_data/reviewer_a.csv \
  --second private_data/reviewer_b.csv \
  --out private_data/industry_review_qa
```

The validator rejects edited source columns, duplicate assignments, impossible absent-but-endorsed labels, incomplete reviews and matching reviewer identifiers. It writes `quality_report.json` and `disagreements.csv` **privately**. A disagreement must be resolved by reading the original record; the tool does not guess a winner.

**Do not publish an industry position census just because two coders agree.** First adjudicate disagreements, check the represented institution and machine recall, verify full industry coverage, reconcile joint submissions, and independently verify any factual claims selected for rebuttal.

## What eventual frequencies can mean

For fully checked industry filings, count each eligible FCC filing **once per topic**, then report `endorsed filing/topic pairs / all verified filings in that exact industry group` and `filings in a group that endorse the topic / all endorsed-topic filing records across groups`. The latter denominator must include reviewed comparator filings or be explicitly restricted to a stated set. Report total source texts and organization counts separately, and show template-sensitive versions. Even a census of filings is not a census of unique people, companies represented in joint filings, or the American public.

For comparator error rates, a reviewed model-positive and model-negative sample can estimate detection quality *only after adjudication*, weighting each filing by its documented stratum size divided by sample size. Report false negatives and uncertain source/identity cases; model confidence and verbatim quotes are not a substitute for reviewing the actual speech act.

See `analysis_methods/industry_argument_accuracy_gates.md` and `analysis_methods/argument_evidence_protocol.md` for the broader policy and source-truth safeguards.
