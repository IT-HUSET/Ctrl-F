# Architecture and design decisions

One page. Written 2026-09-11 during the Caseathon build window, against `docs/prd.md`.

## Context

Nineteen policy documents, 226 pages. Two facts drove almost every decision. The documents have
no text layer, because their glyphs are flattened to vector outlines, so nothing can be parsed
out of them. And the corpus is small, so the usual assumption that you must search before you
can answer does not hold today.

## Decisions

**1. OCR is the ingest path, and it runs through RapidOCR rather than a system binary.**
Two independent PDF parsers returned zero characters on 208 of 226 pages. The pages contain
neither text nor embedded images, only vector drawing operations, which is what flattening
produces. We first reached for Tesseract, which means a system install; the winget install had
not completed after several minutes of a four-hour budget. RapidOCR installs with pip, ships its
own ONNX models, needs no binary and no network at run time. It read a sublimit table correctly
on the first try. Choosing it also made the one-command install honest, since there is now nothing
to install outside the Python environment.

**2. Precompute one record per document. Do not retrieve at query time.**
With nineteen documents, every question can be answered from nineteen structured records built
once, ahead of the demo. Retrieval-augmented search is the right architecture when the corpus is
too large to read exhaustively. It is the wrong architecture today: it adds an index, a similarity
threshold and a failure mode, in exchange for solving a problem we do not have. At real scale the
same extraction runs behind a retrieval stage that shortlists candidates first; the per-document
extraction contract does not change.

**3. Cheap multilingual keyword sweep for recall, local model for precision.**
The customer defines a wrong answer as one that misses real cases or includes false positives.
These pull in opposite directions, so we split them. A regex sweep over Finnish, Swedish and
English hints proposes candidate pages and is tuned for recall, accepting noise. The model then
reads each candidate page and either confirms it with a verbatim quote or rejects it. Neither
stage is trusted alone.

**4. Folder names are ground truth for scoring and are never an input.**
The corpus folders are the customer's own labels. Nothing in the pipeline records which folder a
document came from; `ingest.py` stores only the file identity. `eval.py` reads the folders, and
only to measure precision and recall. Had the folder leaked into the index, the demo would be
circular and would collapse under the first question a judge asked.

**5. Local model: Qwen 2.5 7B Instruct, served by Ollama on localhost.**
It fits in 8 GB of VRAM, handles Finnish alongside English insurance terminology, and supports
constrained JSON output, which removes a class of parsing failures. No request leaves the machine,
which the event requires.

**6. Streamlit for the interface.** Chosen by the team over a static page. Fastest path to
something interactive given the pipeline is already Python.

**7. Parallelise OCR per page, not per document.** One document holds 85 of the 226 pages. Per
document parallelism would have left that one file setting the wall-clock at roughly twenty
minutes. Per page, the work spreads evenly across workers.

**8. Semantic search uses a multilingual embedding model, indexed ahead of time.**
Keyword search only finds wording a query shares with the page, which is a poor fit for a corpus
written in Swedish, Norwegian, Finnish and English at once. We embed every page in overlapping
chunks with `bge-m3`, chosen over the smaller `nomic-embed-text` because it is genuinely
multilingual: an English query for building work retrieves a Norwegian policy that shares none of
its words. 512 chunks index in 49 seconds and the result is cached, so query time is a dot product.
We pulled the smaller model in parallel as a hedge against the larger download not arriving, and the
code selects whichever is installed.

**9. Keyword and semantic results are merged by reciprocal rank, not by score.**
The two produce numbers that are not comparable: one counts term hits, the other is a cosine
similarity. Combining them by rank rather than value avoids inventing a scale, and takes about ten
lines. A page found by both rises to the top, which is the behaviour we want.

**10. The visual theme is CSS injected by the app, with its fonts embedded rather than served.**
The look is Norwegian black metal kept legible: monochrome, a generated treeline and moon behind the
content, blackletter only for the logo and headings, typewriter for evidence quotes, and no occult or
runic symbols because this is shown to a customer. A font CDN was ruled out by the local-only rule.
We first served the fonts through Streamlit's static file route, which answered the font URL with a
200 carrying the app's own HTML page, so both faces silently fell back to serif. The fonts are now
embedded in the stylesheet as data URIs, which needs no route and no request.

## Known weaknesses

Figures for questions two and three are only as good as the OCR of a number, and a misread digit
is a wrong answer by the customer's own definition. Scoring assumes folder membership equals
truth, which is worth confirming before the number is quoted. Extraction quality rests on a 7B
model reading OCR output, which is the main thing a larger model would improve. Semantic search is
unscored: we have no labelled relevance judgements, so it is demonstrated rather than measured.
