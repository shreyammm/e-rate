# Data-first GitHub Pages dashboard — source, measures and publishing

The site in `docs/` is a **data-first observatory**, not a landing page. Views: Overview, Positions & alignment, Arguments, Commenter types, Corpus explorer, Methods. It is hosted on GitHub Pages, not Streamlit.

## Main measures (Oct 20, 2026 snapshot)

- 3,231 ECFS filing records / 3,230 with substantive text, including candidate OCR. These are NOT verified distinct commenters.
- Broad issue-mention counts come from term presence over **all 3,230 available augmented filing texts**, counted once per filing per category. A document can mention several topics, quote its opponents or be largely unrelated to a proposal; **mentions are not positions**.
- Thirteen mutually exclusive, provisional commenter categories are inferred from the full ECFS filer field AND self-identification within complete source text; unresolved role and unclear representative capacity are retained as explicit categories. They are not independently verified unique people or organizations.
- 19 source-exact, first-pass organizational position examples are available as an exploratory comparison and a sparse organization × proposal alignment matrix. They are illustrative, not a random sample or independently dual-coded census.
- The completed census read **all 211,756,379 characters** and checked **93,699 filing/provision pairs**, with 14 separately reported argument-language families. There is **no inference from a 27-excerpt or any other subsample**. Explicit preservation wording is still a text-retrieval signal, not a confirmed opinion or a validated sentiment classifier; automatic positive-elimination phrases were found to be falsely triggered by commenters quoting the FCC's own question.
- A single exact filer-name string appears on 277 ECFS records and accounts for 80.3% of extracted characters; full-text length must not weight each person's policy views.

## Corpus explorer

The standalone public index is a compact, privacy-minimized derivative generated **locally** from the user's full corpus. The newer reconciled role-code layer covers every record, replacing the original filer-field-only grouping. Each row has the FCC filing ID, filing date, ECFS submission type, one provisional filer-field affiliation category, bitmask of the nine issue-mention categories, an OCR flag, a duplicate-text count, and a recognizable organization label only when that can be safely displayed. It intentionally does not publish the original full text, raw individual filer-name fields, emails, or phone numbers. Clicking a filing links to its official FCC ECFS record.

**To make all 3,231 records browseable on GitHub Pages**, after merging the dashboard branch, run:

```bash
cd ~/Downloads/e-rate
git pull --ff-only
python3 -m scripts.export_static_corpus_index --corpus ~/Downloads/fcc_complete_corpus --snapshot-id ocr_candidate_v1
git add docs/data/corpus_index.json
git commit -m "Publish privacy-minimized FCC corpus index"
git push
```

The exporter checks source-text SHA-256, 3,231 IDs, all nine previously audited issue totals and eight affiliation-group totals before writing. If local data no longer agrees with the published aggregate, it raises an exception instead of silently misrepresenting the source. Generated JSON may include recognizable organizational names (not bulk personal-name fields); a human privacy review remains advisable before pushing.

Without the generated file, the site provides a clearly labeled **limited preview explorer** of the organizational example filings; it does NOT falsely claim full corpus indexing.

## Next valid inference gates

To publish an estimated proportion of filings supporting/opposing each specific FCC provision, we must **actually classify the full texts or a defensibly drawn sample** and evaluate false-positive and false-negative rates. Exact term matching and unsupervised NMF topic labels cannot do this, especially when filings quote the FCC's proposal. The provision codebook, source-exact candidate retrieval, sample review packet, and evidence validation tools already exist, but the ~3,200 individual policy positions are **not yet human adjudicated**. Report separate counts by filing, verified filer entities (once identity reviewed), exact unique texts, and candidate template families. A first-pass organizational coalition table is not a substitute for population-wide position counts.

See [the exhaustive, no-sampling census methodology](full_corpus_census_20261020.md) for updated counts and limitations.
