# Incremental build plan

One page. Each increment is independently runnable and carries a test scenario that decides
whether it is done. Written against `docs/prd.md` and `docs/adr.md`.

## Increment 1 — Ingest: make the corpus readable

Render every page and recover its text, by OCR where there is no text layer. Store one record per
page with its file identity, page number and rendered image. Folder names are not recorded.

**Command:** `uv run python -m src.ctrlf.ingest`

**Test scenario.** Run over `data/`. Expect 226 page records across 19 documents. At most 5% of
pages may come back with empty text. Spot-check one known page: the 2023 property policy page 1
must contain the debris removal sublimit of 7 000 000 EUR, because that figure was verified by eye
against the rendered page before OCR was chosen.

## Increment 2 — Extract: one structured record per document

For each document, read the header for insured, policy number and period. For each of the three
questions, sweep for multilingual hints, then have the local model confirm or reject each candidate
page and pull out the figures. Evidence is a verbatim quote plus its page number.

**Command:** `uv run python -m src.ctrlf.extract`

**Test scenario.** Expect 19 records. Every record has a non-empty `policy_no` or an explicit
failure recorded. Every finding marked `applies` carries at least one evidence quote with a page
number. No finding may be marked `applies` with zero evidence.

## Increment 3 — Score: prove it rather than assert it

Compare predictions against the customer's folder labels and report precision, recall and the
specific documents that were missed or wrongly included.

**Command:** `uv run python -m src.ctrlf.eval`

**Test scenario.** Offshore must reach precision 1.00 and recall 1.00 against the five documents in
the offshore folder: no misses and no false positives. This is the PRD's stated bar. Excess auto
and layer report their numbers without a required threshold. The command must name every false
positive and false negative by document, so failures are actionable rather than a score.

## Increment 4 — App: the interface a judge uses

Pick one of the three questions, see the matching policies with insured, policy number, period and
the figures the question asks for. Every row opens to its evidence quote, page number and the
rendered page image. The measured precision and recall sit beside the results.

**Command:** `.\run.ps1`

**Test scenario.** From a clean clone, one command builds everything missing and opens the app.
All three questions render without error. At least one row opens to a page image that visibly
contains the quoted text. The score panel shows the offshore result.

## Increment 5 — Grouping (stretch, cut without consequence)

Group layer policies by insured so that policies covering different layers of the same risk appear
together, which is the third part of the customer's question three.

**Test scenario.** Where two layer policies share an insured, they appear under one heading.

## Order and parallelism

One and two are sequential, because two consumes what one produces. Three and four both depend on
two but not on each other, so they were built in parallel. Five depends on four.
