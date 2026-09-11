"""Score answers against ground truth.

The corpus folders are the customer's own labels: `Offshore Projects`, `excess
auto liability`, `Layers`, and `Projects` as the negative set. The pipeline never
sees them; this module does, and only to measure. The customer defines a bad
answer as one that misses real cases or includes false positives, so precision
and recall are the right measure rather than a subjective look at the output.
"""
from __future__ import annotations

import json

from .config import DATA, RECORDS

FOLDER_LABEL = {
    "offshore projects": "offshore",
    "excess auto liability": "excess_auto_us",
    "layers": "layer",
    "projects": None,  # negative / distractor set
}


def truth() -> dict[str, set[str]]:
    """doc_id -> set of labels, derived from folder names."""
    out: dict[str, set[str]] = {}
    seen: dict[str, int] = {}
    for pdf in sorted(DATA.rglob("*.pdf")):
        stem = pdf.stem.replace(" ", "_")
        seen[stem] = seen.get(stem, 0) + 1
        doc_id = stem if seen[stem] == 1 else f"{stem}__{seen[stem]}"
        label = FOLDER_LABEL.get(pdf.parent.name.lower())
        out[doc_id] = {label} if label else set()
    return out


# Hand-checked exceptions.
#
# The folders are the document set the customer supplied per question, not an
# answer key, so a document can legitimately match a question it was not filed
# under. Each entry below was read by a person on the page image and confirmed.
# They are reported separately rather than silently folded into the score.
VERIFIED_CORRECT = {
    ("offshore", "temp.lh.policy.2024.02.21"):
        "for off-shore GBP 5,000,000 - genuine offshore cover, filed under excess auto",
    ("layer", "temp.lh.policy.2022.06.22"):
        "cover is MNZD10 in excess of MNZD20 - a layer, filed under excess auto",
}


def score(records: list[dict], key: str) -> dict:
    gt = truth()
    expected = {d for d, labels in gt.items() if key in labels}
    predicted = {r["doc_id"] for r in records if r["findings"].get(key, {}).get("applies")}
    known = set(gt)
    predicted &= known
    tp = len(expected & predicted)
    fp = len(predicted - expected)
    fn = len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    raw_fp = sorted(predicted - expected)
    verified = [d for d in raw_fp if (key, d) in VERIFIED_CORRECT]
    return {
        "expected": sorted(expected), "predicted": sorted(predicted),
        "true_positives": sorted(expected & predicted),
        "false_positives": raw_fp,
        "verified_correct": {d: VERIFIED_CORRECT[(key, d)] for d in verified},
        "unexplained_false_positives": [d for d in raw_fp if d not in verified],
        "false_negatives": sorted(expected - predicted),
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
    }


def main():
    records = json.loads(RECORDS.read_text(encoding="utf-8"))
    print(f"{'question':16} {'prec':>6} {'recall':>7} {'F1':>6}   FP / FN")
    for key in ("offshore", "excess_auto_us", "layer"):
        s = score(records, key)
        print(f"{key:16} {s['precision']:>6.2f} {s['recall']:>7.2f} {s['f1']:>6.2f}   "
              f"{len(s['false_positives'])} / {len(s['false_negatives'])}")
        for d in s["unexplained_false_positives"]:
            print(f"    FP  {d}")
        for d, why in s["verified_correct"].items():
            print(f"    ok  {d} - scored as FP, verified correct: {why}")
        for d in s["false_negatives"]:
            print(f"    FN  {d}")


if __name__ == "__main__":
    main()
