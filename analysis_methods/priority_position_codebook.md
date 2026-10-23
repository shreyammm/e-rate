# Priority filing-level adjudication codebook (v0.1)

**Scope:** FCC E-Rate 26-41 research snapshot, 3,231 submissions / 3,230 readable. This is the targeted *Positions & Coalitions* project, kept distinct from GPT-OSS's broad exploratory extraction. The existing Kaggle \`support\`/\`oppose\` fields are **never** treated as authoritative.

## Unit of analysis

One **ECFS filing** for every topic. Count each filing once per answer category; a single filing can endorse multiple discrete ideas. Report 3,231 total filings, 3,230 readable, the number substantively coded for each question, and the number **not yet adjudicated**. Do not call the counts "people" or "public opinion." Compare by source-verified filer role, identify repeat text and organizations, avoid conflating named-person filers with independent citizens.

## Four independent questions

### A. E-Rate funding / scope

Non-exclusive yes/no propositions:
- \`preserve_expand\`: Filer **explicitly recommends** maintaining, continuing, strengthening or expanding E-Rate. Just describing benefits is not automatically endorsement unless the requested outcome is discernible.
- \`abolish_program\`: Explicitly recommends abolishing / entirely terminating / sunsetting E-Rate itself. An objection to an individual eligible expense does **not** qualify.
- \`targeted_restriction\`: Explicitly advocates cutting, withholding, or limiting particular *E-Rate-funded services, recipients, geography, devices or expenditures*. This can coexist with \`preserve_expand\`.
- \`conditional_or_redesign\`: Specific proposal to change the nature of support without necessarily cutting funding.
- \`discusses_no_clear_recommendation\` and \`not_established\`: Insufficient or no relevant text, never impute support from an FCC question quoted in the filing.

### B. **New** federal E-Rate conditions

Separate from existing CIPA rules and voluntary local choices. Non-exclusive:
- \`favor_new_federal_condition\`: Filer explicitly asks for *additional mandatory* federal condition for E-Rate recipients (screen caps, mandated monitoring, parental choice, blocking, educational-purpose standards, etc.).
- \`oppose_new_federal_condition\`: Explicitly objects to *additional* federal conditions.
- \`conditional_or_locally_controlled\`: Supports child safety or reasonable standards but wants narrower applicability, local choice, funding, privacy guardrails, or implementation flexibility.
- \`existing_rules_only\`: Argues existing obligations suffice or should be enforced, without advocating a new federal mandate.
- \`not_established\`.
Specify subtopic and separate **child-safety conditions** from general consultant registration/accountability; "conditions on E-Rate" is otherwise too vague to aggregate.

### C. Screen-time harms / concerns

- \`affirmative_harm_concern\`: Filer expresses its own concern about excessive screen/device use harming learning, development, health, attention, social experience or family life.
- \`questions_harm_claim\`: Explicitly disputes/qualifies empirical harm assertions.
- \`acknowledges_concern_no_policy\`: Mentions concern without clear personal endorsement.
- \`no_evidenced_view\`: Not found; **not** "supports unlimited screen time."
Allow overlap for nuanced filings. Coding harms is distinct from requiring a federal limit.

### D. **Allegations** of misuse of E-Rate funds/resources

Flag as **claims by filers, never established misconduct**. Do not label people/organizations as wrongdoers based on unreviewed public comments. Consider only assertions made/endorsed by the filing author, not merely FCC NPRM recitations, literature reviews, hypotheticals or disputed quotes.

- \`specific_allegation\`: Filer alleges a *concrete instance* of ineligible spending, improper billing, a conflict, procurement manipulation, diversion, or misuse. Must cite the actual action and the named/unnamed recipient described; identity is optional. **Never infer a violation solely because the filer disfavors a legal educational use.**
- \`general_misuse_allegation\`: Expressly says E-Rate is being improperly used, wasted or abused without a sufficiently specific incident.
- \`risk_or_hypothetical\`: Only notes potential misuse/fraud incentives, not an event.
- \`oversight_only\`: Discusses preventing fraud, integrity enforcement or compliance without alleging an event.
- \`not_established\`: No supportable allegation located.
Additional non-exclusive allegation \`subtypes\`: \`ineligible_costs\`, \`billing\`, \`bid_procurement\`, \`vendor_consultant_conflict\`, \`wifi_device_screen_use\`, \`diversion_waste\`, \`other\`.

For every **specific** or **general** allegation, reviewers must also explicitly check whether the filer claims **illegal/ineligible** use vs **normatively undesirable but not necessarily prohibited** use (e.g. objecting to subsidized Wi-Fi on screen-time grounds). These are different dimensions.

## Evidence and adjudication

Each positive verdict requires: exact original-source quote + character offset + filing ID + rationale of why the **filer** endorses the position. A model-generated paraphrase alone does not qualify. If original quote is only an FCC question, quote from an opponent's submission, or a source not endorsed by filer, mark uncertain. Any filing receiving both support and oppose hints, OCR uncertainty, long selected-window analysis, repeated campaign text, or unsupported allegation is flagged for targeted review.

Two review layers:
1. **Complete candidate pass:** read all original filing texts and ALL available source-verified GPT-OSS claims; record source windows and plausible categories. Machine/lexical cues in this layer are **candidate mentions**, not actual validated positions or misconduct.
2. **Independent adjudication:** a reviewer reads the original context, records final codes and evidence, and a second reviewer double-codes at least a randomly selected subset, plus every contentious allegation or contradictory funding/mandate case. Resolve differences; preserve the full revision history.

Draw a random sample from **both candidate-positive and candidate-negative filings** per axis to estimate sensitivity/false negatives, not only a handpicked high-risk queue. Document seed, strata, sample sizes, disagreements and remaining uncertainty. If full adjudication cannot be completed, report audited model estimates with confidence intervals, **never** label all unreviewed cases verified.

## Release conditions

Until adjudication exists, UI counts are **"candidate filings for review"** and do not purport to be how many supporters or misconduct incidents there are. "No candidate located" is not a true negative. Publish 4-way intersections only when all component decisions are adjudicated or clearly qualified as exploratory. Every allegation excerpt displayed on the site must carry "Allegation in a public filing; not an established finding" and direct source links.

The published data must never automatically promote candidate hints into \`verified_support\` or \`verified_allegation\`. Distinct persons and independent organizations require a separate verified identity/deduplication pass.
