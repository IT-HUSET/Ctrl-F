"""Semantic search: embed every page once, then compare by meaning at query time.

Lexical search only finds wording the query shares with the page. This corpus is
Swedish, Finnish and English, often within one document, so a query for
"offshore" should also reach a page that says "till sjoss" or "merella". That is
what embeddings buy here, and it is why the model is multilingual.

Embeddings are computed once into cache/embeddings.json and reused. Long pages
are split into overlapping chunks so a single hit points at a passage rather
than at eight pages of policy schedule.
"""
from __future__ import annotations

import json
import math
import re

import requests

from .config import CACHE, OLLAMA_URL
from .search import pages

# bge-m3 is multilingual, which is what this corpus needs: a query in English
# should reach a Swedish or Finnish passage. nomic-embed-text is the smaller
# fallback if the larger download does not arrive in time; it is English-centric,
# so cross-language recall drops with it.
PREFERRED_MODELS = ["bge-m3", "nomic-embed-text"]
VECTORS = CACHE / "embeddings.json"


def _installed():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def model_name():
    """Whichever preferred embedding model is actually installed."""
    have = _installed()
    for want in PREFERRED_MODELS:
        for name in have:
            if name.startswith(want):
                return name
    return None
CHUNK_CHARS = 900
CHUNK_OVERLAP = 200

_index = None


def embed(texts, timeout: int = 180):
    """Embed a batch of strings with the local model. Nothing leaves the machine."""
    out = []
    for t in texts:
        r = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": model_name() or PREFERRED_MODELS[0], "prompt": t[:4000]},
            timeout=timeout,
        )
        r.raise_for_status()
        out.append(r.json()["embedding"])
    return out


def chunk(text: str):
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) <= CHUNK_CHARS:
        return [text] if text else []
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + CHUNK_CHARS])
        start += CHUNK_CHARS - CHUNK_OVERLAP
    return out


def available() -> bool:
    return model_name() is not None


def build(verbose: bool = True):
    """Embed every chunk of every page. Run once; results are cached on disk."""
    rows = []
    for p in pages():
        for i, c in enumerate(chunk(p["text"])):
            rows.append({"doc_id": p["doc_id"], "page": p["page"], "image": p["image"],
                         "chunk": i, "text": c})
    if verbose:
        print("embedding %d chunks from %d pages" % (len(rows), len(pages())), flush=True)
    step = 16
    for s in range(0, len(rows), step):
        batch = rows[s:s + step]
        for row, vec in zip(batch, embed([r["text"] for r in batch])):
            row["vec"] = vec
        if verbose:
            print("  %d/%d" % (min(s + step, len(rows)), len(rows)), flush=True)
    VECTORS.write_text(json.dumps(rows), encoding="utf-8")
    if verbose:
        print("-> %s" % VECTORS)
    return rows


def index():
    global _index
    if _index is None:
        if not VECTORS.exists():
            return []
        rows = json.loads(VECTORS.read_text(encoding="utf-8"))
        for r in rows:
            n = math.sqrt(sum(x * x for x in r["vec"])) or 1.0
            r["_norm"] = n
        _index = rows
    return _index


def semantic(query: str, limit: int = 20):
    """Rank chunks by cosine similarity to the query."""
    rows = index()
    if not rows:
        return []
    q = embed([query])[0]
    qn = math.sqrt(sum(x * x for x in q)) or 1.0
    scored = []
    for r in rows:
        v = r["vec"]
        dot = sum(a * b for a, b in zip(q, v))
        scored.append((dot / (qn * r["_norm"]), r))
    scored.sort(key=lambda t: -t[0])

    best, seen = [], set()
    for sim, r in scored:
        k = (r["doc_id"], r["page"])
        if k in seen:
            continue
        seen.add(k)
        best.append({
            "similarity": round(float(sim), 3),
            "doc_id": r["doc_id"], "page": r["page"], "image": r["image"],
            "snippet": r["text"][:420] + ("..." if len(r["text"]) > 420 else ""),
        })
        if len(best) >= limit:
            break
    return best


def main():
    if not available():
        raise SystemExit("No embedding model. Run: ollama pull " + PREFERRED_MODELS[0])
    build()


if __name__ == "__main__":
    main()
