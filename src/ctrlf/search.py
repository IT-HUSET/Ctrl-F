"""Free-text search across every OCR-ed page, with an optional written answer.

This is Ctrl-F in the literal sense, which is the point of the product name: the
source PDFs have no text layer, so before today you could not Ctrl-F them at all.

The one thing that makes this non-trivial is the same defect that bit extraction
twice: OCR runs words together, so "below sea level offshore" can arrive as
"belowsealeveloffshore". Every query is therefore matched against both the page
text and a de-spaced copy, and hits found in the de-spaced copy are mapped back
to a readable snippet.
"""
from __future__ import annotations

import json
import re

from .config import PAGES
from . import llm

_pages_cache = None


def pages():
    global _pages_cache
    if _pages_cache is None:
        rows = []
        if PAGES.exists():
            with PAGES.open(encoding="utf-8") as fh:
                for line in fh:
                    r = json.loads(line)
                    r["_flat"] = re.sub(r"\s+", "", r["text"]).lower()
                    r["_low"] = r["text"].lower()
                    rows.append(r)
        _pages_cache = rows
    return _pages_cache


# Question words carry no signal and drown the real terms: "what is the debris
# removal limit" otherwise scores pages full of "the" above the page holding the
# figure. Covers the three languages in this corpus.
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "for", "to", "in", "on", "at",
    "and", "or", "what", "which", "who", "how", "much", "many", "does", "do", "did",
    "any", "all", "this", "that", "these", "those", "it", "its", "be", "been", "with",
    "from", "by", "as", "we", "our", "you", "your",
    "och", "eller", "vad", "som", "en", "ett", "den", "det", "av", "for", "till", "med",
    "ja", "tai", "mika", "joka", "on", "ovat", "se", "ne",
}


def _terms(query: str):
    words = [t for t in re.split(r"\W+", query.strip().lower()) if len(t) > 1]
    kept = [t for t in words if t not in STOPWORDS]
    return kept or words  # never return nothing, even for an all-stopword query


def search(query: str, limit: int = 20):
    """Rank pages by how well they match. Phrase matches outrank scattered terms."""
    terms = _terms(query)
    if not terms:
        return []
    phrase = query.strip().lower()
    phrase_flat = re.sub(r"\s+", "", phrase)
    hits = []
    for p in pages():
        score = 0
        matched = []
        if phrase in p["_low"]:
            score += 10
            matched.append(phrase)
        elif phrase_flat and phrase_flat in p["_flat"]:
            score += 8
            matched.append(phrase)
        for t in terms:
            t_flat = re.sub(r"\s+", "", t)
            n = p["_low"].count(t)
            if n:
                score += min(n, 5)
                matched.append(t)
            elif t_flat and t_flat in p["_flat"]:
                score += 1
                matched.append(t)
        if score:
            hits.append((score, p, matched))
    hits.sort(key=lambda h: (-h[0], h[1]["doc_id"], h[1]["page"]))
    return [{
        "score": s,
        "doc_id": p["doc_id"],
        "page": p["page"],
        "image": p["image"],
        "text_source": p["text_source"],
        "snippet": snippet(p["text"], matched),
        "matched": sorted(set(matched)),
    } for s, p, matched in hits[:limit]]


def snippet(text: str, matched, width: int = 160) -> str:
    """A readable window around the best match, falling back to the page start."""
    low = text.lower()
    for m in sorted(set(matched), key=len, reverse=True):
        i = low.find(m)
        if i >= 0:
            s = max(0, i - width)
            return ("..." if s else "") + text[s:i + len(m) + width].strip() + "..."
    # match was only found in the de-spaced copy: show the densest-looking region
    flat_key = re.sub(r"\s+", "", (matched[0] if matched else ""))
    if flat_key:
        stripped = re.sub(r"\s+", "", text).lower()
        j = stripped.find(flat_key)
        if j >= 0:
            frac = j / max(len(stripped), 1)
            k = int(frac * len(text))
            s = max(0, k - width)
            return ("..." if s else "") + text[s:k + len(flat_key) + width].strip() + "..."
    return text[:2 * width].strip() + "..."


ANSWER_SYSTEM = (
    "You answer questions about insurance policy documents using only the page excerpts given. "
    "The excerpts come from OCR, so words are sometimes run together and characters are wrong; "
    "read past that. Cite the page number for every claim, like [page 4]. If the excerpts do not "
    "contain the answer, say so plainly instead of guessing."
)


def answer(query: str, hits, max_pages: int = 6) -> str:
    """Have the local model answer from the retrieved pages, citing page numbers."""
    if not hits:
        return "Nothing in the corpus matched that."
    block = "\n\n".join(
        "[%s page %d]\n%s" % (h["doc_id"], h["page"], h["snippet"])
        for h in hits[:max_pages]
    )[:7000]
    prompt = (
        "Question: " + query + "\n\n"
        "Excerpts retrieved from the policy corpus:\n\n" + block + "\n\n"
        "Answer the question in at most four sentences, citing page numbers."
    )
    try:
        return llm.ask(prompt, system=ANSWER_SYSTEM, timeout=120).strip()
    except Exception as e:
        return "The local model did not answer (%s). The matching pages are listed below." % (
            str(e)[:80])
