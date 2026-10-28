# Refreshing the FCC E-Rate filing census without corrupting the study

**The published site is a fixed October 20, 2026 research snapshot**, not a live ECFS docket feed. Comments submitted after that date and reply comments may be missing. The reply-comment deadline in the FCC 26-41 proceeding is November 12, 2026. Before treating any chart as the entire proceeding, check FCC ECFS for the associated WC Dockets 26-133, 13-184, 21-93 and 21-455 and review whether each docket belongs in the analysis.

## 1. Retrieve current metadata from FCC ECFS

Use the [official FCC ECFS portal](https://www.fcc.gov/ecfs/) to obtain a new filing metadata list. Record the exact docket filters, received-date range, retrieval time, reply/comment distinction, all pagination or download-plan files, and whether the scope includes cross-docket and subsequently amended filings. This project does not assume that one paginated API response or an unofficial scrape is complete.

An official export or carefully normalized local CSV is acceptable. Prepare one row **per ECFS submission ID**, preserving an ID in `submission_id`, `filing_id` or `id`. Supported optional fields include `date`, `last_modified`, `type`, and an official FCC `source_url`. No individual names, email addresses, or unreviewed comment text are necessary in the metadata input. If a filing appears in multiple docket exports, deduplicate based on its ECFS submission ID with an explicit provenance log before comparison; the tool rejects repeated IDs.

Example:

```csv
filing_id,date,type,last_modified
26110099999,2026-11-06,REPLY,2026-11-06
```

The ID above is **synthetic**, not a claim that such a filing exists.

## 2. Compare with the frozen corpus

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 -m scripts.audit_ecfs_refresh --input ~/Downloads/ecfs_filing_metadata.csv
```

By default the report goes to `private_data/ecfs_refresh_qa/ecfs_metadata_delta.json`, a gitignored path. It includes new filing-ID candidates, metadata changes to review, original ID coverage, and links to FCC filings. **Absent** original IDs are not counted as missing when the export is partial.

Only when you have checked *all* intended dockets, the full period and complete pagination should you opt in to the missing-ID comparison:

```bash
python3 -m scripts.audit_ecfs_refresh \
  --input ~/Downloads/ecfs_filing_metadata.csv --complete-export
```

The report still warns that apparent absences can reflect docket filters, cross-docket submissions or withdrawn/amended filings.

## 3. Verify new source material before extending the analysis

For each newly seen filing: independently open its FCC record, verify docket membership, filing ID and attachment identity, download all attachments, record original file checksum, extract text and document OCR gaps, check whether it is an amendment or a reply referencing another filing, and maintain original-to-new text hash links. Never silently overwrite the old 3,231-record source archive. Make a versioned manifest and record the complete inclusion/exclusion rules, collection time, search queries and codebook version.

Run the model and context checks *against the newly versioned corpus*; regenerate the stakeholder registry and comparison denominator together. The current published claim ledger is tied by SHA-256 to the old source snapshot. A new metadata record on its own must not be counted as endorsing an argument, classified as an industry source, or included in a machine frequency.

This refresh utility intentionally uses a user-supplied local export; it does **not** claim access to FCC API credentials, fetch newly filed attachments, or assert that any post-snapshot comment has been collected.
