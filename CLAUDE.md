# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overriding constraint: Caseathon prototype, due today

Event guidelines: https://orange-beach-0e1493b03.7.azurestaticapps.net/caseathon.html

One day, 09:00–18:00. Build phase 13:10–17:00, demo and review 17:00–18:00. Four-person team, two Definers and two Builders. This section outranks the workflow below wherever the two pull in different directions.

### Six deliverables, all due 18:00

1. PRD, one page, problem and requirements. Written: `docs/prd.md`.
2. Architecture and design decisions (ADR).
3. Incremental build plan with test scenarios.
4. `AGENTS.md` rules file, under 100 lines.
5. Working prototype, runnable with **one command**.
6. Friction log and review findings.

### Hard constraints

- **Local data only, no external APIs.** Treat this as binding on the prototype at runtime and plan for a local index over a sample corpus.
- Start a **new AI session for each increment**.
- Read off what the day cost once, at the demo.

### Scored 0–3 on each

Demo aligns with the PRD. Increments built in parallel. Review found issues before the demo. One automation identified for the next iteration.

### Working implications

- Prefer the shortest path to something demonstrable end to end over completeness, polish, or scale. The 200-million-document target is the eventual goal, not today's.
- The PRD, ADR, and build plan are graded artifacts, so they are written files under `docs/`, one page each. Do not collapse them into conversation.
- Keep the interview inside the build window. Ask the questions whose answers change what gets built today, and record the rest as deferred.
- Log friction and shortcuts as they happen. Deliverable 6 and the automation score both depend on having kept that record.

## Current state

This repository is at the pre-implementation stage. It contains no source code, build system, package manifest, or tests yet. The case brief is `docs/case.md`, the customer's three questions are in `docs/Use cases.docx`, and what the team committed to building today is `docs/prd.md`.

- The `.gitignore` is GitHub's Jekyll/GitHub Pages template (`_site/`, `Gemfile.lock`, `/vendor`). It was picked at repo creation and is **not** a signal that the project uses Jekyll or Ruby. Replace it once a tech stack is chosen.
- There are no build, lint, or test commands to run. Update this file with them as soon as the first scaffold lands.

## What is being built (case in `docs/case.md`, written in Swedish)

Ctrl-F is an AI-powered search and analysis solution for **IF Industri**, which holds roughly 200 million documents in many formats and structures. Existing metadata is insufficient, so the solution must understand and process the documents' actual content.

Required capabilities:

1. Natural-language search over document content.
2. Discovery of relationships and recurring patterns across documents.
3. Analyses and aggregations over the corpus.
4. Handling of heterogeneous document formats and structures.
5. Clear, trustworthy presentation of results **with sources/citations**.
6. A simple, easy-to-use interface.

Keep these six requirements in mind when proposing architecture; source attribution and format heterogeneity are first-class constraints, not afterthoughts.

## Spec-driven workflow

Work descends through a hierarchy of artifacts. Each level must be settled before the next one begins, and no level may be skipped:

1. **Product brief** — `docs/case.md` (input) and `docs/prd.md` (what we committed to).
2. **Plan** — decomposition into stories, with dependencies between them made explicit.
3. **Spec** — per-story implementation detail: interfaces, data shapes, acceptance criteria.
4. **Implementation** — code, written only against a spec that is already settled.

### Interview before descending a level

Before producing a plan, before producing a spec, and before implementing against one:

- Interview me relentlessly about every aspect of this plan until we reach a shared understanding.
- Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.
- For each question, provide your recommended answer.
- Ask the questions one at a time.
- If a question can be answered by exploring the codebase, explore the codebase instead.

## Working conventions

- Product and planning documents live under `docs/`. The PRD is the source of truth for scope until a plan or spec supersedes it.
- The case brief is Swedish. The source documents in `data/` are Finnish with English insurance
  terminology. Code, identifiers, technical docs and commits are English unless told otherwise.
