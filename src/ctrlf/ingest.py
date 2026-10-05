"""Turn the corpus (PDFs, plus scans and screenshots) into searchable page text.

The documents have no text layer: their glyphs are flattened to vector outlines,
so 208 of 226 pages yield zero characters from any PDF parser. Those pages are
rendered and OCR'd. The 18 pages that do carry text are read directly, which is
both faster and exact.

OCR runs through RapidOCR (ONNX, pip-installed), so the prototype needs no system
binary and makes no network calls. Work is parallelised per PAGE rather than per
document, because one document holds 85 of the 226 pages and would otherwise set
the wall-clock on its own.

Folder names are deliberately NOT recorded. They are ground truth for scoring
(see eval.py) and must never influence an answer.
"""
from __future__ import annotations

import os

# onnxruntime grabs every core per instance by default. With several worker
# processes that means dozens of threads fighting over 16 logical cores, which
# measured 14x SLOWER than the numbers below. Cap threads before it is imported.
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import pymupdf

from .config import DATA, PAGES, IMAGES, OCR_DPI, corpus_files

MIN_NATIVE_CHARS = 200  # below this, treat the page as having no text layer
_ocr = None


def _engine():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def do_page(task: tuple[str, str, int, int]) -> dict:
    """Render one page, read it, write its image. Runs in a worker process."""
    doc_id, pdf_path, index, n_pages = task
    doc = pymupdf.open(pdf_path)
    page = doc[index]
    native = (page.get_text() or "").strip()
    png = page.get_pixmap(dpi=OCR_DPI).tobytes("png")
    doc.close()

    img_path = IMAGES / f"{doc_id}_p{index + 1:03d}.png"
    if not img_path.exists():
        img_path.write_bytes(png)

    if len(native) >= MIN_NATIVE_CHARS:
        text, source = native, "pdf-text"
    else:
        result, _ = _engine()(png)
        text = "\n".join(line[1] for line in result) if result else ""
        source = "ocr"
    return {
        "doc_id": doc_id, "page": index + 1, "n_pages": n_pages,
        "text": text, "text_source": source, "image": img_path.name,
    }


def done_pages() -> list[dict]:
    """Pages of documents already read in full. Adding one file to the corpus
    should not cost a full re-OCR; delete cache/ (run.ps1 -Rebuild) to redo all."""
    if not PAGES.exists():
        return []
    by_doc: dict[str, list[dict]] = {}
    with PAGES.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            by_doc.setdefault(r["doc_id"], []).append(r)
    return [r for ps in by_doc.values() if len(ps) == ps[0]["n_pages"] for r in ps]


def build_tasks(skip: set[str] = frozenset()) -> list[tuple[str, str, int, int]]:
    """Page tasks, shortest documents first.

    One document holds 85 of the 226 pages. Finishing the small ones first means
    an interrupted run still covers most documents, instead of most of one.
    """
    docs = []
    for doc_id, path in corpus_files():
        if doc_id not in skip:
            docs.append((pymupdf.open(path).page_count, doc_id, str(path)))
    docs.sort()
    tasks = []
    for n, doc_id, path in docs:
        tasks += [(doc_id, path, i, n) for i in range(n)]
    return tasks


def main():
    IMAGES.mkdir(parents=True, exist_ok=True)
    PAGES.parent.mkdir(parents=True, exist_ok=True)
    kept = done_pages()
    tasks = build_tasks({r["doc_id"] for r in kept})
    if not tasks and not kept:
        sys.exit(f"No documents under {DATA}")
    if kept:
        print(f"keeping {len(kept)} pages already read", flush=True)
    workers = max(1, min(int(os.environ.get("CTRLF_WORKERS", "6")), len(tasks)))
    print(f"{len(tasks)} pages across {len({t[0] for t in tasks})} documents, "
          f"{workers} workers", flush=True)

    started = time.time()
    done = 0
    with PAGES.open("w", encoding="utf-8") as out, \
            ProcessPoolExecutor(max_workers=workers) as pool:
        for rec in kept:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        for rec in pool.map(do_page, tasks, chunksize=1):
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            done += 1
            if done % 10 == 0 or done == len(tasks):
                rate = done / (time.time() - started)
                left = (len(tasks) - done) / rate if rate else 0
                print(f"  {done}/{len(tasks)} pages  ({rate:.1f} p/s, ~{left:.0f}s left)",
                      flush=True)
    print(f"\n{done} pages -> {PAGES} in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
