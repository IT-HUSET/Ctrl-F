"""Shared paths and settings. Everything derived lives under cache/."""
from __future__ import annotations
import os
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CACHE = ROOT / "cache"
PAGES = CACHE / "pages.jsonl"       # one record per page: text + provenance
RECORDS = CACHE / "records.json"    # one structured record per document
IMAGES = CACHE / "pageimages"       # rendered page PNGs, used as citations

# Scans and screenshots arrive alongside the PDFs; pymupdf opens an image as a
# one-page document, so they take the same OCR path.
CORPUS_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg"}


def corpus_files() -> list[tuple[str, pathlib.Path]]:
    """(doc_id, path) for every source file. ingest and eval must agree on ids."""
    out, seen = [], {}
    for path in sorted(DATA.rglob("*")):
        if path.suffix.lower() not in CORPUS_SUFFIXES:
            continue
        stem = path.stem.replace(" ", "_")
        seen[stem] = seen.get(stem, 0) + 1
        out.append((stem if seen[stem] == 1 else f"{stem}__{seen[stem]}", path))
    return out


OLLAMA_URL =os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("CTRLF_MODEL", "qwen2.5:7b-instruct")
OCR_DPI = int(os.environ.get("CTRLF_OCR_DPI", "200"))
OCR_LANGS = os.environ.get("CTRLF_OCR_LANGS", "fin+eng")


def find_tesseract() -> str | None:
    """Locate the tesseract binary without assuming it is on PATH."""
    found = shutil.which("tesseract")
    if found:
        return found
    for p in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if pathlib.Path(p).exists():
            return p
    return None
