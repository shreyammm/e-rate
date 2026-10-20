# FCC E-Rate Public Comment Observatory

An auditable, research-grade project to map **who participates, what they say, which issues they discuss, and how repeated submissions affect the interpretation of FCC E-Rate public comments**.

**Current implementation (v0.1):** read-only corpus inventory, SHA-256 attachment audit, short/possibly-scanned-PDF queue, exact and candidate near-duplicate detection, conservative filer concentration metrics, auditable manual coding templates, and an interactive local dashboard. **Not yet implemented/validated:** an exhaustive OCR re-extraction, verified filer identity resolution, issue-specific sentiment/stance classification, theme embeddings, or deployed public site. No fabricated results.

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
