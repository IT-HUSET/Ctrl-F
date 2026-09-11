"""Ctrl-F — ask the portfolio a question, get policies with evidence.

Everything shown here is precomputed by the ingest and extract steps, so the app
does no model work at query time and no network calls at all.
"""
from __future__ import annotations

import json
import pathlib

import streamlit as st

from src.ctrlf.config import RECORDS, IMAGES, PAGES
from src.ctrlf import eval as scoring
from src.ctrlf import search as textsearch
from src.ctrlf import embed as embedding
from src.ctrlf import theme

QUESTIONS = {
    "offshore": {
        "title": "Policies covering offshore risk",
        "customer_wording": "Identify policies covering offshore risks/projects.",
        "columns": [],
        "bar": "Must be exact: every offshore policy, and nothing else.",
    },
    "excess_auto_us": {
        "title": "US excess auto liability, with attachment point and limit",
        "customer_wording": (
            "Find all liability policies with excess auto cover in United States. "
            "For such policies, find the attachment point and possible limit."
        ),
        "columns": ["attachment_point", "limit", "currency"],
        "bar": "Best effort. Figures come from OCR and need checking.",
    },
    "layer": {
        "title": "Policies insuring a layer of a risk",
        "customer_wording": (
            "Identify policies insuring a layer of the risk. Find excess point and limit. "
            "Group together policies insuring different layers of the same risk."
        ),
        "columns": ["attachment_point", "limit", "currency"],
        "bar": "Best effort, including grouping by insured.",
    },
}

st.set_page_config(page_title="Ctrl-F", page_icon="🌲", layout="wide")
theme.apply()


@st.cache_data
def load():
    if not RECORDS.exists():
        return None
    return json.loads(RECORDS.read_text(encoding="utf-8"))


records = load()
theme.hero("Ctrl-F", "Questions over If Industrial policy documents. Every answer carries its source.")

if not records:
    st.error("No extracted records yet. Run the pipeline first:  `uv run python -m src.ctrlf.extract`")
    st.stop()

with st.sidebar:
    st.subheader("Corpus")
    ocr_pages = sum(r.get("ocr_pages", 0) for r in records)
    st.metric("Documents", len(records))
    st.metric("Pages", sum(r.get("n_pages", 0) for r in records))
    st.metric("Pages read by OCR", ocr_pages)
    st.caption(
        "The source PDFs have no text layer — their text is flattened to vector "
        "outlines — so almost every page is recovered by OCR before anything else happens."
    )

FREE = "__free__"
LABELS = {k: v["title"] for k, v in QUESTIONS.items()}
LABELS[FREE] = "Free text search"

key = st.radio(
    "Question",
    list(QUESTIONS) + [FREE],
    format_func=lambda k: LABELS[k],
    horizontal=True,
)

if key == FREE:
    st.info(
        "Search every page of every document. These PDFs have no text layer, so before "
        "this pipeline ran you could not search them at all — not even with Ctrl-F."
    )
    query = st.text_input(
        "Search the corpus",
        placeholder="e.g. debris removal, offshore wind, excess of, deductible",
    )
    sem_ready = embedding.available() and embedding.VECTORS.exists()
    modes = ["Keyword", "Semantic", "Both"] if sem_ready else ["Keyword"]
    c1, c2 = st.columns([1, 2])
    with c1:
        mode = st.radio("Matching", modes, horizontal=True)
    with c2:
        want_answer = st.checkbox(
            "Have the local model answer from the matching pages", value=True)
    if sem_ready:
        st.caption(
            "Keyword finds wording the query shares with the page. Semantic compares meaning, so "
            f"an English query can reach a Swedish or Finnish passage. Model: {embedding.model_name()}."
        )
    else:
        st.caption(
            "Keyword matching only. Semantic search needs an embedding model and a built index: "
            "`ollama pull bge-m3` then `uv run python -m src.ctrlf.embed`."
        )

    if query:
        if mode == "Keyword":
            hits = textsearch.search(query, limit=25)
        elif mode == "Semantic":
            hits = [dict(h, score=h["similarity"], matched=["semantic"],
                         text_source="semantic") for h in embedding.semantic(query, limit=25)]
        else:
            lex = textsearch.search(query, limit=20)
            sem = embedding.semantic(query, limit=20)
            merged = {}
            for rank, h in enumerate(lex):
                merged[(h["doc_id"], h["page"])] = dict(h, score=round(1.0 / (60 + rank), 5))
            for rank, h in enumerate(sem):
                k = (h["doc_id"], h["page"])
                add = 1.0 / (60 + rank)
                if k in merged:
                    merged[k]["score"] = round(merged[k]["score"] + add, 5)
                    merged[k]["matched"] = sorted(set(merged[k]["matched"] + ["semantic"]))
                else:
                    merged[k] = dict(h, score=round(add, 5), matched=["semantic"],
                                     text_source="semantic")
            hits = sorted(merged.values(), key=lambda h: -h["score"])[:25]
        if want_answer and hits:
            with st.spinner("Reading the matching pages..."):
                st.markdown("#### Answer")
                st.write(textsearch.answer(query, hits))
                st.caption(
                    "Written by the local model from the pages below, nothing else. "
                    "Check the cited page before relying on it."
                )
                st.divider()
        st.markdown(f"#### {len(hits)} matching pages")
        for h in hits:
            with st.expander(
                f"{h['doc_id']} — page {h['page']}  ·  score {h['score']}"
                f"  ·  matched: {', '.join(h['matched'][:4])}"
            ):
                st.markdown(f"> {h['snippet']}")
                st.caption(
                    f"Text recovered by {'OCR' if h['text_source'] == 'ocr' else 'the PDF text layer'}."
                )
                img = IMAGES / h["image"]
                if img.exists():
                    with st.popover(f"Show page {h['page']}"):
                        st.image(str(img), use_container_width=True)
        if not hits:
            st.warning("Nothing matched. Try a shorter phrase — OCR sometimes runs words together.")
    st.stop()

