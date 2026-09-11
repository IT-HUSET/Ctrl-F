# Ctrl-F

Natural-language search and analysis over a large, heterogeneous document corpus. Ask a question in
plain language, get an answer with citations back to the source documents.

## The problem

IF Industri holds roughly 200 million documents across many formats, structures and layouts. The
knowledge is in there, but it is hard to find and harder to analyse. The metadata that exists is not
sufficient, so any solution has to work from the documents' actual content.

The case as handed to the team is in `docs/case.md` (Swedish). What the team committed to building
today is in `docs/prd.md`. The customer's own questions are in `docs/Use cases.docx`.

## What it does today

- **Answers three portfolio questions** taken verbatim from the customer: which policies cover
  offshore risk, which carry US excess auto cover and at what attachment point and limit, and which
  insure a layer of a risk. Each answer is a list of policies with the evidence passage, its page
  number, and the rendered page image behind it.
- **Searches every page** by keyword, by meaning, or both. Semantic matching is multilingual, so an
  English query reaches a Swedish, Norwegian or Finnish passage sharing none of its words. The local
  model writes a short answer from the retrieved pages and cites them.
- **Scores itself.** Precision and recall per question are shown next to the results, measured
  against the customer's own document folders, which the pipeline never sees.

The source PDFs have no text layer: their glyphs are flattened to vector outlines, so 208 of 226
pages yield nothing to any PDF parser. Everything above rests on an OCR pass that makes them
readable in the first place.

## Status

Working prototype, built in a one-day Caseathon over a 19-document sample corpus.

| Question | Precision | Recall |
| --- | --- | --- |
| Offshore | 0.83 | 1.00 |
| Excess auto, US | 1.00 | 0.50 |
| Layer | 0.80 | 1.00 |

Both results the score counts as wrong were read by hand and are correct: they match a question
they were not filed under, because the folders are a search set rather than an answer key. There
are no unexplained false positives. Scaling, authentication, deployment and visual polish are
deliberately deferred.

## Running it

```powershell
.
un.ps1
```

That installs dependencies, starts the local model server, OCRs the corpus, extracts one record per
document, prints the score and opens the app. The first run takes a while because of the OCR pass;
after that everything is cached under `cache/` and startup is immediate. Use `.
un.ps1 -Rebuild`
to redo it from scratch.

Prerequisites are [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com) with two
models pulled:

```
ollama pull qwen2.5:7b-instruct   # reading and answering
ollama pull bge-m3                # multilingual embeddings for semantic search
```

Put the source PDFs in `data/`. Nothing else is installed outside the Python environment, and
nothing leaves the machine at run time. OCR runs through RapidOCR, which ships its own models and
needs no system binary.

## Constraints

- **Local data only.** No external APIs at runtime.
- **Sample documents only.** No real IF Industri material is committed to this repository.
- **Answers cite their sources.** A result that cannot be traced back to a document is a defect.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Product and process documents, one page each |
| `docs/prd.md` | What the team is building today, one page |
| `docs/case.md` | The case brief as handed to the team |
| `docs/Use cases.docx` | The customer's three questions and what a bad answer looks like |
| `AGENTS.md` | Rules for AI agents working in this repository |
| `CLAUDE.md` | Claude Code guidance: event terms, constraints, workflow |
