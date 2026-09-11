# Ctrl-F — Product Requirements

One page. Written 2026-09-11 for the Caseathon build window. Input case: `docs/case.md`.
Customer questions: `docs/Use cases.docx`.

## Problem

If Industrial answers portfolio questions by reading policy documents. Questions like "which of
our policies cover offshore risk" have no metadata answer, because the evidence is a phrase buried
in free text, written in any of several languages. Today someone opens fifteen to twenty documents
per question and reads them. The documents make this worse: their text is flattened to vector
outlines, so they are not even searchable with Ctrl-F.

The cost is not just time. An answer that misses policies, or includes wrong ones, is worse than no
answer, because portfolio decisions get made on it.

## User

An underwriter or portfolio analyst who needs to answer a question about the book and must be able
to defend the answer to someone who asks where it came from.

## Scope today

Three questions, taken verbatim from the customer:

1. **Offshore.** Identify policies covering offshore risks or projects.
2. **Excess auto.** Find liability policies with excess auto cover in the United States, and for
   each, the attachment point and limit.
3. **Layers.** Identify policies insuring a layer of a risk, find excess point and limit, and group
   policies insuring different layers of the same risk.

Plus free-text search across every page, added late in the build:

4. **Search.** Type any phrase and get the pages that contain it, with a short answer written by
   the local model citing the pages it used. This is Ctrl-F in the literal sense, and it is the
   capability the product is named after: these PDFs have no text layer, so before this pipeline
   existed they could not be searched at all.

Over the 19-document sample corpus in `data/`: 226 pages, of which 208 carry no text layer.

## What the user does

Opens the app, picks one of the three questions, and gets the list of policies that match. Each row
shows the policy number, the insured, the period, the figures the question asks for, and the passage
the answer came from with its page number. No row appears without that evidence.

## Acceptance criteria

- **Question 1 is exact.** Offshore returns every offshore policy and nothing else, verified against
  the labelled folders. No misses, no false positives.
- **Questions 2 and 3 are best effort**, and every returned row still carries a checkable citation.
- **Nothing is asserted without a citation.** A claim with no traceable passage is a defect.
- **Folder paths are never an input.** The system reads document content only. The folder names are
  ground truth for scoring and must not leak into the index, or the result is circular.
- **One command starts it**, from a clean clone.

## Out of scope today

Scaling beyond the sample corpus. Authentication. Deployment. Formats other than PDF. Visual polish.
Semantic search: retrieval is lexical, so a query has to share wording with the document. Free-text
search was moved into scope during the build and this section updated to match, rather than leaving
the demo showing something the PRD called out of scope.

## Known risks

- **OCR fidelity.** The text is vector outlines in Finnish and English. Question 2 and 3 need exact
  figures, and a misread digit is a wrong answer by the customer's own definition.
- **Ground truth.** Scoring assumes folder membership equals the correct answer. Confirm that a
  `Projects` document is not also offshore before trusting the number.
- **Throughput.** Extraction runs on a local 8 GB card. If a full pass over 19 documents is slow,
  the precompute must start early.
