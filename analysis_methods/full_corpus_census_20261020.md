# Exhaustive source-text census — 20 October 2026

## Scope and collection units

All **3,231** indexed ECFS submission records were included. There are **3,230** augmented substantive-text files and one metadata-only record (the link-only filing). The census read **211,756,379** available source-text characters **without trimming or a random sample**. All **29 FCC 26-41 draft codebook provisions** were checked against every filing, generating **93,699 filing × provision retrieval outcomes**, including explicit negative keyword results.

**No support, opposition or argument endorsement percentage has been extrapolated from a 27-excerpt, 100-excerpt or other sample.** The earlier 27-excerpt spot check has been removed as a claim of classifier validity. Do not treat matching vocabulary as independently validated sentiment or position.

## What each public chart actually measures

- **Types of commenter:** Each filing is assigned one *provisional* principal category using its ECFS filer field **and** self-identification / professional role statements found in the actual source text. For example, an individual-name filing can be recoded as educator when the letter says its writer is a superintendent. A personal reference to 'our district' is retained as *school connected, capacity unconfirmed*, not assumed official representation. Scientific source appendices saying 'as a consultant' cannot override the actual filer's organizational attribution.
- **29 FCC provisions:** `docs/data/exhaustive_census.json` records how many filings contain exact terms in the draft issue codebook. A match does not imply support, opposition or even substantive discussion; letters frequently reproduce the FCC's wording as a target of criticism. A negative is `not_detected_by_codebook_terms`, not proof of issue absence. Counts are nonexclusive and cannot sum to 3,231.
- **Argument-language families:** Fourteen sets of source-located, distinct phrases identify reason categories such as recurring costs, rural access, education, statutory authority, consultant integrity, autonomy and privacy. Counts indicate **language present in a filing**, not an endorsed argument. One text can match several families.
- **Source-linked direction:** The 19 first-pass organizational position examples are explicitly separate from the full-corpus retrieval census. They do not justify corpus-wide support/opposition percentages, or network measures asserting that non-reviewed organizations are aligned.
- **Corpus explorer:** Compact IDs, original FCC ECFS URLs, document date, issue-mention tags, OCR flags, and one provisional category for all 3,231 entries. The site's category codes are derived from the full source-text identity pass, not the old name-only heuristic. No personal-name roster or bulk comment text is republished.

## Identity census and uncertainty

The full-text pass assigns 607 records to schools/district institutions, 368 to explicitly identified educators or school employees, 288 to school-connected but unconfirmed-capacity voices, 314 to libraries/library workers, 487 to nonprofits or associations, 76 to self-identified parents, 45 to government/Tribal bodies, 39 other businesses, 13 consultants and firms, 3 telecom/network providers, 4 students, 3 researchers/health professionals, and **984 unresolved**.

These 13 categories sum to 3,231 **filing records**. They do not represent independently verified numbers of unique human speakers or organizations. The method found 598 records with explicit source-text declarations used to identify a role. Another 288 school-connected records remain separate precisely because representative capacity cannot safely be inferred.

## Critical bias and provenance exclusions

- A single normalized exact filer-name field submitted 277 filings and accounts for **80.3%** of all extracted characters. Never weight public opinion by source-text volume.
- **123** filings (about 74.7 million characters, **35.3%** of the overall text) contain source-header signatures of **ET Docket 13-84 / DA 26-997** and all bear the same exact filer field. These are retained in the collection but flagged for E-Rate issue-relevance review. This flag does **not** prove a filing is invalid or should be deleted.
- **80** source manifest entries have submission-type proxies that make them agency-document candidates; their agency origin is **not independently verified**, so their counts are shown as sensitivity flags beside provisions.
- **206** attachments were OCR-recovered, and transcription is candidate OCR pending original-page-level human validation.
- Exact filer fields and content-identical letters are not unique individuals. Repeated boilerplate must be counted by filing, source-distinct text, prospective template family, and verified filer entity before coalition analysis.

## What remains unverified

Even complete coverage of all text does not, by itself, make an accurate *semantic* classification. The first directional regex retrieved passages quoting the FCC's **hypothetical elimination of E-Rate** and would have misreported them as actual pro-elimination comments. This is why the public website reports those direction labels as unresolved rather than publishing a false pro/con chart. A defensible stance census needs every relevant passage **semantically adjudicated** (automated model plus accuracy auditing or exhaustive human review), including opposite/conditional positions, negation, source citations, and cross-proposal distinctions. Unresolved stays unresolved; it is never imputed from a subset.

All original personal-level source evidence, quote offsets, and rows for 93,699 filing/provision checks are retained privately, not committed to the public GitHub Pages repository. Aggregate checks and minimal role codes are published for reproducibility and exploration.
