## Argument-level research: what people claim and why

An FCC filing can advance **multiple arguments about the same provision**. For instance, a district could oppose reduced discounts because it predicts affordability problems and also question the FCC's statutory authority. One filing/provision stance row must NOT become multiple individual commenters simply because it has multiple rationales.

Use `scripts/validate_argument_claims.py` to check a separately prepared human-coded argument CSV. Each argument needs a unique ID, `submission_id`, `provision_id`, `claim_kind`, `argument_summary`, `evidence_quote`, `evidence_type`, `evidence_independently_verified` (`no` or `yes`), `coder_id`, and `review_status=manual_reviewed` or `adjudicated`. For predictive arguments add the causal mechanism and consequence, for legal claims the statute/case, for empirical claims the cited study/source. `evidence_independently_verified=yes` requires a reference. **Quoting a study is not the same as independently validating it.**

The source-exact quote must be unique in the immutable snapshot text. This is a source-transcription check, not a determination that the stated claim is true. For OCR candidates, reviewers should also visually check the original PDF, especially negation, monetary figures and other pivotal details.

```bash
cd ~/Downloads/e-rate
python3 -m scripts.validate_argument_claims --corpus ~/Downloads/fcc_complete_corpus --annotations ~/Downloads/fcc_argument_human_reviews.csv
python3 -m scripts.export_public_site_data --corpus ~/Downloads/fcc_complete_corpus
```

Output in local `policy_analysis_augmented/` includes `validated_argument_claims.csv`, `argument_validation_errors.csv` and `argument_validation_summary.json`. The public preview (not auto-published) can display aggregate argument kinds under each FCC provision alongside counts of reviewed filing/provision stances. **The two counting units are deliberately separate.**

### Provide source material for deeper qualitative coding

The assistant cannot directly read the full original corpus on the user's Mac. To analyze actual examples without sending thousands of original PDFs, run:

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 -m scripts.prepare_policy_analysis --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --view augmented
python3 -m scripts.package_policy_excerpt_sample --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1 --per-provision 4
```

This prepares `~/Downloads/FCC_POLICY_EVIDENCE_SAMPLE.zip`, covering up to four keyword-matched filings per proposal with a limited passage, source ID and FCC link. Basic email and phone redaction is attempted; **read the excerpts before sharing** because names or other personal details may remain. The sample is intentionally NOT representative, and a keyword hit alone does not imply support. Upload that ZIP into this conversation so the assistant can inspect the actual passages, identify stances, reasons, alternatives and unresolved ambiguities, and help expand source-verified coding. Do not commit the ZIP or unreviewed snippets to public GitHub.
