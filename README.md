# FCC E-Rate Comment Observatory — argument-first public research

**Primary research entry point: [Stakeholders & Arguments](https://shreyammm.github.io/e-rate/stakeholders.html).** Compare who filed what by stakeholder and topic, with within-group and within-topic filing frequencies, verbatim original-source evidence, sector-specific company and consultant categories, and plain-language comparisons. The project is organized around what appears in the original FCC comment record: recurring language, reasons, commenter perspectives, disagreements requiring investigation, and direct filing evidence. The analyst's 29-item policy codebook is now a **secondary FCC regulatory crosswalk**, not the research taxonomy.

- [**Stakeholders & Arguments**](https://shreyammm.github.io/e-rate/stakeholders.html) — main editorial research interface. A reproducible, complete-file snapshot of source-linked candidate arguments, with no fabricated stance counts. Clean separation of named edtech companies, their trade associations, E-Rate consultants, telecom/network vendors, schools, parents, libraries and unknown roles. Original quotations and denominator-aware frequency matrices.
- [**Kaggle Research Studio**](https://shreyammm.github.io/e-rate/kaggle.html) — the primary GPT-OSS 20B research layer: complete 14,835-row Kaggle evidence ledger across 3,230 readable filings, 42 open-ended exploratory claim groups, question/claim retrieval, provisional role/issue comparisons, per-filing profiles, 150 risk-prioritized audit cases, all-filing quality triage, downloadable evidence and optional on-device LLM synthesis of every query-matched claim. Source-only analysis is retained independently.
- [Argument Atlas](https://shreyammm.github.io/e-rate/atlas.html) — source-linked open-ended full-document topics (21 current exploratory NMF topics), 16 separate debate-passage clusters, 14 transparent reason-language families, stakeholder prevalence, overlap map, and questions of disagreement.
- [Research Studio](https://shreyammm.github.io/e-rate/research.html) — evidence-first navigation to comparison, time patterns, duplicate sensitivity, exact source phrases, and document similarity.
- [Ask the Corpus](https://shreyammm.github.io/e-rate/ask.html) — rescan all 3,231 source records for each question, browse source excerpts and all lexical matches, optionally generate a locally sourced citation-bearing synthesis.
- [Secondary regulatory crosswalk](https://shreyammm.github.io/e-rate/regulatory.html) — 29 analyst-defined FCC questions/proposals with explicit notice-status labels, language-mention counts, and interpretation cautions.
- [Separate machine-extraction explorer](https://shreyammm.github.io/e-rate/llm.html) — GitHub Granite, Kaggle gpt-oss, and any other model outputs are *unvalidated interpretive analysis*, not the source-only statistics.

**The two discovery systems are different:** `scripts/discover_open_topics.py` analyzes full extracted text without a prespecified FCC proposal or advocacy-sentence filter. The older `scripts/build_argument_map.py` first selects candidate debate-like sentences; its 16 lexical clusters are therefore narrower. Both are exploratory language structures, **not 21 + 16 verified substantive arguments**. The 14 reason families are analyst-defined vocabulary groupings, not discovered claims. One filing is not necessarily an independent person, a word match is not endorsement, and self-selected filings do not estimate public opinion.

Research methods and future source-grounded claim schema: [argument-first methodology](analysis_methods/argument_first_methodology.md) and [argument-first ontology](analysis_methods/argument_first_ontology_v2.json). These are additive: the GitHub/Kaggle automated LLM jobs are not interrupted.

---

## Analyze every FCC filing on an Apple Silicon Mac (automatic GitHub upload)

For an **M3 Pro Mac with 18 GB of unified memory**, the suggested local model is US-developed, Apache-2.0 licensed **IBM Granite 4.2 8B** (the default Ollama quantization is approximately 5.3 GB). Local inference is a much better fit than running a quality model on GitHub's free CPU-only runner. Larger open models such as gpt-oss 20B may technically fit some 18 GB setups but risk substantial memory pressure and slower end-to-end processing.

Paste this into macOS Terminal (requires Python 3 and Git):

```bash
cd ~/Downloads && { [ -d fcc-llm-local/.git ] || git clone https://github.com/shreyammm/e-rate.git fcc-llm-local; } && cd fcc-llm-local && caffeinate -i bash scripts/run_local_analysis.sh
```

The bootstrap checks for Ollama, installs it via Homebrew when available, or points you to the official macOS installer if not. It downloads **`ibm/granite4.2:8b`** once, verifies the model extraction tests, then processes the entire public corpus in safe batches. All original texts are already in GitHub, so there is no need to export or reupload files from the Mac. A temporary `--once` option runs one batch for an initial speed check.

After *each* batch, the runner writes independent, source-linked machine-classification checkpoints to `data/llm_census_mac/filings/`, refreshes `docs/data/llm_mac_exploratory.json`, and pushes them directly to `main` with Git. You may need to authenticate to GitHub on your first push. **Stopping and rerunning the exact command resumes saved work; it does not need to begin the corpus again.** Keep the Mac awake, powered, and its lid open while inference runs. Processing 3,230 readable filings may take many hours or longer, depending on document lengths and actual Apple Silicon inference speed.

The separate `data/llm_census_fast/` and legacy `data/llm_census/` GitHub CPU batches remain preserved. The website prefers local 8B exploratory results once available; `scripts/build_argument_map.py` incorporates local annotations first, and `.github/workflows/argument-map.yml` automatically rebuilds the source-grounded argument clusters when local checkpoints are pushed.

All outputs remain **machine-generated, unvalidated analytical estimates**. Exact duplicates with byte-identical comment texts may reuse the same quoted inference under their respective original filing IDs, but fuzzy text variants are never silently treated as identical.

## Priority positions and possible E-Rate misuse (four-question study)

The [Positions & Coalitions reviewer](https://shreyammm.github.io/e-rate/positions.html) asks four questions of every public FCC source filing, while preserving separation between automated retrieval and independently validated position counts: E-Rate continuation/abolition/targeted restrictions; proposed **new** federal recipient conditions; screen-time harms; and **allegations** of E-Rate resource misuse (versus routine oversight or hypothetical risk). Source excerpts and precise offsets are linked. The source scan covers all 3,230 readable filings and makes no use of the unreliable Kaggle support/oppose polarity field. Reviewer annotations live in the browser and can be exported as CSV; a single review does not create validated population counts. Specific allegations are not legal findings. Codebook: `analysis_methods/priority_position_codebook.md`.

## Kaggle Research Studio: complete machine-evidence exploration

The [Kaggle Research Studio](https://shreyammm.github.io/e-rate/kaggle.html) is the first stop for analyzing the finished GPT-OSS 20B census. Unlike the source-only [Argument Atlas](https://shreyammm.github.io/e-rate/atlas.html), every research panel is grounded in the Kaggle machine-extracted argument record. The main view uses `docs/data/kaggle/machine_claim_rows.json` (14,835 rows) and `docs/data/kaggle/claim_landscape.json` (42 exploratory clusters), plus verified corpus metadata and the 150-entry human-audit suggestion queue.

What is implemented:
- **Full claim ledger:** filter all 14,835 source-linked LLM claims by text, issue, reason, commenter category, provisional position, group, OCR and sunset-stance review status; export the complete filtered set; follow FCC links and source offsets.
- **Question evidence workspace:** evaluate **every** Kaggle claim for each question with transparent concept/lexical expansion; display question-specific requested actions, reasons, organizational roles, opposing evidence candidates, source links, and a drilldown that includes all retrieved rows rather than a top-12 cap. This is not a true transformer embedding-based semantic index, and a lexical/concept retrieval miss is possible.
- **Optional on-device question synthesis:** locally load the free Microsoft Phi-3.5 Mini WebGPU model to read **all question-matching Kaggle claim rows** in batches and progressively synthesize a source-cited answer. No arbitrary input-row sampling cap. This can take substantial time; user opt-in is required. This is **not** a claim to read every original FCC word through the model for each question or to guarantee complete recall.
- **Argument-family explorer:** inspect all rows in any automatically discovered group, tentative reasoning structure, distinct filing and distinct source-text counts, and related issue pairs. Labels are provisional and group membership does not establish endorsement.
- **Who-says-what, issues, and filing profiles:** use the original filing metadata role crosswalk rather than the model's frequently unknown role field, show organizational comparisons, and inspect an entire individual comment's extracted claims with original evidence links.
- **QA and researcher decisions:** automatically generated per-filing quality index (short/full versus selected long-document windows, no grounded claims, OCR, suspected polarity reversal); a 150-case source-linked audit queue; browser-local review decisions and CSV export. The source LLM extraction files remain unchanged. The QA flags are *candidates*, not automatically validated corrections.
- **Interpretation guardrails:** machine support/oppose totals for `erate_sunset` are withheld because concrete source examples show that support for continuing the program can be misread as support for sunsetting it. No unvalidated label is interpreted as a surveyed person's position. Long-filings semantic reading remains incomplete for 417 filings. Exact quote offsets verify source matching, not semantic correctness.

Every query's source-only full-text scan is preserved in [Ask the Corpus](https://shreyammm.github.io/e-rate/ask.html), which additionally shows the Kaggle evidence index alongside the raw source excerpts. User research can therefore distinguish source text, machine classifications, question retrieval, and new optional generative synthesis.

Outstanding research work: independent human validation with a randomized control sample, semantic reprocessing of the unexamined portions of 417 long filings, correction of misclassified policy stances in a versioned audited layer, identity verification, and a fast hosted LLM service if genuinely immediate free-form generative answers are required. The website currently provides a feature-rich evidence and locally generated synthesis path, but **does not yet guarantee flawless semantic retrieval or audited stance counts**.

## Ask the Corpus: full original-text, question-specific model analysis

[Open **Ask the Corpus**](https://shreyammm.github.io/e-rate/ask.html) to research the October 20, 2026 FCC E-Rate corpus. This browser-based, no-paid-API capability runs **separately from the ongoing GitHub Granite and Kaggle GPT-OSS classification pipelines**.

- **Full original text fed to the model for every question.** The site first searches all 3,231 filing records (3,230 readable) and offers a lexical evidence navigator. **Lexical matching is NOT a filter for the model.** With generative analysis enabled, the site streams every original readable text again, breaks long documents into overlapping 4,000-character windows, and sends *every* window to the on-device Microsoft Phi-3.5 Mini model. No document shortlist, per-filing excerpt cap, or top-12 prompt limit applies to this path.
- **Source-verified claim ledger and multi-stage synthesis.** Each model window produces question-specific relevance and argument records. Model-extracted quotations must exactly match the original source window; otherwise processing retries and then fails closed. All validated claim rows, including evidence offsets and source IDs, are retained in a downloadable research ledger. Every claim row is passed through hierarchical, source-ID-checked synthesis; a final answer is withheld until all readable source windows and reduction batches have succeeded. No model can guarantee perfect semantic recall or a lossless synthesis: the full ledger remains available for manual scrutiny.
- **Resumable research.** The site stores successfully processed windows and synthesis batches in local browser IndexedDB when available. A cancelled or interrupted run can be restarted for the same question without repeating successfully checkpointed work. **This is not a cloud/background process:** the browser must stay open and awake while model inference is running. Questions across 3,230 texts can require thousands of model calls and may take many hours or be impractical on some devices.
- **Free US-developed open model.** Phi-3.5 Mini uses WebLLM/WebGPU, with a multi-GB initial model download and roughly 3.7 GB of GPU memory required. The source-only evidence navigator works even where the model cannot run. The site does not invent a full-corpus LLM answer when GPU support is absent, incomplete, or model validation fails.
- **Research boundaries.** All original text is model-processed for a completed run, but the model can still omit or misunderstand arguments. This is unvalidated machine extraction, not a verified prevalence estimate or a representative survey. Exact-text citations demonstrate source provenance, not interpretive correctness. Model-generated support/opposition fractions must be independently audited. Filings containing unreadable text cannot be semantically analyzed until source material exists.
- **Tests.** `tests/test_ask_full_corpus.cjs` checks exhaustive source scanning; `tests/test_ask_exhaustive.cjs` checks original-text window coverage, resumability, citation verification, cancellation, and refusal to answer after source failure.

## Automatically discovered whole-corpus argument landscape

[View the argument map](https://shreyammm.github.io/e-rate/llm.html#argument-map). The complete public archive has been scanned to identify 14,517 candidate argument-language passages across all 3,231 ECFS filing records. `scripts/build_argument_map.py` groups them into 16 preliminary themes, shows frequent filer fields, provisional commenter categories and direct source quotations, and separately groups open-ended arguments extracted by the per-filing Granite model. `scripts/label_argument_map.py` uses US IBM Granite 1B to summarize and name discovered argument themes without manually training or labeling data. GitHub Actions automatically refresh the map as extracted claims accumulate.

**Important separation:** The first-pass whole-corpus map is unsupervised passage clustering (NOT a census of support/oppose). The stricter LLM claim map includes only filings that the model has analyzed and cited. Both display their coverage and source limitations rather than extrapolating from a handful of comments to the whole docket.

## Automated free LLM analysis — separate exploratory research lane

An **additional** LLM census has been installed alongside (not in place of) the existing audit, topic-modeling, human-review, and public-data methods. [Open the separate LLM explorer](docs/llm.html) and read [the methodology](analysis_methods/llm_census_methodology.md).

- **Free inference:** scheduled GitHub Actions jobs now use the faster US-developed, Apache-2.0 open-source `ibm/granite4:1b-q4_K_M` instruction model (roughly 1.6B parameters, 1 GB quantized weights) on standard public-repository CPU runners. This uses no paid API key, no user training or manual labeling. Earlier Granite 4.2 3B checkpoints remain separately preserved in `data/llm_census/` while the new workflow writes to `data/llm_census_fast/`. Each run checkpoints progress and resumes; there is no claim that all 3,231 records have finished model inference yet.
- **Per-filing questions:** provision-specific requested actions and stances, verbatim evidence, arguments and rationale, stakeholder role grounded in comment text, exact-duplicate-weighted counts, issue co-occurrences, and corpus coverage.
- **Auditability:** every accepted quote must occur in the source excerpt at its recorded character offset. OCR-candidate uncertainty, conflicting stances, duplicates, missing texts, model/codebook versions, and unmatched claims are tracked. These are **machine-generated exploratory hypotheses**, never certified survey estimates or manually validated positions.
- **Automatic cadence:** once `data/fcc_corpus/filings.jsonl` or verified `data/fcc_corpus/shards/filings-*.jsonl.gz` files exist in GitHub, [the scheduled workflow](.github/workflows/llm-census.yml) checks for remaining filings six times daily and writes the separate `data/llm_census/` and `docs/data/llm_exploratory.json` outputs. Do not copy this machine output into human-reviewed records.

**Source upload status (October 20, 2026):** The 3,231-filing source corpus with 3,230 readable source texts is **published in this public repository** as 12 checksum-verified gzip JSONL shards under `data/fcc_corpus/shards/`. GitHub Actions independently verified and copied those complete texts into `docs/data/full_text_shards/`, with per-filing metadata in `docs/data/full_corpus_index.json`. [Browse and search full source texts](https://shreyammm.github.io/e-rate/corpus.html). The separate IBM Granite LLM census runs in resumable scheduled batches; a workflow starting successfully is **not** proof its substantive analysis is finished. The original research and source document files are never modified by model inference.


## Public website: GitHub Pages (not localhost or hosted Streamlit)

The long-term dashboard is a static site in [`docs/`](docs/) powered by selectively published, **source-validated** aggregate JSON. It uses no Python server, Streamlit account or browser API keys. The older `app.py` is an internal prototype, not the planned public product.

To activate GitHub Pages once the code is merged: open this repository's **Settings → Pages**, under **Build and deployment** choose **Deploy from a branch**, select `main` and `/docs`, then Save. The eventual address is expected to be `https://shreyammm.github.io/e-rate/` **after** GitHub successfully publishes it. Validated research data are not published automatically. The original extracted comment text is publicly accessible through the dedicated full-corpus reader.

## Research question: what are commenters actually advocating?

Unlike the initial keyword topic model, substantive analysis is grounded in **specific FCC policy options** and tracks (a) proposed regulatory action; (b) support, opposition, conditional endorsement, or an alternative; (c) reasons, predicted costs/benefits and cited evidence; (d) whether and how the commenter claims to represent an organization; (e) text-template and repeat-filer sensitivity. See [`analysis_methods/substantive_position_research_protocol.md`](analysis_methods/substantive_position_research_protocol.md).

The first draft [`analysis_methods/provision_codebook_v1.json`](analysis_methods/provision_codebook_v1.json) operationalizes 29 FCC policy questions across program eligibility, discounts, screen use, CIPA, consultants and administration. These are *draft* proposal boundaries; check exact FCC paragraph citations before final publication.

Prepare source-exact passage candidates (NOT stance labels) and create a private side-by-side review interface:

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 -m scripts.prepare_policy_analysis --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view augmented
python3 -m scripts.build_policy_review_packet --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1
open ~/Downloads/fcc_complete_corpus/analysis_observatory/research_snapshot_ocr_candidate_v1/policy_analysis_augmented/private_review_packet.html
```

Once actual human-coded annotations are exported to `~/Downloads/fcc_policy_human_reviews.csv`, run:

```bash
python3 -m scripts.validate_position_annotations --corpus ~/Downloads/fcc_complete_corpus --annotations ~/Downloads/fcc_policy_human_reviews.csv
python3 -m scripts.export_public_site_data --corpus ~/Downloads/fcc_complete_corpus
```

These commands generate a *private* evidence review and a private public-data preview. Publishing results into `docs/data/public_results.json` requires explicit `--publish-reviewed` **after** validation and privacy review. All raw source texts, reviewer forms and keyword candidate rows stay off public GitHub.

# FCC E-Rate Public Comment Observatory

An auditable, research-grade project to map **who participates, what they say, which issues they discuss, and how repeated submissions affect the interpretation of FCC E-Rate public comments**.

**Current status (October 20, 2026):** The local 3,231-filing research corpus now has 3,230 files with substantive original or staged OCR-candidate text, 206 OCR-recovered PDF attachments, two immutable research-text views, exploratory topic comparisons and candidate repeated-text families. A GitHub Pages research website is being built under `docs/`. The provision-level coding, commenter/entity identity and argument analysis are **not yet validated or published**. No fabricated findings.

## Research scope

FCC 26-41, WC Dockets 26-133, 13-184, 21-93, 21-455. [Official June 2026 NPRM/FNPRM](https://docs.fcc.gov/public/attachments/FCC-26-41A1.pdf) and [Federal Register notice](https://www.govinfo.gov/content/pkg/FR-2026-08-14/pdf/2026-16590.pdf). Initial comments were due October 13, 2026 and replies November 12, 2026. The local 3,231-filing snapshot is **not** represented as the final docket population; later filings/replies must be appended as a documented snapshot refresh.

## Run locally on macOS

1. Put the repo directory (`erate-observatory`) in `~/Downloads` alongside your existing **`~/Downloads/fcc_complete_corpus/`**. Do not move or edit the original corpus.
2. In Terminal:

```bash
cd ~/Downloads/erate-observatory
python3 -m erate.engine --corpus ~/Downloads/fcc_complete_corpus
python3 scripts/ocr_triage.py --corpus ~/Downloads/fcc_complete_corpus
python3 -m erate.annotation sample --corpus ~/Downloads/fcc_complete_corpus
```

Alternatively, double-click `run_first_audit.command` in Finder (Terminal may ask you to allow it).

3. Start the interactive dashboard:

```bash
python3 -m pip install -r requirements-dashboard.txt
python3 -m streamlit run app.py -- --corpus ~/Downloads/fcc_complete_corpus
```

4. Optionally find likely form-letter families:

```bash
python3 -m erate.near_duplicates --corpus ~/Downloads/fcc_complete_corpus
```

The analysis is written to **`~/Downloads/fcc_complete_corpus/analysis_observatory/`**, leaving original text and manifests unchanged. Reports include `summary.json`, `filing_inventory.csv`, `document_audit.csv`, `filer_concentration.csv`, `exact_duplicate_clusters.csv`, `review_queue.csv`, `pdf_ocr_review_queue.csv`, and manual-coding templates. The dashboard runs locally and exposes source links to the FCC.

## What to audit before trusting a percentage

In a prior, **pre-integration** manifest, 194 PDF attachments had extracted text of 100 characters or fewer despite many having extraction status `embedded_text`. Whether they were scanned or poorly extracted is not yet verified. Run the **current** audit on your Mac and inspect its PDF queue before classifying stakeholder opinions. Download completion != readable text.

## Methodology, transparency and reproducibility

See [analysis_methods/methodology.md](analysis_methods/methodology.md) and [analysis_methods/issue_taxonomy.json](analysis_methods/issue_taxonomy.json). All statements of sentiment/stance must have traceable quotes and validated coding; `unknown` is an acceptable result. Public comments are self-selected, not a representative poll.

At the researcher's explicit request, the original public-FCC extracted comment text and associated filer fields are in the public repository and source-text reader. Some ECFS filings may contain personal details. `.gitignore` still protects locally generated research files, secrets and authentication keys. Do not commit FCC API keys or unrelated personal data.

## Testing

```bash
python3 -m unittest discover -s tests -v
```

## Roadmap

1. **QC/OCR:** audit full corpus; visually review short PDFs; repair extraction using provenance-preserving versioned outputs.
2. **Identity and participation:** adjudicate repeated filer entities and organization affiliations; compare filings vs distinct filers vs distinct texts.
3. **Policy taxonomy:** anchor to FCC 26-41 numbered paragraphs; build 120+ manually coded samples and held-out template families.
4. **Theme discovery and evidence-backed labeling:** embed passages, cluster arguments, use LLM labels only after strict evidence/validation gates, quantify failures.
5. **Interactive research publishing:** searchable source-backed issue and stakeholder matrix, argument maps, campaign clusters, weighting/sensitivity toggles, GitHub Pages or hosted Streamlit dashboard with a publication privacy review.

## Current provenance of demonstration data

The complete OCR-augmented source filing texts are now committed as compressed shards. Original analysis methods still compute source-traceable figures rather than shipping fabricated charts, and unreviewed model-derived estimates remain separate.

### Optional exploratory theme map

After installing `requirements-dashboard.txt`, run:

```bash
python3 -m erate.topics --corpus ~/Downloads/fcc_complete_corpus --topics 12
```

This creates deterministic, provisional TF-IDF/NMF topics and a 2D SVD projection that can be explored in the **Theme explorer** dashboard tab. Its categories are **not** policy positions, and the map should not be used for publication before the OCR and human-validity review. Duplicate normalized texts are fit only once, and original filing counts are retained for plotting. Long filings may be truncated for model input, with the truncation count reported explicitly.

### Corrected v0.2 quality gate (after the first 2026-10-20 audit)

The original v0.1 report incorrectly counted **short combined text** as **missing/ambiguous**
combined text because of a substring-based flag check. The corrected count uses
actual combined-file matches. **Original v0.1 exact-duplicate counts should also
not be cited**: the downloader embedded each unique FCC filing ID in generated
combined-text headings, thereby defeating exact text hashes. The corrected
analyzer strips only recognized downloader-generated source headings and page
markers for deduplication, while preserving all original content on disk.

To rerun the audit after pulling the latest GitHub code:

```bash
cd ~/Downloads/e-rate
git pull --ff-only
zsh run_first_audit.command
python3 scripts/pdf_deep_audit.py --corpus ~/Downloads/fcc_complete_corpus
```

`pdf_deep_review.csv` then separates likely scanned/image-based PDFs, PDFs
whose text layer was not captured by the previous extractor, short native text,
and PDFs needing visual/manual review. The classifications are triage hints, not
validated content recovery. Original attachments remain untouched. **Do not
publish issue-position rates until the OCR queue has been adjudicated.**

## 2026-10-20 full-corpus audit: OCR recovery gate

The locally supplied corrected v0.1 audit snapshot shows 3,231 indexed filings, 3,029 with nonempty **substantive** text after generated headings are removed, 16 exact normalized-text duplicate clusters (71 filings) and 194 PDFs flagged with <=100 extracted characters. Independent page-level triage inspected all 435 pages and found 193 image-bearing/no-native-text PDFs and one PDF lacking both a text layer and detected raster images. The *images* in these PDFs are candidates for OCR, not proof of the documents' final semantic content. The observed 201 substantive-text gaps and 194 OCR flags may overlap; use `scripts/coverage_diagnostics.py` to reconcile them before interpreting the denominator.

### Local, resumable OCR with source preservation

After `python3 scripts/pdf_deep_audit.py` and `zsh run_first_audit.command`, run:

```bash
python3 scripts/coverage_diagnostics.py --corpus ~/Downloads/fcc_complete_corpus
python3 scripts/recover_pdf_ocr.py --corpus ~/Downloads/fcc_complete_corpus --engine vision --limit 3
# If the 3-file trial succeeds, run the rest:
python3 scripts/recover_pdf_ocr.py --corpus ~/Downloads/fcc_complete_corpus --engine vision
```

Apple Vision runs **on device** through a locally compiled Swift helper; `swiftc` must be available. Alternatively use `--engine tesseract` if the `tesseract` executable is already installed. Both backends require `pymupdf` (`python3 -m pip install pymupdf`). Output is saved **only** under `analysis_observatory/ocr_recovery`, with source SHA-256, per-page text and OCR evidence, run manifest, and a JSON summary. Completed outputs are hash-verified and skipped on rerun. The original PDFs, the original text extraction, and the canonical combined text remain untouched. OCR candidates must be visually checked and approved before use in substantive analysis.

The local detail tables and OCR contents are sensitive research working files and should not be committed to this public repository. Share only `coverage_diagnostics_summary.json` and `ocr_summary.json` for aggregate progress reviews.

## Remaining 12 PDF extraction discrepancies (2026-10-20)

After full OCR recovery of the original 194 flagged PDFs, the technical gap report isolated 12 additional PDFs with existing source/extraction files but no substantive text in combined analysis. The 13th outstanding record is the separately retained link-only submission `26110077815`. The 12 are not presumed to be blank, scanned, or unimportant.

A **separate, read-only** provenance workflow handles these PDFs:

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 scripts/reconcile_remaining_pdfs.py --corpus ~/Downloads/fcc_complete_corpus
caffeinate -i python3 scripts/recover_pdf_ocr.py --corpus ~/Downloads/fcc_complete_corpus --engine vision --include-remaining-pdfs
python3 scripts/ocr_quality_report.py --corpus ~/Downloads/fcc_complete_corpus
python3 scripts/ocr_review_packet.py --corpus ~/Downloads/fcc_complete_corpus --additional-only
open ~/Downloads/fcc_complete_corpus/analysis_observatory/ocr_recovery/ocr_review_packet_additional_pdfs.html
```

See [remaining PDF gap reconciliation methodology](analysis_methods/remaining_pdf_gap_reconciliation.md). Neither old originals nor canonical combined texts are rewritten; candidate OCR requires manual review before it can be used in substantive findings.

## Reproducible research snapshots and provisional theme analysis

After the 206 PDF OCR candidates were recovered (194 initial and 12 additional),
create an **immutable, source-traceable local research dataset**:

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 scripts/build_research_snapshot.py --corpus ~/Downloads/fcc_complete_corpus --run-id ocr_candidate_v1
```

The snapshot contains **two separate views**, each with a private filing table, original source links, content hashes, and segment-level provenance:

- **Baseline:** ECFS direct text and original extractions for attachments without OCR candidates.
- **OCR-augmented:** the baseline plus integrity-checked OCR candidate text for the 206 recovered PDFs (previous broken extraction is not added a second time).

The augmented view is valuable for exploratory comparisons, **but OCR candidates are not yet human-verified evidence**. No source file, historical extracted text, FCC filing status, or OCR transcript is modified.

To compare themes under the two views:

```bash
python3 -m pip install -r requirements-dashboard.txt
python3 -m erate.topics --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view baseline
python3 -m erate.topics --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view augmented
python3 -m streamlit run app.py -- --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view augmented
```

The model uses seeded TF-IDF/NMF and lexical SVD for exploration, **not** validated sentiment or FCC policy positions. View changes refit the model, so cluster IDs and 2D axes do not align automatically across runs. See [snapshot research methods](analysis_methods/research_snapshot_methodology.md).

**Keep the snapshot folder private on your Mac.** It includes actual filer names and comment texts and is intentionally excluded from the public GitHub repository.

## Comparing the independently fitted topic models (October 2026)

**Do not compare numeric topic IDs directly.** `T01` in baseline and `T01` in augmented are independently fitted components that may describe different language. We match topics using overlap on the *same filing IDs* with one-to-one optimal assignment. This measures descriptive assignment stability, **not semantic truth or policy stances**.

Once both topic models are generated:

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 scripts/compare_topic_views.py --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1
```

Output stays under the local snapshot's `theme_comparison/` directory: `topic_comparison_summary.json` (aggregate coverage, assignment stability, source hashes), `topic_alignment.csv` (one-to-one matching and overlap), `topic_transitions.csv` (cross-tab of shared filings), `ocr_newly_eligible_by_topic.csv` (distribution of newly eligible OCR filings), and `human_theme_review_sample.csv` (FCC filing links for high-scoring examples in each topic and OCR stratum).

The local dashboard's Theme explorer shows this comparison after generating it. No raw text is sent to GitHub. High-scoring examples are not representative, and the model excludes a provisional set of agency-type records. Substantive publication requires independent validation.
