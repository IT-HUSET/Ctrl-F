# Search & Document Store — Prototype Research

Context: [prd.md](./prd.md) calls for AI-powered natural-language search, pattern/relationship discovery, analysis/aggregation, and source-backed answers across ~200 million documents in mixed formats.

## Recommended stack for the prototype

**OpenSearch** (Apache 2.0, free, self-hosted) as the document store and search index.

- Supports BM25 full-text search and k-NN vector search in the same engine → enables hybrid (keyword + semantic) search, which natural-language querying needs.
- Scales toward hundreds of millions of documents; avoids a rewrite later if the prototype succeeds.
- Tradeoff: more operational overhead than a quick-start engine like Meilisearch/Typesense.

Alternatives considered:

| Option | Why not primary | When to prefer it |
|---|---|---|
| PostgreSQL + `tsvector` + `pgvector` | Won't scale as gracefully to 200M docs without sharding | Already standardized on Postgres; simplest single-service setup |
| Meilisearch / Typesense | Less proven at 200M-doc scale | Speed of setup matters more than long-term scale right now |
| Apache Solr | No built-in vector search, more ops overhead | Team already has Lucene/Solr expertise |

## File format support

OpenSearch itself only indexes structured JSON/text — it has **no native file parsers**. A text-extraction step must run in front of it.

**Extraction layer: Apache Tika**, via either:
- **FSCrawler** — open-source crawler purpose-built for watching a filesystem/share, extracting with Tika, and pushing documents into OpenSearch.
- **`ingest-attachment` plugin** — runs Tika inside an OpenSearch ingest pipeline on base64-encoded attachments.

Formats Tika covers out of the box (relevant subset for a corporate/industrial archive):

- PDF (text-based)
- Microsoft Office: DOC/DOCX, XLS/XLSX, PPT/PPTX
- OpenDocument: ODT, ODS, ODP
- RTF, plain text, CSV
- HTML/XML
- Email: EML, MSG
- EPUB

**Known gaps to plan for:**

- **Scanned/image-based PDFs and photos** — Tika needs a Tesseract OCR integration to extract text; without it these return empty. Given the PRD notes inconsistent metadata and mixed formats, expect a meaningful share of the 200M to need OCR.
- **CAD/engineering drawings** (DWG, DXF, etc.) — not covered by Tika; needs dedicated parsers or falls back to metadata-only indexing.
- **Legacy/proprietary formats** — evaluate case by case as they're discovered in the corpus.

## Suggested prototype pipeline

```
Source files (shares / archive)
        │
        ▼
  FSCrawler (crawl + extract via Tika)
        │
        ├── text-based files ──────────────► extracted text + metadata
        │
        └── scanned/image files ── Tesseract OCR ──► extracted text
        │
        ▼
  OpenSearch ingest pipeline
        │
        ├── BM25 full-text index
        └── embedding step → k-NN vector index (for semantic/hybrid search)
        │
        ▼
  Query layer: natural-language query → hybrid (BM25 + vector) search
        → results returned with source document references
```

## Open questions / next steps

- Confirm the actual format mix in the 200M-document corpus (sampling needed) to size OCR and custom-parser effort.
- Decide embedding model for the vector index (affects infra cost and relevance quality).
- Define what "source" means in the UI (document + page/section-level citation) to satisfy the PRD's traceability requirement.
- Scope the prototype's document count (a representative subset, not all 200M) before committing to full-scale infra.
