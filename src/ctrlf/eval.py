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
    return {
        "expected": sorted(expected), "predicted": sorted(predicted),
        "true_positives": sorted(expected & predicted),
        "false_positives": sorted(predicted - expected),
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
        for d in s["false_positives"]:
            print(f"    FP  {d}")
        for d in s["false_negatives"]:
            print(f"    FN  {d}")


if __name__ == "__main__":
    main()
