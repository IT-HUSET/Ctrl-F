# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

This repository is at the pre-implementation stage. It contains no source code, build system, package manifest, or tests yet. The only substantive content is the product brief in `docs/prd.md`.

- The `.gitignore` is GitHub's Jekyll/GitHub Pages template (`_site/`, `Gemfile.lock`, `/vendor`). It was picked at repo creation and is **not** a signal that the project uses Jekyll or Ruby. Replace it once a tech stack is chosen.
- There are no build, lint, or test commands to run. Update this file with them as soon as the first scaffold lands.

## What is being built (from `docs/prd.md`, written in Swedish)

Ctrl-F is an AI-powered search and analysis solution for **IF Industri**, which holds roughly 200 million documents in many formats and structures. Existing metadata is insufficient, so the solution must understand and process the documents' actual content.

Required capabilities:

1. Natural-language search over document content.
2. Discovery of relationships and recurring patterns across documents.
3. Analyses and aggregations over the corpus.
4. Handling of heterogeneous document formats and structures.
5. Clear, trustworthy presentation of results **with sources/citations**.
6. A simple, easy-to-use interface.

Keep these six requirements in mind when proposing architecture; source attribution and format heterogeneity are first-class constraints, not afterthoughts.

## Working conventions

- Product and planning documents live under `docs/`. The PRD is the source of truth for scope until a plan or spec supersedes it.
- The PRD is in Swedish; code, identifiers, and technical docs should be in English unless the user says otherwise.
