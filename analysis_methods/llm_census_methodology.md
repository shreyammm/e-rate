# Additive free, unattended LLM census (exploratory only)

This lane **does not replace or write** the OCR, deduplication, topic, commenter-identity, human review, or validated policy-position pipelines. Existing `validated_positions.csv` and `validated_argument_claims.csv` are never read as labels or overwritten. LLM output is segregated under `data/llm_census/` or the path explicitly requested by the researcher.

## Approved model policy

Only IBM Granite 4.2 3B and 8B are permitted by the program CLI, and the unattended GitHub Actions job uses `granite4.2:3b`. The source never calls unapproved or paid LLM providers. The model's thinking output is disabled in the inference request for faster structured JSON generation. This does not demonstrate model classification accuracy; source-grounded model-only estimates remain unvalidated.

## Operation

* The source must be an authoritative `research_snapshot_*` baseline or OCR-augmented text view, or its **portable export** in `data/fcc_corpus/filings.jsonl` or checksum-verified gzip JSONL shards under `data/fcc_corpus/shards/`. The corpus is one record per **FCC submission ID**, *not* an estimate of distinct people.
* Every readable filing, including filings with no keyword hits, gets model processing. Long files use overlapping windows. Each window yields zero to many cited arguments; keyword nonmatches are never coded `not_addressed`.
* The model receives the draft FCC policy-codebook's exact **option wording**, not just issue names. It extracts proposal-specific stance, FCC action requested, argument, reason family, claim type and verbatim original evidence; a role is only accepted if the filing itself supplies a matching supporting quote. Multiple positions or rationales per filing are preserved.
* Machine quotes must match the actual text of their source window at an exact character offset, or they are excluded from counted claims. A match validates transcription, **not** coding correctness, truth or external fact-checking.
* Comment text is treated as untrusted data, not as model instructions. Structured JSON generation, deterministic prompt parameters, codebook/model/source hashes and per-file resume checkpoints help reproducibility. No attempt is made to pretend the model is infallible.
* Each filing has a single cached record under `filings/{submission_id}.json`, with `params_key` computed from source text, model, codebook, processing version and chunk settings. New or changed records automatically invalidate themselves, without overwriting other research lanes.
* When a run hits its time or count cap, the scheduler resumes on the next attempt. Partial filings are not included in population counts. Each chunk is checkpointed so even long files can resume after timeout.
* The model is [IBM Granite 4.2 3B](https://ollama.com/library/granite4.2) (developed by US-based IBM Research and released under the Apache 2.0 open-source license); GitHub public-repo standard runners use CPU inference at no service charge. Expect many runs; actual throughput depends on document lengths and runner speed. Free does **not** mean immediate or unlimited concurrent compute. [GitHub standard runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) are free on public repositories; [GitHub Models was retired July 30, 2026](https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/).

## Outputs / analyses

The machine-only aggregate preview at `docs/data/llm_exploratory.json` enables independently exploring:

1. **Provision-specific position distributions:** support, opposition, conditional/change, alternatives, discussion only, unclear and within-filing conflicts. Position counts are **filings**, and only fully analyzed filings enter the denominator. Nothing is coded as absence merely because no quote was found.
2. **Argument and rationale distribution:** budget, equity, privacy/expression, child safety, legal authority, implementation and other rationale frequencies. One filing can generate several claim rows, so those counts are **claims**, not additional filers.
3. **Inferred stakeholder cross-tabs:** which arguments and positions appear in self-described school/library/provider/parent/other comments. A role without textual evidence remains `unknown`; this is not verified filer identity.
4. **Issue co-occurrence:** pairs of FCC questions argued in the same comment; a bridge into later network diagrams and coalition comparisons.
5. **Text-campaign sensitivity:** exact normalized text families among completed filings; compare submission-weighted versus unique-text-weighted observations before policy claims.
6. **Source-backed example explorer:** verbatim quote, FCC filing link, issue and stance, labeled unreviewed machine estimate.
7. **Audit/coverage:** missing-text files, incomplete chunk checkpoints, provenance hashes and rejected hallucinated quotes.

## Denominators and publication warnings

Never call model-only estimates validated or representative. Quote-grounding is mechanical string matching; it does not establish stance correctness. Stakeholder inference is particularly fragile. The draft codebook's question boundaries still require exact NPRM paragraph audit. OCR candidate source text remains unverified. Keep LLM and human-reviewed results visibly separate in the interface. Exemplar rows are sampled in submission-ID order and **not representative** of all categories. Annotated human samples and intercoder checks remain essential before using the estimates as public findings.

## Source archive and live publication

The 3,231 ECFS filing records have been published in this public repository, in 12 compressed JSONL files, from the October 20, 2026 OCR-augmented research snapshot. The original 3,230 readable comment transcripts are preserved; one record lacks a transcript. These are not ongoing live counts from the FCC API. The independently checksum-verified website source is rebuilt by `scripts/publish_full_corpus.py` in the public `docs/data/full_text_shards/` directory. The reader is `docs/corpus.html` and links directly to original source filings.

## Automatic model-quality controls and interpretive limits

- The approved IBM Granite model must return an explicit JSON `claims` array. A missing or malformed array is a retryable model error, **not** a filing with zero policy claims.
- Verbatim source evidence for positions must contain at least 15 characters and match the exact text window and filing offset. This is mechanical grounding, not proof of correct interpretation.
- Any inferred stakeholder role requires an exact supporting passage; inconsistent roles across sections are downgraded to unknown.
- Long filings are processed in bounded, overlapping windows, checkpointed, and resumed on subsequent scheduled runs. They are never counted as completed until every window finishes.
- `data/llm_census/suggested_human_audit.json` lists reproducibly selected source-linked cases flagged for OCR uncertainty, conflicting positions, invalid/missing quotes, long documents and random audit coverage. They are **not** assumed to be reviewed merely because listed.
- The reporting output distinguishes filings, cited arguments, unique normalized source texts and machine-inferred roles. A single filing can have multiple arguments or discuss multiple provisions.
- Each provision has an inferred stakeholder-by-position matrix and a reason-by-position comparison; these are exploratory cross-tabs, not validated estimates or representative public polling.
- GitHub Actions must report inference failures as failures while retaining any completed checkpoints, instead of showing an apparently successful census from a failed model invocation.
- The original first-pass analytical procedures (OCR, deterministic keyword retrieval, clustering, human annotation and source validation) remain unchanged and separately published.

Publicly accessible source comments can contain filer names and contact information. Their republication was requested by the researcher. Actual FCC filing texts may include prompt-injection-like instructions, but the model treats them as data; no approach completely eliminates model errors. Reviewers should inspect a balanced stratified sample and reconcile uncertainty before interpreting substantive rates.
