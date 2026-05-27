# `faithful/` — citation check (pure functions)

This package contains a set of **zero-dependency pure functions** (standard
library `re` + `unicodedata` only) used for the CLI's built-in **citation
check**. No database, no cron, no LLM, no network — strings in, verdict dicts
out.

- Modules: `citation_utils.py`, `section_segmenter.py`, `verifier.py`
- The CLI calls only two functions: `verifier.check_wrong_doc_identity` and
  `verifier.check_fake_quote`.

## ⚠️ This is a vendored snapshot with unused internals

This directory is a **snapshot** copied from an internal codebase. It includes
more functions than the CLI uses — `verifier.py` also defines
`check_party_as_court`, `check_verdict_flip`, and `run_all_checks`, and
`section_segmenter.py` carries a fairly heavy role-segmentation machinery. **The
CLI does not call any of those.**

Their presence does **not** mean the CLI performs semantic / holding-level
verification. They are experimental checks that need evidence spans and semantic
judgement; the CLI deliberately exposes only the two bundle-level checks below.
A future release may trim these unused internals down to citation utils +
quote-presence. Do not read the file listing as a feature list.

## What the CLI actually checks (bundle-level, best-effort)

Given an AI-generated answer and the retrieved bundle, it flags:

1. **citation_no_doc / wrong_doc_identity** — a cited case number that is not in
   the retrieved bundle, or whose court/year/case-type/number key does not match
   the judgment it claims to be.
2. **bundle quote-presence** — a verbatim "the court said …" quote that does not
   appear ANYWHERE in the bundle's text. This is a narrow, pattern-based string
   match across the whole bundle; it does NOT prove a quote came from the
   specific judgment the answer attributes it to.

Each check returns `pass` / `needs_review` / `fail`, and is conservative: when
in doubt it returns `needs_review` rather than `fail`.

## What it does NOT check

This is **not** a semantic faithfulness verifier. It cannot tell whether:

- the model read the court's reasoning correctly;
- a litigant's argument was wrongly presented as the court's holding;
- incidental discussion was treated as the core holding;
- a paraphrased proposition is actually supported by the judgment.

Those require reading the full judgment — which is why the CLI ships reasoning
text excerpts in its bundle and instructs downstream models to verify before
concluding. Treat a `pass` as "the citation's identity checks out", not "the
legal reasoning is correct".
