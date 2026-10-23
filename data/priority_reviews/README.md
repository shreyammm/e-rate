# Independently reviewed priority-position exports

This directory is for exported CSV files from the [Positions & Coalitions reviewer](https://shreyammm.github.io/e-rate/positions.html). The first-pass dataset is **not** a source of validated stances or proven misconduct.

**To produce credible counts:**

1. Two reviewers independently open the original full FCC filing and record all endorsed positions under each of the four axes, including an exact source quote and explanation.
2. Export their complete one-reviewer CSV files from the website and name them separately, such as \`reviewer_a.csv\` and \`reviewer_b.csv\`. Reviewers should use different reviewer IDs.
3. Add these CSV exports to this directory. The GitHub workflow \`priority-review-aggregation.yml\` runs the strict two-reviewer agreement rules and generates \`docs/data/kaggle/priority_adjudicated_positions.json\`.
4. Disagreements are withheld and sent for manual resolution. A single review is **never** counted as validated. Agreement counts are only for the fully double-reviewed subset, not projected onto all 3,230 readable filings.

Important: the reviewer tool uses browser-local storage; export your decisions before clearing browser data or switching devices. Recode original source context, never the Kaggle \`support\`/\`oppose\` label. Misuse allegations are **not findings that anyone violated the rules**; distinguish legally ineligible conduct from normative objections to otherwise lawful expenditure.

The codebook is [here](../../analysis_methods/priority_position_codebook.md). Use the separately published stratified audit assignments for probability-based validation, including previously unflagged filings.
