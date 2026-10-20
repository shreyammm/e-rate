# Remaining PDF extraction-gap reconciliation

The October 20, 2026 audit isolated **13** filings without existing substantive text outside the original PDF OCR queue. The technical triage distinguishes **12 filings with existing local PDF originals and attachment extraction files** and **one source that contains only a temporary `blob:` link**. The latter is FCC filing `26110077815`, which must remain in the filing inventory with an explicit unresolvable-substantive-text limitation, not falsely counted as a substantive comment.

The 12 PDF filenames and their source links come from `non_ocr_gap_triage.csv`; the earlier document manifest reports 103–275 attachment-text characters, yet the combined-text analysis found no substantive text. **This is a discrepancy**—it does not establish that those PDFs are scanned, that the previous extracted characters are trustworthy, or that the PDFs have no opinions.

## Read-only recovery workflow on Mac

All commands start in your local `~/Downloads/e-rate` Git repository:

```bash
cd ~/Downloads/e-rate
git pull --ff-only

# Inspect the original PDF text layers and compare against saved extraction.
python3 scripts/reconcile_remaining_pdfs.py --corpus ~/Downloads/fcc_complete_corpus

# Resume the 194 previous successes and OCR the 12 additionally inspected PDFs.
caffeinate -i python3 scripts/recover_pdf_ocr.py \
  --corpus ~/Downloads/fcc_complete_corpus \
  --engine vision \
  --include-remaining-pdfs

# Verify hashes, page coverage, recognized lines, empty pages and review flags.
python3 scripts/ocr_quality_report.py --corpus ~/Downloads/fcc_complete_corpus

# Review original PDF images alongside OCR transcripts for these 12 documents.
python3 scripts/ocr_review_packet.py \
  --corpus ~/Downloads/fcc_complete_corpus \
  --additional-only

open ~/Downloads/fcc_complete_corpus/analysis_observatory/ocr_recovery/ocr_review_packet_additional_pdfs.html
```

The staged reconciliation output stays under `analysis_observatory/additional_recovery/`:

- `additional_pdf_summary.json`: aggregate counts and classifications for 12 PDFs.
- `additional_pdf_diagnostics.csv`: one row per source PDF, original hash, existing extracted character count, native PDF text layer counts and page/image coverage.
- `additional_pdf_review_queue.csv`: exactly the independently audited additional OCR candidates.
- `native_text/*.txt` and `native_evidence/*.json`: optional native-text candidates and source hashes, where available.

The OCR candidate outputs remain under `analysis_observatory/ocr_recovery/`; no original PDF, historical extracted text, filing manifest, or canonical combined text is modified.

## Acceptance rules

1. Confirm the 12 source PDFs match the original manifest hashes and correspond to the correct filing IDs.
2. Run OCR on each additional PDF, even where its native text layer seems useful. Independently compare native-layer and OCR outputs for conflicts.
3. Review the 12 scanned pages versus OCR transcripts for negations, amounts, positions, names and omissions; export the offline review CSV. If errors are found, preserve both the machine output and a separate corrected human-reviewed version.
4. Keep the one link-only filing with `no_substantive_text`; do not manufacture a recovered comment.
5. **Do not add staged or unverified OCR candidates automatically to stance calculations.** Build a versioned analysis input with per-document provenance and human-review status. Report how much text comes from source ECFS direct text, native PDF extraction, staged OCR, and human corrections, and maintain an abstention option.

The `NPRM` submission-type value on filing `26110076984` accompanies a document titled `OLH FCC Letter.pdf`. Submission-type metadata is not sufficient to conclude it is an FCC-issued agency notice; manual organization/role verification is needed before excluding records from public-comment analysis.

## Share the next review results safely

Only send aggregate reports by default:

```bash
cd ~/Downloads/fcc_complete_corpus/analysis_observatory
zip -j ~/Downloads/FCC_FINAL_GAPS_TECHNICAL_REPORT.zip \
  additional_recovery/additional_pdf_summary.json \
  ocr_recovery/ocr_summary.json \
  ocr_recovery/ocr_qc_summary.json
open -R ~/Downloads/FCC_FINAL_GAPS_TECHNICAL_REPORT.zip
```

The offline review HTML embeds original document images and recognized texts; **never commit it to public GitHub**. The export CSV containing review decisions may be shared directly if desired.
