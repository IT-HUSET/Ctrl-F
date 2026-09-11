"""Build one structured record per document, with page-level evidence.

Two properties of this corpus shape the design.

OCR frequently runs words together, so every pattern is matched against both the
raw text and a de-spaced copy, and patterns avoid word boundaries where the term
is distinctive on its own.

The documents mix Swedish, Finnish and English, often on one page, so hints are
multilingual and tuned for recall. The local model then reads the matched
snippets and confirms or rejects, which is what controls false positives. One
model call per document per question, not per page: the per-page version measured
112s for a four-page document, which does not fit the day.

Folder names are never read here. They are ground truth for scoring only.
"""
from __future__ import annotations

import collections
import json
import re
import sys
import time

from .config import PAGES, RECORDS
from . import llm

OFFSHORE_HINTS = [
    r"off\s*-?\s*shore", r"subsea", r"below\s*sea\s*level", r"sea\s*level",
    r"wreck", r"sue\s*and\s*labour", r"merell[ai]", r"merialue", r"avomeri",
    r"till\s*sj[o0]ss", r"til\s*havs", r"havsbaserad", r"havsvind", r"sj[o0]fart",
    r"platform", r"\brig\b", r"vessel", r"marine", r"windfarm", r"havvind",
    r"inter\s*array", r"cable\s*to\s*shore", r"jack\s*up", r"dockside",
]
EXCESS_AUTO_HINTS = [
    r"excess\s*auto", r"auto\s*liability", r"automobile\s*liability",
    r"motor\s*liability", r"attachment\s*point", r"underlying\s*(policy|limit|insurance)",
    r"excess\s*of\s*loss", r"\bumbrella\b",
]
LAYER_HINTS = [
    r"\blayer\b", r"kerros", r"skikt", r"excess\s*of", r"in\s*excess\s*of",
    r"attachment", r"excedent", r"primary\s*(layer|policy|insurer)", r"\bxs\b",
    r"first\s*loss", r"underlying",
]
US_HINTS = [
    r"united\s*states", r"u\.?s\.?a\b", r"\busa\b", r"yhdysvallat",
    r"f[o0]renta\s*staterna", r"north\s*america",
]

HINTS = {"offshore": OFFSHORE_HINTS, "excess_auto_us": EXCESS_AUTO_HINTS, "layer": LAYER_HINTS}


def _norm(text):
    """OCR drops spaces; searching a de-spaced copy recovers those matches."""
    return re.sub(r"\s+", "", text)


def snippets(text, patterns, width=130):
    out, seen = [], set()
    for haystack in (text, _norm(text)):
        for p in patterns:
            for m in re.finditer(p, haystack, re.IGNORECASE):
                s = max(0, m.start() - width)
                frag = haystack[s:m.end() + width].replace("\n", " ").strip()
                k = frag[:60].lower()
                if k not in seen:
                    seen.add(k)
                    out.append(frag)
    return out[:6]


VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "applies": {"type": "boolean"},
        "page": {"type": "integer"},
        "quote": {"type": "string"},
        "attachment_point": {"type": "string"},
        "limit": {"type": "string"},
        "currency": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["applies", "quote", "reason"],
}
HEADER_SCHEMA = {
    "type": "object",
    "properties": {
        "insured": {"type": "string"},
        "policy_no": {"type": "string"},
        "period": {"type": "string"},
    },
    "required": ["insured", "policy_no", "period"],
}

QUESTIONS = {
    "offshore": (
        "Do these excerpts show that the policy covers OFFSHORE risk: anything at sea, below sea "
        "level, on a vessel, rig or platform, subsea or inter-array cabling, marine wreck removal, "
        "or an offshore wind project? A cover item whose own name begins with the word Offshore "
        "counts. Marine and sea-related wording counts even inside a transport or cargo policy. "
        "Answer applies=true if any excerpt shows offshore exposure."
    ),
    "excess_auto_us": (
        "Do these excerpts show EXCESS AUTO or automobile or motor liability cover, sitting excess "
        "of an underlying policy, applying in the UNITED STATES? If so give the attachment point, "
        "meaning where this cover starts, and the limit, with currency. Answer applies=false if the "
        "cover is not auto liability, or is not excess, or has no US scope."
    ),
    "layer": (
        "Do these excerpts show that this policy insures a LAYER of a risk: cover sitting excess of "
        "an underlying amount rather than from the ground up? If so give the excess or attachment "
        "point and the limit of this layer, with currency. A sublimit inside a primary policy is "
        "NOT a layer."
    ),
}

