# Project plan — acceptance gates

**Scope:** 2026 FCC E-Rate rulemaking, FCC 26-41, WC 26-133 / 13-184 / 21-93 / 21-455.

## M0 — Corpus integrity (code delivered, review pending owner run)

- [x] Read-only 1-filing-per-ID inventory, document manifest audit, source URLs, SHA-256 check
- [x] PDF short-text warning, missing/placeholder flags, OCR triage CSV
- [x] Prolific filer counts with explicit unverified identity caveat
- [x] Exact duplicate clusters without removing any filings
- [x] Unit tests in GitHub Actions
- [ ] Run against **post-integration** owner's corpus, review flagged missing/hash and very short PDFs
- [ ] Visual/OCR reconciliation for poor PDF extraction, with original hashes and correction log
- [ ] Confirm snapshot cutoff, docket search predicates, full count, date scope and agency notices
- [ ] Reconcile any actual count changes; never change raw FCC source files in place

**Acceptance criterion:** all attachment rows have an auditable reason for any unreadable text; scan-quality issues explicitly recorded; all counts reproducible.

## M1 — Descriptive analysis and identity

- [x] Local interactive dashboard with filing types, dates, filer frequency, exact-dup tables, original links
- [x] Optional lexical theme map using NMF/SVD (exploratory, not published as final topics)
- [x] Optional MinHash near-duplicate candidates (not automatically attributed to campaigns)
- [ ] Human audit of top filer keys, composite identifiers, same-name conflicts and organizational affiliations
- [ ] Review probable near-duplicate letter templates, link publicly documented campaigns
- [ ] Sensitivity analysis: all filings vs exact filer keys vs unique texts; exclude top 1% prolific filers

**Acceptance criterion:** every visualization names its denominator and uses defensible, clearly labeled units; high-frequency identities reviewed.

## M2 — Policy taxonomy and labeled benchmark

- [x] Source-linked provisional issue families + evidence-validation schema
- [x] Deterministic stratified pilot sampling tool
- [ ] Annotate full NPRM with FCC paragraph references for specific proposals/questions
- [ ] Independent dual-annotator pilot; codebook revision; adjudication log
- [ ] Held-out gold benchmark stratified by duplicate family, filer type, document length and OCR quality

**Acceptance criterion:** codebook anchored to primary text, unambiguous direction of each position label, gold set and agreement metrics.

## M3 — Validated classifications and semantic argument map

- [ ] Versioned, cached model-assisted evidence extraction; quota/cost controls, no invented passages
- [ ] Classify stakeholder capacity, policy stance and argument claims independently
- [ ] Verify quoted passages against original texts; manual adjudication of low-confidence results
- [ ] Evaluate precision/recall per position and issue, including abstention rates and error slices
- [ ] Passage-level embeddings, argument map, theme co-occurrence and campaign comparisons
- [ ] Robustness: filer-, filing-, and unique-text-weighted comparisons, uncertainty and date cutoffs

**Acceptance criterion:** model results cannot be published without human benchmark accuracy, denominators, evidence traceability and extraction QC.

## M4 — Public deployment and reproducibility

- [ ] GitHub repo: code, unit tests, source registry, audit reports with privacy review, taxonomy, prompts and validation stats
- [ ] Deployment of reviewed dashboard; public aggregates by default, restrict individual data exports
- [ ] Link every individual quote/claim to public FCC filing; corrections and methodological caveats visible
- [ ] Data refresh for **reply comments due Nov 12, 2026**; capture and compare snapshots

**Acceptance criterion:** independent researcher can reproduce public statistics and trace every headline claim to original source and coding rules, without exposing unnecessary PII.
