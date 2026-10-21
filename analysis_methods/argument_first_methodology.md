# Argument-first analysis: evidence architecture (v2)

## Primary research question

What patterns of reasoning, desired outcomes, justifications, tensions, and stakeholder perspectives actually appear in the complete FCC E-Rate corpus? **The analyst's 29-option codebook is a secondary regulatory crosswalk, not the discovery framework.**

## Four distinct evidence types (do not conflate)

1. **Corpus-discovered language clusters.** The published `argument_landscape.json` contains 16 clusters from unsupervised source-text analysis of 14,517 extracted argument-related passages. Working labels are the most distinctive terms, not verified summaries. The Atlas deliberately uses original `topic_terms`, source excerpts, and filing-language matches—not the LLM-generated `llm_synthesis` field included for a separate exploratory page. One filing can match several clusters. Source samples are chosen automatically and are not probability samples.
2. **Analyst-defined argument-language families.** Fourteen intelligible reason-vocabulary families were detected across all 3,230 available source texts, and counts are published in `exhaustive_census.json` and `argument_language_by_role.json`. They are **not organically discovered**, and their frequencies count *mentioning filings*, not filings endorsing the argument. Display by stakeholder within-category rates, without treating provisional categories as verified identities.
3. **Interpreted claims, positions and relationships.** GitHub's small Granite model and Kaggle's gpt-oss GPU model independently extract requested actions, reasons, quotations, and potentially conflicting assertions. These results are separate from the corpus-only Atlas. Their agreement is neither required nor sufficient for publication as validated stances; every specific claim must retain filing ID, source quote, exact offset and scope, extraction model, and review state. The `argument_first_ontology_v2.json` describes the future normalized schema.
4. **FCC regulatory crosswalk.** The 29 entries in `provision_codebook_v1.json` contain a mixture of proposals and questions for comment with broad (not verified per-option) paragraph ranges. Use them for procedural/regulatory analysis after discovering the underlying arguments. A keyword hit is not an endorsement.

## Research modes

- **Find patterns:** explore clusters, read their characteristic phrases and source quotations, compare the proportion of repeated quotations in a small auto-selected sample, and flag clusters dominated by one heuristic category. These are *review priorities*, not accusations that comments were coordinated or irrelevant.
- **Study reasons:** compare 14 reason vocabularies against full-category denominators and inspect their separate potential cross-docket-text flags. Do not infer coalitions from common words alone.
- **Study disagreement:** formulate tensions as questions and run Ask the Corpus across all original source text. Do not claim one faction exists, is prevalent, or is opposed by another from a pre-written question; extract and verify examples of requested actions first.
- **Study relationships:** a visual link between lexical clusters means only overlapping high-weight vocabulary. It does not mean that the same filing addresses both, that its signatories agree, or that the contents are substantively compatible.
- **Connect to the FCC:** navigate the secondary regulatory crosswalk for specific disposition, notice status, and corresponding corpus-wide source evidence.

## Necessary next substantive validation

1. Independently inspect high-repeat and source-concentrated clusters, especially radiofrequency-related clusters that may reflect long cross-docket materials. Deduplicate source texts and use source-family-weighted sensitivity analyses.
2. Develop filing-level membership lists for each discovered theme so co-membership and trend plots can be computed from actual records. Aggregate-only language cluster counts do not support those plots.
3. Independently adjudicate a stratified sample of stance/argument classifications with an explicit taxonomy of requested actions, rationales, and evidence. Include keyword-negative and high-risk cases.
4. Compare models by exact source passage, not headline-level cluster assignment. Log disagreement and coverage for both Github and Kaggle; retain extracted claims as unreviewed until review.
5. Before any publication of a measured coalition or full-corpus support percentage, establish denominator, independent-text sensitivity, identity/capacity verification method, and source-review quality.

## Source limitations

Research snapshot October 20, 2026: 3,231 ECFS records, 3,230 with available extracted text. Text includes provisional OCR; exact quote verification against extracted text does not establish that OCR faithfully reproduces a scanned original. Filer categories and cross-docket flags are provisional. These are public filings, not a representative public opinion sample. One frequently repeated filer-name field is associated with unusually large attached documents; character-weighted measurements should not be mistaken for respondent-level evidence.

## The website

The argument-first experience starts at `docs/atlas.html`, with a landing callout in `docs/index.html` and `docs/research.html`. The secondary FCC-specific index lives at `docs/regulatory.html`. Previously built full-text, patterns, comparisons, similarity, Ask, and LLM pages remain available.

The ontology and UI are complementary to existing corpus code and do not modify or replace either ongoing LLM workflow.
