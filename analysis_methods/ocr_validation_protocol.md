# OCR recovery and validation protocol

This workflow uses OCR candidates **without changing** original FCC attachments, extracted source text, or the manifest. The first 3-document Apple Vision pilot (2026-10-20) finished with nonempty recognized text and no reported errors; this is **not** a measured accuracy score.

## Run

From the repository folder after `git pull --ff-only`:

```bash
cd ~/Downloads/e-rate
caffeinate -i python3 scripts/recover_pdf_ocr.py --corpus ~/Downloads/fcc_complete_corpus --engine vision
python3 scripts/ocr_quality_report.py --corpus ~/Downloads/fcc_complete_corpus
```

The OCR runner resumes previously completed files only if original and OCR evidence hashes still match. Do not use `--force` unless deliberately rerunning an OCR candidate; it is not necessary for resuming.

## Outputs (kept on your Mac)

`fcc_complete_corpus/analysis_observatory/ocr_recovery/`:

- `run_manifest.csv` — each document's status, page counts, source link, original SHA-256 and text/evidence paths
- `text/<submission>_<number>.txt` — OCR candidate transcript; not canonical text
- `evidence/<submission>_<number>.json` — page-level OCR lines, confidence, original SHA-256 and OCR text hash
- `ocr_summary.json` — runtime summary for the selected/full OCR queue
- `ocr_qc_documents.csv` — independently checked original and evidence hashes, line confidence, empty pages, prioritized flags
- `ocr_qc_summary.json` — aggregate quality findings
- `ocr_review_sample_generated.csv` — deterministic review list with source and transcript paths, generated afresh each run

Do **not** write human adjudications into the generated sample file; it is overwritten by the next report run. Maintain a separate `human_ocr_adjudications.csv` with the filing ID, document number, reviewer, reviewed page range, whether OCR matches the scanned original, corrections, confidence/limitations and date.

## Manual spot check

For each document in the generated sample, open the original PDF in Preview and the OCR candidate text in TextEdit. Compare dates, names, numeric claims, negations, policy positions, and reading order, not just whether words are present. Check **every page** for short documents; review selected pages including the first and last for long ones. Correctly recognized headers do not prove substantive text was fully captured.

```bash
open ~/Downloads/fcc_complete_corpus/original_documents/<submission>_<number>.pdf
open -a TextEdit ~/Downloads/fcc_complete_corpus/analysis_observatory/ocr_recovery/text/<submission>_<number>.txt
```

## Research integrity

- Apple Vision confidence is a recognition heuristic, **not a measured transcription-accuracy rate**.
- All staged OCR remains unverified until visually checked; a completed OCR row does not imply reliable text.
- Do not overwrite PDFs, original extracted text, or filing statuses to make aggregate text coverage appear better.
- Pilot/full-queue metrics and manual-review denominators must be reported separately.
- The independent coverage audit found 202 filings without substantive existing text: 189 have an OCR-flagged PDF; 12 have no flagged PDF; and one has a missing combined-text file. Handle the other 13 individually.
- The 194 flagged PDF attachments occur across 193 filings, including four filings that already have some text; OCR may add missing attached content even where a filing is otherwise readable.
- Once quality is validated, create a **versioned analysis input view** that assembles direct text, original extraction and human-approved OCR while preserving per-attachment provenance; never silently overwrite canonical originals.
- Keep the individual-level OCR transcript, filing names and any contact information out of the public GitHub repository.
