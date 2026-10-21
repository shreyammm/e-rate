# Full-corpus FCC E-Rate argument mining, attribution, stance, and semantic map
**Architecture decision record — 2026-10-21 (design, not a completed research result)**

## Research product
Understand **all 3,231 indexed ECFS filings** and all recoverable source passages: the author's requested regulatory outcome(s), distinct arguments and rationales, cited authorities, relationships among arguments, identity/representative capacity, repeated language, and relative frequency. The public outputs are an analytically sourced report, an argument-by-commenter quantitative dashboard, a spatial argument explorer, and a question-answer interface that can give source-backed corpus-wide counts. Do not manufacture estimates from selected excerpts or treat keyword hits as positions.

## Layered architecture and authoritative units
**Input:** Immutable FCC filing manifest (one per ECFS filing); attachment and text segments (multiple per filing); citations with exact offsets and SHA-256; docket and provenance flags. Preserve long appendices and missing text in the denominator, but distinguish author prose from reproduced studies and FCC material.

**Segment-level discourse layer (all text):**
- Each paragraph or semantic segment has `segment_id, filing_id, source_document_id, source_start, source_end, text_hash, origin`.
- `origin` values: `author_own`, `fcc_notice_quote`, `third_party_quote`, `appendix_reference`, `letterhead_or_signature`, `ambiguous`. The model can abstain. In-document citations and quotative framing are signal, not dispositive.
- Identify who *asserts* a proposition: `comment_author, fcc, cited_source, other_party, unclear`. The filing author's stance cannot be inferred from propositions attributed to the FCC, critics, or literature citations.

**Claim/argument layer (multiple per filing, no fixed claim cap):**
`claim_id, filing_id, segment_id, source_quote, quote_start, quote_end, source_hash, attributed_speaker, quotation_function, policy_target, requested_action, stance_to_target, claim_content, causal_mechanism, supporting_reason, evidence_type, cited_reference, confidence, model_revision, review_status`.
- `quotation_function`: `own_assertion`, `endorsed_quote`, `quoted_to_rebut`, `neutral_report`, `background_reference`, `ambiguous`.
- `stance_to_target`: `support`, `oppose`, `conditional`, `alternative`, `mixed/conflicting`, `describes_without_position`, `not_addressed` (only after full review), `unresolved`.
- A quote matching its source text is **necessary, not sufficient** to know the claimant or stance. Keep surrounding context (adjacent paragraphs and the authored document heading) for attribution, negation and rebuttal.
- Deduplicate repeated claims *within a filing × target × rationale* without deleting distinct arguments, and preserve multiple directions/conditions.

**Two nonexclusive taxonomies:**
1. A **notice-driven policy-action register** from precise FCC paragraphs: actual proposal, request for comments, hypothetical option, alternative, existing rule. The current 29-item draft is provisional, not a constraint.
2. A **bottom-up argument register** discovered from all authored assertions, including novel topics not explicitly in the FCC register. Record multiple rationales and values separately from the requested outcome.

**Validated counting layer:**
- Report distinct ECFS filings making an *attributed and supported* argument. Supplemental views: distinct verified commenter entities (when validated), distinct normalized texts, near-duplicate family-weighted, positions conditional on actual target.
- Explicit `processed, not_addressed, ambiguous, missing_text, failed` denominators. Automated estimates must be identified as machine coded.
- Quantitative prevalence comes from **applying the final taxonomy to every filing**. No thematic prevalence extrapolation from sample excerpts.
- All published counts drill through to a full (possibly redacted) list of the exact source filing IDs and supporting quoted spans.

## Sentiment and stance: separate concepts
Cheap off-the-shelf sentiment/polarity scoring can be a secondary **tone** signal on the author's own relevant passages (`positive, negative, neutral, mixed`). It is not a substitute for target-specific stance. Use the target-specific classifier to distinguish:
- Negative tone about excessive screen time, but support for maintaining E-Rate.
- A quoted FCC question about eliminating funding followed by the author's **opposition**.
- A commenter supporting consultant registration but opposing a ban on percentage-based consultant fees.
Sentiment labels are optional on the public website and should not lead the analysis. A model claiming neutral may really mean no stance can be inferred.

