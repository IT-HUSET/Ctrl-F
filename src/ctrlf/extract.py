"""Build one structured record per document, with page-level evidence.

Strategy: a cheap multilingual keyword sweep proposes candidate pages, then the
local model verifies each candidate and pulls out figures. Verification is what
kills false positives, which the customer names as a failure mode for every
question. Documents are never judged by the folder they live in.
"""
from __future__ import annotations

import collections
import json
import re
import sys

from .config import PAGES, RECORDS
from . import llm

# Multilingual hints. Recall first: the model prunes false positives afterwards.
OFFSHORE_HINTS = [
    r"off\s*-?\s*shore", r"\boffshore\b", r"merell[aä]", r"merialue", r"avomeri",
    r"till\s+sj[oö]ss", r"til\s+havs", r"havsbaserad", r"\bsubsea\b", r"\bplatform\b",
    r"\brig\b", r"\bvessel\b", r"\bmarine\b", r"\bwindfarm\b", r"havvind",
]
EXCESS_AUTO_HINTS = [
    r"excess\s+auto", r"auto\s+liability", r"automobile\s+liability",
    r"excess\s+of\s+loss", r"attachment\s+point", r"\bunderlying\b",
]
LAYER_HINTS = [
    r"\blayer\b", r"\bkerros\b", r"\bskikt\b", r"excess\s+of", r"\bprimary\b",
    r"\bxs\b", r"in\s+excess\s+of", r"attachment", r"\bexcedent\b",
]
US_HINTS = [r"united\s+states", r"\bU\.?S\.?A?\b", r"yhdysvallat", r"\bUSA\b"]


def _hits(text: str, patterns: list[str]) -> list[str]:
    out = []
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            s = max(0, m.start() - 90)
            out.append(text[s:m.end() + 90].replace("\n", " ").strip())
    return out[:4]


VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "applies": {"type": "boolean"},
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
        "document_type": {"type": "string"},
    },
    "required": ["insured", "policy_no", "period"],
}

QUESTIONS = {
    "offshore": (
        "Does this page show that the insured risk or the cover is OFFSHORE — located at sea, "
        "on a vessel, rig, platform, subsea, or an offshore wind or marine project? "
        "A generic mention of transport, cargo or a company name is NOT offshore. "
        "Answer applies=false unless the page genuinely indicates offshore risk."
    ),
    "excess_auto_us": (
        "Does this page show EXCESS AUTO or automobile liability cover applying in the "
        "UNITED STATES? If so, give the attachment point (the excess point where this cover "
        "starts) and the limit, with currency. Answer applies=false if either the excess auto "
        "nature or the US scope is absent."
    ),
    "layer": (
        "Does this page show that this policy insures a LAYER of a risk — cover sitting "
        "excess of an underlying amount rather than from the ground up? If so give the excess "
        "point (attachment) and the limit of this layer, with currency. "
        "A plain sublimit inside a primary policy is NOT a layer."
    ),
}
HINTS = {"offshore": OFFSHORE_HINTS, "excess_auto_us": EXCESS_AUTO_HINTS, "layer": LAYER_HINTS}

SYSTEM = (
    "You read insurance policy documents written in Finnish and English. The text comes from "
    "OCR and may contain errors. Answer only from the text you are given. Quote verbatim from "
    "the page as evidence. If the page does not support the claim, say applies=false."
)


def load_pages():
    docs = collections.OrderedDict()
    with PAGES.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            docs.setdefault(r["doc_id"], []).append(r)
    return docs


def extract_doc(doc_id: str, pages: list[dict]) -> dict:
    pages = sorted(pages, key=lambda p: p["page"])
    head_text = "\n".join(p["text"] for p in pages[:2])[:6000]
    try:
        header = llm.ask_json(
            f"Insurance policy document, first pages:\n\n{head_text}\n\n"
            "Extract the insured party, the policy number and the insurance period.",
            HEADER_SCHEMA, system=SYSTEM)
    except Exception as e:
        header = {"insured": "", "policy_no": "", "period": "", "error": str(e)[:120]}

    rec = {
        "doc_id": doc_id,
        "n_pages": pages[0]["n_pages"],
        "insured": header.get("insured", ""),
        "policy_no": header.get("policy_no", ""),
        "period": header.get("period", ""),
        "ocr_pages": sum(1 for p in pages if p["text_source"] == "ocr"),
        "empty_pages": sum(1 for p in pages if not p["text"].strip()),
        "findings": {},
    }

    us_doc = any(_hits(p["text"], US_HINTS) for p in pages)
    for key, question in QUESTIONS.items():
        finding = {"applies": False, "evidence": [], "attachment_point": "", "limit": "",
                   "currency": "", "candidate_pages": []}
        for p in pages:
            snippets = _hits(p["text"], HINTS[key])
            if not snippets:
                continue
            finding["candidate_pages"].append(p["page"])
            try:
                v = llm.ask_json(
                    f"{question}\n\nPage {p['page']} of the document:\n\n{p['text'][:5000]}",
                    VERIFY_SCHEMA, system=SYSTEM)
            except Exception:
                continue
            if not v.get("applies"):
                continue
            if key == "excess_auto_us" and not us_doc:
                continue  # US scope must appear somewhere in the document
            finding["applies"] = True
            finding["evidence"].append({
                "page": p["page"], "quote": (v.get("quote") or "")[:400],
                "reason": (v.get("reason") or "")[:300], "image": p["image"],
            })
            for f in ("attachment_point", "limit", "currency"):
                if v.get(f) and not finding[f]:
                    finding[f] = v[f]
        rec["findings"][key] = finding
    return rec


def main():
    if not llm.available():
        sys.exit("Local model not reachable. Start it with: ollama serve")
    docs = load_pages()
    out = []
    for i, (doc_id, pages) in enumerate(docs.items(), 1):
        print(f"[{i}/{len(docs)}] {doc_id} ({len(pages)} pages)", flush=True)
        out.append(extract_doc(doc_id, pages))
    RECORDS.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(out)} records -> {RECORDS}")


if __name__ == "__main__":
    main()
