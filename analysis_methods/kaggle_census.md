# Free Kaggle GPU census (additive)

This lane uses local OpenAI gpt-oss 20B (Apache 2.0), with no paid API or cloud inference endpoint. It writes only data/llm_census_kaggle and separate website data. The IBM CPU/Mac workflows, OCR, source snapshots, human-reviewed tables and Ask the Corpus remain intact.

The source manifest must contain exactly 3,231 records, including 3,230 readable texts. Source-shard and per-text hashes are verified before inference. The GPU model selects numbered overlapping source spans for citations. Saved evidence is copied directly from those spans, then checked against the original filing and character offset. This prevents generated wording from being passed off as quotations; it does not independently validate the model's interpretation. Checkpoints are atomic and resumable per model window; exact-byte duplicate reuse retains separate filing identities.

Scope follows the existing deadline-aware window selector: short filings are read in full; long appendices are scanned to select high-signal author-advocacy windows. Each completed file records semantic_scope, source_windows_total and source_windows_model_analyzed. Completion of all readable filings does not mean semantic reading of every appendix word. The machine explorer exposes both scope counts. These outputs are unvalidated model interpretations.

Kaggle saved sessions stop safely before the 12-hour platform limit (620 inference minutes plus setup). Enable Files only persistence. The notebook restores the latest source-validated GPU checkpoints from GitHub and/or its prior saved output. Public sharing of the Kaggle notebook is pending explicit approval; until then, the public GitHub downloader cannot access the private outputs. A single compressed JSONL checkpoint bundle is saved alongside a summary and provenance. Models live under /kaggle/temp, keeping model weights out of saved outputs.

The scheduled kaggle-census-import GitHub workflow downloads the explicit checkpoint bundle from the public Kaggle notebook with KaggleHub, revalidates it against the immutable source and publishes separate GPU summaries, claims and findings. No GitHub token is stored in Kaggle, and no Kaggle token is committed to GitHub. Existing research outputs are not overwritten.

The 24–40-hour goal is a target, dependent on observed inference throughput, session availability and the account's remaining free GPU quota. A started job is not completed analysis. Inspect the actual completed_filings and semantic-scope counts.

