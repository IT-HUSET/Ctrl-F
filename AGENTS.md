# AGENTS.md

Rules for AI agents working in this repository, whatever the tool. Read "Non-negotiables" first.

## Project

Ctrl-F turns a large, heterogeneous document corpus into a usable knowledge source. Users ask
questions in plain language and get answers with citations back to the source documents.
Case: `docs/case.md` (Swedish). Committed scope: `docs/prd.md`. Customer questions:
`docs/Use cases.docx`. Today's target is a working prototype, not a system.

## Non-negotiables

1. **Local data only, no external APIs at runtime.** Indexing and inference run locally against a
   sample corpus. If a task appears to need a hosted endpoint, stop and raise it rather than adding one.
2. **One command to run.** Starting the prototype from a clean clone takes a single documented
   command, recorded in `README.md`. If a change breaks that, fix it before moving on.
3. **Every answer cites its sources.** A result the user cannot trace back to a document is a defect,
   not a rough edge. Citations are the product, not decoration.
4. **Never claim something works without running it.** Show the command and its real output.
5. **Sample data only.** No real IF Industri documents and no secrets in the repository.

## How work flows

Artifacts descend in this order. Do not open a level until the one above it is agreed:

`docs/case.md` → `docs/prd.md` → ADR → build plan → code

Before producing a plan, before producing a spec, and before implementing against one:

- Interview me relentlessly about every aspect of this plan until we reach a shared understanding.
- Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.
- For each question, provide your recommended answer.
- Ask the questions one at a time.
- If a question can be answered by exploring the codebase, explore the codebase instead.

Timebox the interview to the build window. Ask what changes today's build; record the rest as
deferred in writing rather than resolving it now.

## Increments

- One increment per agent session. Start a fresh session for the next increment.
- Increments are built in parallel by different people. Stay inside your increment's files. If you
  must touch shared code, say so before you do.
- An increment is done when its test scenario passes **and** the prototype still starts with one command.
- Commit at the end of each increment, with a message saying what changed and why.

## Verification

- Every increment carries a test scenario in the build plan. Run it and show the output.
- Review before the demo, not after. Issues found before showtime count; issues found after do not.
- Log friction as it happens: what fought you, roughly what it cost, what would have prevented it.
  A log written from memory at 17:30 is worth little.

## Conventions

- Product and process documents live in `docs/`, one page each.
- The case brief is Swedish; the documents are Swedish, Norwegian, Finnish and English, often
  mixed within one page. Code, identifiers, technical docs and commits are English.
- Prefer the shortest path to something demonstrable end to end over completeness or polish.
- **Stage explicit paths, never `git add -A`.** `data/` and `cache/` hold real policy documents and
  their extracted text. A blanket add put a customer-internal file on the public remote once.
- **OCR runs words together.** Any pattern matched against document text must also be matched
  against a de-spaced copy. Word boundaries have silently hidden real evidence twice.
- **Nothing loads from outside the machine, including the look.** Fonts are embedded from
  `assets/fonts/`, never linked from a CDN, and Streamlit's usage statistics stay off.

## Out of scope today

Scaling to 200 million documents. Authentication. Deployment. Record these as deferred
decisions; do not build them.

## Deliverables due 18:00

A one-page PRD. Architecture and design decisions. An incremental build plan with test scenarios.
This file, under 100 lines. A working prototype runnable with one command. A friction log and
review findings.

Scored on: the demo matching the PRD, increments built in parallel, review finding issues before
the demo, and one automation identified for the next iteration.
