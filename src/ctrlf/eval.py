"""Score answers against ground truth.

The corpus folders are the customer's own labels: `Offshore Projects`, `excess
auto liability`, `Layers`, and `Projects` as the negative set. The pipeline never
sees them; this module does, and only to measure. The customer defines a bad
answer as one that misses real cases or includes false positives, so precision
and recall are the right measure rather than a subjective look at the output.
"""
from __future__ import annotations

import json

from .config import RECORDS, corpus_files

FOLDER_LABEL = {
    "offshore projects": "offshore",
    "excess auto liability": "excess_auto_us",
    "layers": "layer",
    "projects": None,  # negative / distractor set
}


def truth() -> dict[str, set[str]]:
    """doc_id -> set of labels, derived from folder names."""
    out: dict[str, set[str]] = {}
    for doc_id, path in corpus_files():
        label = FOLDER_LABEL.get(path.parent.name.lower())
        out[doc_id] = {label} if label else set()
    return out


def answers(records: list[dict], key: str) -> dict[str, str]:
    """policy doc_id -> where its yes came from: "policy" or a supporting doc_id.

    Supporting documents are not scored on their own; their evidence counts for
    the policies they were linked to. The customer confirmed one policy's US excess
    auto cover is stated only outside the policy document (temp.lh.policy.2022.06.08), so a
    policy may only be answerable through one.
    """
    by_id = {r["doc_id"]: r for r in records}
    out = {}
    for r in records:
        if r.get("kind") == "supporting":
            continue
        if r["findings"].get(key, {}).get("applies"):
            out[r["doc_id"]] = "policy"
            continue
        for s in r.get("supported_by", []):
            if by_id.get(s, {}).get("findings", {}).get(key, {}).get("applies"):
                out[r["doc_id"]] = s
                break
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
    # Removed: ("layer", "temp.lh.policy.2022.06.22"), "cover is MNZD10 in excess of
    # MNZD20". The customer defined a layer as a policy covering only a band of
    # losses. That line is one New Zealand extension of a ground-up master policy,
    # so it is not a layer, and the hand check that accepted it was wrong.
}


def score(records: list[dict], key: str) -> dict:
    supporting = {r["doc_id"] for r in records if r.get("kind") == "supporting"}
    gt = {d: labels for d, labels in truth().items() if d not in supporting}
    expected = {d for d, labels in gt.items() if key in labels}
    source = answers(records, key)
    predicted = set(source) & set(gt)
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
        "via_supporting": {d: source[d] for d in sorted(predicted) if source[d] != "policy"},
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
        for d, sup in s["via_supporting"].items():
            print(f"    via {d} - answered from supporting document {sup}")


if __name__ == "__main__":
    main()
