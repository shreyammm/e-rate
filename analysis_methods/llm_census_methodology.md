# Additive free, unattended LLM census (exploratory only)

This lane **does not replace or write** the OCR, deduplication, topic, commenter-identity, human review, or validated policy-position pipelines. Existing `validated_positions.csv` and `validated_argument_claims.csv` are never read as labels or overwritten. LLM output is segregated under `data/llm_census/` or the path explicitly requested by the researcher.

## Operation

* The source must be an authoritative `research_snapshot_*` baseline or OCR-augmented text view, or its **portable export** in `data/fcc_corpus/filings.jsonl`. The corpus is one record per **FCC submission ID**, *not* an estimate of distinct people.
* Every readable filing, including filings with no keyword hits, gets model processing. Long files use overlapping windows. Each window yields zero to many cited arguments; keyword nonmatches are never coded `not_addressed`.
* The model receives the draft FCC policy-codebook's exact **option wording**, not just issue names. It extracts proposal-specific stance, FCC action requested, argument, reason family, claim type and verbatim original evidence; a role is only accepted if the filing itself supplies a matching supporting quote. Multiple positions or rationales per filing are preserved.
* Machine quotes must match the actual text of their source window at an exact character offset, or they are excluded from counted claims. A match validates transcription, **not** coding correctness, truth or external fact-checking.
* Comment text is treated as untrusted data, not as model instructions. Structured JSON generation, deterministic prompt parameters, codebook/model/source hashes and per-file resume checkpoints help reproducibility. No attempt is made to pretend the model is infallible.
* Each filing has a single cached record under `filings/{submission_id}.json`, with `params_key` computed from source text, model, codebook, processing version and chunk settings. New or changed records automatically invalidate themselves, without overwriting other research lanes.
* When a run hits its time or count cap, the scheduler resumes on the next attempt. Partial filings are not included in population counts. Each chunk is checkpointed so even long files can resume after timeout.
* The model is [Ollama Qwen2.5 3B](https://ollama.com/library/qwen2.5); GitHub public-repo standard runners use CPU inference at no service charge. Expect many runs; actual throughput depends on document lengths and runner speed. Free does **not** mean immediate or unlimited concurrent compute. [GitHub standard runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) are free on public repositories; [GitHub Models was retired July 30, 2026](https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-july-30-2026/).

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

## Data ingestion limitation

The previously built 3,231-filing snapshot is on the user's Mac, not GitHub. A bot cannot read files on an offline personal machine. If `data/fcc_corpus/filings.jsonl` does not yet exist, the scheduled workflow **intentionally skips without generating imaginary findings**. An already available export can be checked into the repository; use `python3 -m scripts.export_llm_corpus --corpus ~/Downloads/fcc_complete_corpus --output data/fcc_corpus/filings.jsonl` from a checkout of this code to produce that archive once. It includes original unredacted comments and filer metadata; do not confuse an ECFS public filing with permission to publish arbitrary private metadata. Once any source file is committed, the schedule will automatically process it, checkpoint it, and incorporate future updates. Re-export from a new snapshot when source data changes.
