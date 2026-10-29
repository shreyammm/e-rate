# Accuracy review protocol

## Unit of analysis

A filing record is not a unique person, organization, or substantive endorsement. Keep distinct filing, unique normalized text, verified institution, and signatory counts separate.

## Human review sequence

1. Confirm filing identity and whether the claimed affiliation is the submitter, signatory, quoted third party, or vendor mentioned in passing.
2. Read the original filing around each extracted passage and verify the text is attributed to the filer rather than a quote, hypothetical example, or reproduced notice.
3. Record stance on a *specific* policy action separately from whether a topic is mentioned: supports / opposes / conditional / mixed / describes without a position / cannot determine.
4. Review each rationale independently, with exact source passage and an explicit yes / no / uncertain. One filing can advance several rationales, including incompatible ones.
5. Flag scanned PDFs, truncated long filings, duplicate templates, mixed dockets, agency summaries, and co-signed institutional letters.
6. Use blind second review for a random slice of audited records and adjudicate disagreements against the original FCC PDF.

## Measurement rules

- Use mutually exclusive, documented source-verified institutional roles for primary group counts; preserve secondary affiliations without double-counting filings.
- Show a denominator for each percentage, and clearly distinguish `argument in group / all group filings` from `group share of argument / all filings with that argument`.
- Provide full-record and unique-text sensitivity counts; document sampling strata and inclusion probabilities before using human labels to infer corpus-wide rates.
- Never label missing extraction as true absence, or mixed model support/oppose labels as verified ambivalence.
- Report precision and recall on held-out source-adjudicated cases separately for edtech vendors, consulting firms, schools, and remainder; no quality claims until completed.
- When reviewing misuse allegations, distinguish specific allegation, hypothetical concern, call for oversight, and verified adjudicated fact. Never treat accusations as findings.

## Release gate

Before reporting verified who-supports-what proportions, require source citations, complete docket and filing coverage, a versioned review codebook, adjudicated sample results with uncertainty intervals, and a cross-check against duplicated filings.
