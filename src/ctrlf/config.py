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

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("CTRLF_MODEL", "qwen2.5:7b-instruct")
OCR_DPI = int(os.environ.get("CTRLF_OCR_DPI", "300"))
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
