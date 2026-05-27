# `faithful/` — citation check (pure functions)

This package contains a set of **zero-dependency pure functions** (standard
library `re` + `unicodedata` only) used for the CLI's built-in **citation
check**. No database, no cron, no LLM, no network — strings in, verdict dicts
out.

- Modules: `citation_utils.py`, `section_segmenter.py`, `verifier.py`
- Entry point: `verifier.run_all_checks(...)`

## What it can check (bundle-level, best-effort)

Given an AI-generated answer and the retrieved judgments, it flags:

1. **citation_no_doc / wrong_doc_identity** — a cited case number that is not in
   the retrieved bundle, or whose court/year/case-type/number key does not match
   the judgment it claims to be.
2. **fake_quote** — a verbatim "the court said …" quote that does not appear in
   the retrieved judgment's reasoning text. This is a narrow, pattern-based
   string check, not a semantic one.

Each check returns `pass` / `needs_review` / `fail`, and is conservative: when
in doubt it returns `needs_review` rather than `fail`.

## What it does NOT check

This is **not** a semantic faithfulness verifier. It cannot tell whether:

- the model read the court's reasoning correctly;
- a litigant's argument was wrongly presented as the court's holding;
- incidental discussion was treated as the core holding;
- a paraphrased proposition is actually supported by the judgment.

Those require reading the full judgment — which is why the CLI ships the full
text in its bundle and instructs downstream models to verify before concluding.
Treat a `pass` as "the citation's identity checks out", not "the legal reasoning
is correct".