## Full-corpus extraction workflow
1. **Segment all readable text** (including every long filing) using hierarchy and provenance, not just the first/last N characters. Heuristically flag appendices/quoted FCC text, retain ambiguous material and protect novel arguments in attachments.
2. **Extract author-attributed claims:** initial economical IBM Granite pass may propose spans; require exact source offsets and speaker attribution. There must be no arbitrary five-claims-per-window cap. Preserve failures/empty outputs separately.
3. **Strong semantic verification:** reprocess ALL proposed claims and uncertain negative candidates with a larger US-origin open-weight instruction model (e.g. Llama 8B, Granite 8B, NVIDIA Nematron model subject to actual availability and compute fit). Given subject, target, original span and context, separately answer (i) who asserts it? (ii) endorsement/rebuttal/report? (iii) requested outcome? (iv) reason? (v) conflicting statements? Use a target-oriented NLI/entailment scorer as an independent disagreement flag, **not** as the only source of truth. Keep unresolvable records unresolved. Quantization and 18 GB Mac limits imply slow inference; GitHub CPU-only Actions cannot be assumed to handle full strong-model validation promptly or at zero infrastructure cost.
4. **Discover claims bottom-up on the full extracted set**; have a capable model name hierarchically organized rationale families after reviewing all group members and contrasting groups. Distinguish two claims with similar vocabulary but opposite polarity, and two claims advocating the same FCC outcome for different reasons.
5. **Recode every filing** against discovered families and official policy actions, including candidate negatives retrieved semantically, NOT only original keyword hits. Rerun as taxonomy evolves; keep provenance and versioning. Unknown ≠ no position.
6. **QA and calibration**: independent source-checked coding of a strategically designed evaluation set (oversample negations, long PDFs, near-duplicates, quoted FCC paragraphs, small stakeholder groups) to measure precision/recall on stance, attribution, and argument discovery. This set is for assessing error and prompting full reprocessing, **never a substitute for analyzing all filings**. Can estimate residual error and label machine-only findings as uncertain.

## Semantic embedding and clustering
- Embed **normalized argument statements** (e.g. `target + advocated action + causal reason`), NOT complete filings. Also maintain a rationale-only embedding (e.g. `cause -> claimed consequence`), so people who agree on a diagnosis but want different regulatory outcomes are comparable without losing the outcome distinction.
- Suggested locally available, openly licensed US-origin embedder: `nomic-ai/nomic-embed-text-v1.5` (Apache-2.0, task prefix `clustering:`, up to 8192 tokens; use short claim statements). See https://huggingface.co/nomic-ai/nomic-embed-text-v1.5.
- Compare sentence/argument embeddings to TF-IDF baseline; discover argument groups using HDBSCAN (including an **unclustered** category) or an explicitly justified hierarchical method. Do NOT fix `k=15` because it makes an attractive visualization. Verify semantically coherent groups and overlapping rationales; allow multiple argument groups per filing.
- **Do not compute scientific clusters from the 2D display alone.** Group using original or moderately reduced embeddings; compute reproducible UMAP-2D separately for visualization (seed, version, hyperparameters recorded). Nearby dots indicate approximate local semantic similarity; distant map regions are **not** an exact ideological distance metric. Axis names such as `liberal-conservative` are not justified.
- Use static precomputed coordinates on GitHub Pages (no full model in user's browser). Each **point = argument instance** by default; toggle to group centroid or filing view. Color by stance toward selected target, commenter type, or reason family; size group centroids by *distinct filing* count. Filters for agency-record candidates, other-docket material, OCR quality, identity confidence and template family. Click a group → distribution by organization/role → every source filing → exact passage.
- Two linked visualizations: **argument similarity map** (what reasons cluster together), and **commenter-position bipartite network/matrix** (who aligns on which actions). Neither graph proves coordination.

## Rigorous primary outcomes
1. Quantified policy debate: `support, oppose, conditional, alternative, discussed, unresolved` for each verified decision, with denominator and percentage of completed records.
2. Ranked argument families: distinct filing prevalence, within-filing dedupe, conditional stance splits and subgroup/role breakdowns.
3. Map of agreement and disagreement: show the same *rationale* used for different regulatory outcomes, and different rationales used for the same outcome.
4. Documented organization/individual profiles with verified representative capacity and distinction between individuals and institutions.
5. Template and prolific filer sensitivity (filing weighted, entity weighted, distinct-source weighted); no implied public-opinion representativeness because ECFS is self-selected.
6. Expandable claim ledger and Ask-the-Corpus with mandatory source links and safe counting query translations.

## Existing code: retain, replace, assess
- **Retain**: source manifest, OCR/provenance audit, SHA checks, ECFS links, 3,231-record explorer, exact duplicate detection and checkpointed GitHub workflow.
- **Improve**: `scripts/llm_census.py` currently has a 5-claims-per-window prompt and a 29-category prior; 1B model outputs have low claim yield and must not be treated as verified complete understanding.
- **Replace for final inference**: `scripts/build_claim_landscape.py` currently uses TF-IDF/SVD/MiniBatchKMeans on model-written claims and assigns lexical clusters. It is a discovery baseline, not a semantic argument topology.
- **Add**: source-author-attribution labeler, target-conditioned stance checker, argument embedding/clustering and semantic quality flags, complete final recoding and reproducible join tables, 2D precomputed map.

## Deployment gates
**Gate A**: all 3,231 filing records accounted for and 3,230 source texts segmented without untracked omission.
**Gate B**: speaker-attributed claims extracted and semantic consistency checked across **every** relevant source text, with missing/ambiguous cases shown.
**Gate C**: final taxonomy learned from all extracted claims, then applied to **all** source records; counts have explicit unit and drill-through provenance.
**Gate D**: independently evaluated model error, stability of group assignments, documented perspective comparisons and substantive interpretive report.
Only after B–D should the site describe stance percentages as comprehensive *machine-coded findings*, never as human-verified opinions without corresponding human validation.