SYSTEM = (
    "You read insurance policy documents in Swedish, Finnish and English. The text comes from OCR: "
    "words are often run together and characters are sometimes wrong. Read past those errors. "
    "Answer only from the excerpts given, and quote one verbatim as evidence."
)


def load_pages():
    docs = collections.OrderedDict()
    with PAGES.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            docs.setdefault(r["doc_id"], []).append(r)
    return docs


def extract_doc(doc_id, pages):
    pages = sorted(pages, key=lambda p: p["page"])
    by_page = {p["page"]: p for p in pages}

    head = "\n".join(p["text"] for p in pages[:2])[:3500]
    try:
        h = llm.ask_json(
            "First pages of an insurance policy:\n\n" + head + "\n\n"
            "Extract the insured party, meaning the policyholder company name and not a policy "
            "number, plus the policy number and the insurance period.",
            HEADER_SCHEMA, system=SYSTEM)
    except Exception as e:
        h = {"insured": "", "policy_no": "", "period": "", "error": str(e)[:100]}

    rec = {
        "doc_id": doc_id,
        "n_pages": pages[0]["n_pages"],
        "insured": h.get("insured", ""),
        "policy_no": h.get("policy_no", ""),
        "period": h.get("period", ""),
        "ocr_pages": sum(1 for p in pages if p["text_source"] == "ocr"),
        "empty_pages": sum(1 for p in pages if not p["text"].strip()),
        "findings": {},
    }

    us_doc = any(snippets(p["text"], US_HINTS) for p in pages)

    for key, question in QUESTIONS.items():
        found = []
        for p in pages:
            for s in snippets(p["text"], HINTS[key]):
                found.append((p["page"], s))
        finding = {
            "applies": False, "evidence": [], "attachment_point": "", "limit": "",
            "currency": "", "candidate_pages": sorted({pg for pg, _ in found}),
        }
        if found:
            block = "\n".join("[page %d] %s" % (pg, s) for pg, s in found[:14])[:6000]
            try:
                v = llm.ask_json(
                    question + "\n\nExcerpts from one policy document:\n\n" + block,
                    VERIFY_SCHEMA, system=SYSTEM)
            except Exception:
                v = {}
            blocked = (key == "excess_auto_us" and not us_doc)
            if v.get("applies") and not blocked:
                page = v.get("page") or found[0][0]
                if page not in by_page:
                    page = found[0][0]
                finding["applies"] = True
                finding["attachment_point"] = v.get("attachment_point", "")
                finding["limit"] = v.get("limit", "")
                finding["currency"] = v.get("currency", "")
                finding["evidence"] = [{
                    "page": page,
                    "quote": (v.get("quote") or found[0][1])[:400],
                    "reason": (v.get("reason") or "")[:300],
                    "image": by_page[page]["image"],
                }]
        rec["findings"][key] = finding
    return rec


def main():
    if not llm.available():
        sys.exit("Local model not reachable. Start it with: ollama serve")
    docs = load_pages()
    complete = {d: ps for d, ps in docs.items() if len(ps) == ps[0]["n_pages"]}
    skipped = sorted(set(docs) - set(complete))
    if skipped:
        print("skipping %d incomplete document(s): %s" % (len(skipped), skipped))

    # Resume: OCR and extraction run concurrently (OCR on CPU, model on GPU),
    # so this is re-run as documents finish. Already-extracted docs are kept.
    out = []
    if RECORDS.exists():
        try:
            out = json.loads(RECORDS.read_text(encoding="utf-8"))
        except Exception:
            out = []
    have = {r["doc_id"] for r in out}
    todo = {d: ps for d, ps in complete.items() if d not in have}
    if have:
        print("resuming: %d already extracted, %d to do" % (len(have), len(todo)))

    t0 = time.time()
    for i, (doc_id, pages) in enumerate(todo.items(), 1):
        t = time.time()
        out.append(extract_doc(doc_id, pages))
        print("[%d/%d] %s (%dp) %.0fs" % (i, len(todo), doc_id, len(pages), time.time() - t),
              flush=True)
        RECORDS.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n%d records -> %s in %.0fs" % (len(out), RECORDS, time.time() - t0))


if __name__ == "__main__":
    main()