q = QUESTIONS[key]
st.info(f"**Customer's question:** {q['customer_wording']}")

matches = [r for r in records if r["findings"].get(key, {}).get("applies")]
score = scoring.score(records, key)

left, right = st.columns([3, 1])
with right:
    st.subheader("Measured")
    st.caption(q["bar"])
    st.metric("Precision", f"{score['precision']:.0%}")
    st.metric("Recall", f"{score['recall']:.0%}")
    unexplained = score["unexplained_false_positives"]
    if unexplained:
        st.warning(f"False positives: {len(unexplained)}")
        for d in unexplained:
            st.caption(f"· {d}")
    if score["verified_correct"]:
        st.info(f"{len(score['verified_correct'])} scored as wrong, verified correct by hand")
        for d, why in score["verified_correct"].items():
            st.caption(f"· {why}")
    if score["false_negatives"]:
        st.error(f"Missed: {len(score['false_negatives'])}")
        for d in score["false_negatives"]:
            st.caption(f"· {d}")
    if not score["false_positives"] and not score["false_negatives"]:
        st.success("Exact match against the supplied set.")
    st.caption(
        "Scored against the customer's folders. The pipeline never sees them — it reads "
        "document content only. Those folders are the document set supplied per question, "
        "not an answer key, so a document can correctly match a question it was not filed "
        "under. Where that happened we checked the page by hand and say so above."
    )

with left:
    st.subheader(f"{len(matches)} matching " + ("policy" if len(matches) == 1 else "policies"))
    if not matches:
        st.write("No policies matched.")
    for r in matches:
        f = r["findings"][key]
        # These documents are partially redacted: the policyholder name is behind a
        # black box, so the model often returns a customer number. Lead with the
        # policy number, which is reliably present.
        pol = r.get("policy_no") or r["doc_id"]
        insured = r.get("insured") or ""
        period = r.get("period") or "period not read"
        header = f"**Policy {pol}** · {period}" + (f" · {insured}" if insured else "")
        with st.expander(header, expanded=len(matches) <= 3):
            cols = [c for c in q["columns"] if f.get(c)]
            if cols:
                st.write(" · ".join(f"**{c.replace('_', ' ')}:** {f[c]}" for c in cols))
            elif q["columns"]:
                st.caption("Figures not recovered from this document.")
            for ev in f["evidence"][:3]:
                st.markdown(f"> {ev['quote']}")
                st.caption(f"Page {ev['page']} · {ev['reason']}")
                img = IMAGES / ev["image"]
                if img.exists():
                    with st.popover(f"Show page {ev['page']}"):
                        st.image(str(img), use_container_width=True)
            st.caption(f"Source file: `{r['doc_id']}` · {r['n_pages']} pages")

    if key == "layer" and matches:
        st.divider()
        st.subheader("Layers grouped by insured")
        st.caption(
            "Grouping is by insured party. These documents are partially redacted, so the "
            "policyholder name is frequently unavailable and grouping falls back to the "
            "customer number the document does carry. This is a known weakness, not a result."
        )
        groups: dict[str, list] = {}
        for r in matches:
            groups.setdefault(r.get("insured") or "(insured redacted)", []).append(r)
        for insured, rs in groups.items():
            if len(rs) > 1:
                st.write(f"**{insured}** — {len(rs)} policies covering different layers")
                for r in rs:
                    f = r["findings"]["layer"]
                    st.caption(
                        f"   · policy {r.get('policy_no') or r['doc_id']}"
                        f" — excess {f.get('attachment_point') or '?'}"
                        f", limit {f.get('limit') or '?'} {f.get('currency') or ''}"
                    )
            else:
                st.write(f"{insured} — single layer policy")
