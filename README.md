# Ctrl-F

Natural-language search and analysis over a large, heterogeneous document corpus. Ask a question in
plain language, get an answer with citations back to the source documents.

## The problem

IF Industri holds roughly 200 million documents across many formats, structures and layouts. The
knowledge is in there, but it is hard to find and harder to analyse. The metadata that exists is not
sufficient, so any solution has to work from the documents' actual content.

The case as handed to the team is in `docs/case.md` (Swedish). What the team committed to building
today is in `docs/prd.md`. The customer's own questions are in `docs/Use cases.docx`.

## What it should do

- Search document content in plain language.
- Surface relationships and recurring patterns across documents.
- Run analyses and aggregations over the corpus.
- Handle mixed formats and structures.
- Present results and their sources clearly and reliably.
- Stay simple to use.

## Status

Early prototype, built in a one-day Caseathon. No stack chosen yet and nothing runnable so far.

Today's scope is a demonstrable prototype over a small sample corpus, not the full
200-million-document system. Scaling, authentication, deployment and visual polish are deliberately
deferred.

## Running it

```powershell
.un.ps1
```

That installs dependencies, starts the local model server, OCRs the corpus, extracts one record per
document, prints the score and opens the app. The first run takes a while because of the OCR pass;
after that everything is cached under `cache/` and startup is immediate. Use `.un.ps1 -Rebuild`
to redo it from scratch.

Prerequisites are [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com) with the
`qwen2.5:7b-instruct` model pulled. Put the source PDFs in `data/`. Nothing else is installed
outside the Python environment, and nothing leaves the machine at run time.

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
