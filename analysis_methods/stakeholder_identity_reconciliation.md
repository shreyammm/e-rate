# Stakeholder identity reconciliation: 29 October 2026

## What this fixes

The earlier gpt-oss comment-census prompt combined argument extraction and incidental speaker
classification. Its small role taxonomy could not label edtech vendors, trade associations,
telecom firms or other businesses; it abstained on many source-metadata-identifiable filings.
Consequently, its "unknown" labels must never be treated as corrections to the player registry.

The website keeps the source-based deterministic role as a **provisional navigation candidate**.
The new reconciliation ledger compares both independently by exact FCC filing ID, with a
versioned crosswalk and explicit unrepresentable categories. It does not take sides.

## Machine disagreement definitions

- **Both unknown:** no specific comparable label from either.
- **Specific deterministic, LLM unknown:** LLM abstention, not proof of a false positive.
- **Specific LLM, deterministic unknown:** candidate recall lead, not proof of an identity.
- **School institution vs staff:** different legal capacities within the same broad school sector.
- **Cross-sector conflict:** both label specifically and point to different broad sectors.
- **Unmapped taxonomy:** the old LLM has no category that can express the deterministic role.
- **Exact specific match:** models use the same coarse comparable code; still not verification.

The output includes all filing IDs, a confusion matrix, input SHA-256 hashes and a source-linked
risk-ranked review queue. It excludes personal submitter names and raw passages. Public
organization names are included only if they passed the registry's existing organization filter.
Counts are by FCC filing record, not by unique persons, employers or co-signers.

Historical October 29 reconciliation, before the independent pass:
3,230 old LLM records, 70 unmapped roles, 3,160 comparable labels,
1,893 differing labels including abstentions, 253 mutually specific comparisons,
97 different specific categories, 57 school staff-vs-institution cases and
40 cross-sector conflicts. These are **not accuracy percentages**.

## Independent identity-only model pass

The new local American open-weight IBM Granite classifier receives only the public
institution-valued metadata and the *original* FCC filing introduction and signature windows
(first 3,000 and last 2,000 characters for long source texts). It does **not** receive the
deterministic role, the old LLM role or the argument classifications. This prevents simply
copying a previous label, but introduces window truncation risks.

The request uses the same 27 detailed role types as the source-based registry. It specifically
distinguishes professional capacity, institutional submitter, association and representative.
It saves one checkpoint per filing, keyed by source SHA-256 and model name. A verbatim
self-description/signature quote is checked as an exact source substring, but the raw quote
and personal metadata are **not** republished. A public-institution metadata-based role may
be accepted as a model suggestion without a quote; **neither method verifies the correct
interpretation of that evidence**.

Candidate roles never automatically replace the deterministic labels. Invalid role IDs,
unsupported personal-role excerpts or missing metadata must abstain. Source hash changes
invalidate model checkpoints. Run:

    python -m scripts.identity_llm_pass --pending-only
    python -m scripts.identity_llm_pass --limit 300 --max-minutes 80
    python -m scripts.reconcile_stakeholder_labels

The scheduled GitHub Actions pipeline installs the local model, processes pending records,
saves resumable outputs and updates the public identity audit. Public repository changes
may have delayed GitHub Pages propagation. GPU inference would be faster, but the available
GitHub workflow uses the 1B model on a CPU runner and does not purport to match the prior
GPU model's accuracy.

## Required ground truth and publication gate

No corrected sector prevalence/identity accuracy may be claimed until:

1. Verify every initially recognized edtech business, E-Rate consultant and relevant association
   against the complete original PDF, including signatory/represented-client attribution.
2. Stratify source review across **all** four confusion patterns, including two-system
   agreements, both-unknown cases, quote misattribution, scanned PDFs and joint filings.
3. Have two independent reviewers code stakeholder organization, institution type, professional
   capacity and representation relationship from original sources, adjudicating differences.
4. Compute *per-sector precision and recall with denominators and uncertainty*, especially for
   edtech and consulting. A two-model match is not a gold standard.
5. Promote only evidence-backed, adjudicated corrections using
   data/player_review_overrides.json and rebuild the source registry and argument census.
6. Rerun the reconciliation after each material taxonomy or model revision; track sample
   selection and repeated-text filings separately.

Treat affiliation, professional capacity, represented organization and the comment's
policy stance as **distinct concepts**. Never credit a trade association's statement to
each member or a representative's stance to a client without verification.
