# Architecture and design decisions

One page. Written 2026-09-11 during the Caseathon build window, against `docs/prd.md`.

## Context

Nineteen policy documents, 226 pages, plus one clause image the customer supplied after answering
our questions. Two facts drove almost every decision. The documents have
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
Two themes, picked under Appearance in the sidebar and carried in the URL (`?theme=blackmetal`).
The default, Evergreen, is the demo look: insurance-sector sober, graph-paper grid, KPI tiles with
tabular figures, forest green with navy, and a bar strip shading from navy into green. Streamlit's
base theme is process-wide config, so switching sets those options and reruns; acceptable for one
presenter, wrong for many users. The original build-day look is kept as the second theme:
The look is Norwegian black metal kept legible: monochrome, a generated treeline and moon behind the
content, blackletter only for the logo and headings, typewriter for evidence quotes, and no occult or
runic symbols because this is shown to a customer. A font CDN was ruled out by the local-only rule.
We first served the fonts through Streamlit's static file route, which answered the font URL with a
200 carrying the app's own HTML page, so both faces silently fell back to serif. The fonts are now
embedded in the stylesheet as data URIs, which needs no route and no request.

**11. A document without a policy number is supporting evidence, linked to policies by insured.**
The customer confirmed that some cover is stated only outside the policy document. In this corpus,
US excess auto for `temp.lh.policy.2022.06.08` appears only in a separate clause, which they
supplied as an image. Ingest reads images through the same OCR path as PDFs. Extract marks any
document with no `LP` number as supporting, using content only and never the folder. It links the
document to every policy whose insured it names. Eval and the app then credit the policy and say
the answer came from a related document. Linking ignores generic insured values such as
"INSURED COMPANIES" and the insurer's own name, which redaction leaves behind. The first pass
linked on those and credited an unrelated policy. At scale this becomes a link on policy-number
family and client number, both of which master policies already list.

**12. Rules the model will not hold are enforced in code.**
The customer separates a layer (the band of losses a policy covers) from a deductible (what the
insured retains). With that definition in the prompt, layer recall fell from 1.00 to 0.25. Without
it, the model accepted "limits in excess of deductible" as a layer. The prompt stays short, and
`deductible_only()` rejects a layer quote that mentions a deductible but no layer wording. The
model proposes; code applies the customer's definitions where they can be stated as a rule.
Attachment point and limit are required fields for the two questions that ask for figures. As
optional fields, they came back empty on every record.

## Known weaknesses

Figures for questions two and three are only as good as the OCR of a number, and a misread digit
is a wrong answer by the customer's own definition. Scoring uses folder membership as truth. The
customer confirmed the folders are a search set rather than an answer key, so the score is a proxy.
The model sees short snippets, not whole pages. That is why it still accepts the New Zealand
extension in `temp.lh.policy.2022.06.22` as a layer: the snippet does not show that the amount
belongs to one country. Extraction quality rests on a 7B
model reading OCR output, which is the main thing a larger model would improve. Semantic search is
unscored: we have no labelled relevance judgements, so it is demonstrated rather than measured.
