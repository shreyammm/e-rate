## Automated free LLM analysis — separate exploratory research lane

An **additional** LLM census has been installed alongside (not in place of) the existing audit, topic-modeling, human-review, and public-data methods. [Open the separate LLM explorer](docs/llm.html) and read [the methodology](analysis_methods/llm_census_methodology.md).

- **Free inference:** scheduled GitHub Actions jobs run the US-developed, Apache-2.0 open-source `granite4.2:3b` model through Ollama on standard public-repository runners (no paid API key). Jobs batch 100 filings at a time, checkpoint results and resume; runtime limits and runner availability may prevent all filings from finishing immediately.
- **Per-filing questions:** provision-specific requested actions and stances, verbatim evidence, arguments and rationale, stakeholder role grounded in comment text, exact-duplicate-weighted counts, issue co-occurrences, and corpus coverage.
- **Auditability:** every accepted quote must occur in the source excerpt at its recorded character offset. OCR-candidate uncertainty, conflicting stances, duplicates, missing texts, model/codebook versions, and unmatched claims are tracked. These are **machine-generated exploratory hypotheses**, never certified survey estimates or manually validated positions.
- **Automatic cadence:** once `data/fcc_corpus/filings.jsonl` or verified `data/fcc_corpus/shards/filings-*.jsonl.gz` files exist in GitHub, [the scheduled workflow](.github/workflows/llm-census.yml) checks for remaining filings six times daily and writes the separate `data/llm_census/` and `docs/data/llm_exploratory.json` outputs. Do not copy this machine output into human-reviewed records.

**Source upload status (October 20, 2026):** The 3,231-filing, 3,230-text OCR-augmented source archive has been recovered from the researcher's previously shared files and verified against its research inventory. A GitHub-ready package containing twelve checksum-verified gzip JSONL shards has been prepared externally. **The corpus has not yet been pushed into this repository**, and no claim is made that the full LLM census has executed. Once `data/fcc_corpus/manifest.json` and `data/fcc_corpus/shards/filings-*.jsonl.gz` are committed, the existing Granite workflow can load and incrementally analyze the 3,231 filing records. The legacy single-file exporter remains available in `scripts/export_llm_corpus.py`.


## Public website: GitHub Pages (not localhost or hosted Streamlit)

The long-term dashboard is a static site in [`docs/`](docs/) powered by selectively published, **source-validated** aggregate JSON. It uses no Python server, Streamlit account or browser API keys. The older `app.py` is an internal prototype, not the planned public product.

To activate GitHub Pages once the code is merged: open this repository's **Settings → Pages**, under **Build and deployment** choose **Deploy from a branch**, select `main` and `/docs`, then Save. The eventual address is expected to be `https://shreyammm.github.io/e-rate/` **after** GitHub successfully publishes it. No validation data or raw filing texts are published automatically.

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

Individual-level outputs (including names) and the original corpus belong **outside the public Git repo**. `.gitignore` prevents common accidental uploads. The repo does not require any FCC API key, and you should never commit that key or private contact data.

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

No personal filing data is committed. When run on the owner's local corpus the tools compute figures from that snapshot, rather than shipping precomputed, stale or invented charts.

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
