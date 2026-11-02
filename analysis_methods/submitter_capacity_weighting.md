# Deduplicating FCC E-Rate commenters by represented capacity

## Counting unit

The stakeholder explorer and comparison matrix use a **distinct submitter–capacity voice**, rather than a filing or a source text. An entity can submit multiple FCC records, and a single named individual can appear in more than one documented representative capacity. For each issue and stakeholder group, a resolved voice contributes at most once, regardless of how many filings or claims it submitted.

The denominator for “within group” is all distinct voices assigned to the stakeholder group, including those without an extracted argument. “Share of topic” uses distinct voice–group assignments with the topic. A voice can appear in more than one group, so group shares need not sum to the number of all distinct voices. No topic count represents verified support or opposition.

The original source filing counts, exact quoted passages, quality flags, and links remain available for audit. They are not used as the main percentage denominator.

## Resolution hierarchy

1. Use primary FCC ECFS filer metadata and any organization recovered from source metadata, document letterhead, or author signature, as classified in the existing player registry.
2. Normalize capitalization, Unicode variants and punctuation. Use source-backed organization alias crosswalks for recognized institutions, but do not merge arbitrary similar-looking names.
3. Treat an institution filing in its own name as one institutional voice.
4. For a named person, use the combination of that person’s normalized name **and the organization they are identified as representing or being affiliated with**. The same named person associated with two different institutions is counted in two capacities. Different named people at the same institution remain distinct unless source evidence says the institution itself was the filer.
5. Do not mistake occupational titles for personal names or quoted paragraphs for an organization. An institution plus a job title is not evidence of a distinct named individual.
6. A joint institutional filing remains one coalition/source unit in the published joint group; the individual co-signers are not multiplied into endorsements.
7. Missing/generic filer identities stay distinct. Verbatim matching or source-text similarity never establishes common identity. If repeated names lack organizational evidence, they are conservatively grouped by the normalized filer field and flagged when relationship evidence is ambiguous.
8. When exactly one institution is supported among repeated identical personal-name fields within the same stakeholder category, a missing affiliation can be inferred conservatively, with its basis and a review flag retained. Never propagate one institution across conflicting named affiliations or stakeholder roles.

This resolution is **not** proof of individual identity, institutional authority, public representativeness, or stance. ECFS does not provide a verified unique-human identifier. Equal names may refer to different people, names may vary across filings, and being employed by an organization does not automatically make a comment its official position. The systematic method cannot substitute for adjudicating the original document on consequential attribution questions.

## Public reproducibility

- Pipeline: `scripts/submitter_identity_resolution.py`, `scripts/build_stakeholder_census.py`
- Source inventory: `data/fcc_corpus/manifest.json` with SHA-256-verified gzip shards
- Main dataset: `docs/data/stakeholder_argument_census.json`
- Reconciliation output: `docs/data/submitter_count_summary.json`
- Source-linked audit: `metadata_diagnostics.raw_name_collisions_split_by_affiliation` and `metadata_diagnostics.repeated_filer_identity_review_queue` in the summary.
- Synthetic regression tests: `tests/test_submitter_identity_resolution.py`
- Publication tests independently recompute all group, topic, and industry union totals from the published filing-level opaque identity IDs.

The raw names used for matching are not published in the derived census. IDs are opaque corpus-local integers, not unsalted hashes of individuals’ names.

## Interpretation

The large repeat-filer clusters include 277 filings associated with Environmental Health Sciences and 65 associated with the California Brain Tumor Association. These counts should not outweigh a smaller organization’s submission solely because one identity lodged many source records.

The unresolved or review-flagged relationships are explicitly listed with original FCC IDs rather than silently assumed to be different people or the same person. Industry rollups use the union of resolved voice IDs, avoiding overlap between vendor and association categories.
