"""Independent label-based scoring. Missing/error/abstained cases never count as correct."""
from __future__ import annotations

from collections import Counter
from .models import CATEGORIES, Prediction, Truth, ValidationError


def ratio(a: int | float, b: int | float) -> float | None:
    return round(a / b, 6) if b else None


def score(truth: dict[str, Truth], predictions: list[Prediction]) -> dict:
    seen = {}
    for prediction in predictions:
        if prediction.case_id not in truth:
            raise ValidationError(f"Unknown case ID: {prediction.case_id}")
        if prediction.case_id in seen:
            raise ValidationError(f"Duplicate prediction: {prediction.case_id}")
        seen[prediction.case_id] = prediction
    count: Counter = Counter()
    by_category = {c: Counter() for c in sorted(CATEGORIES)}
    items = []
    for cid, target in truth.items():
        p = seen.get(cid, Prediction(cid, "error", note="Missing prediction."))
        count["total"] += 1
        count["unsafe_total" if target.unsafe else "safe_total"] += 1
        abstained = p.decision in {"abstain", "error"}
        if abstained:
            count[p.decision] += 1
        else:
            count["decided"] += 1
        positive = p.decision == "unsafe"
        negative = p.decision == "safe"
        if target.unsafe and positive:
            count["tp"] += 1
        elif not target.unsafe and positive:
            count["fp"] += 1
        elif not target.unsafe and negative:
            count["tn"] += 1
        elif target.unsafe:
            count["fn"] += 1
        correct = not abstained and positive == target.unsafe
        count["correct"] += int(correct)
        count["category_exact"] += int(not abstained and set(p.categories) == set(target.categories))
        predicted_paths = {e["path"] for e in p.evidence}
        if target.unsafe:
            count["localized"] += int(positive and bool(predicted_paths & set(target.evidence_paths)))
        for cat, c in by_category.items():
            actual, predicted = cat in target.categories, cat in p.categories
            c["support"] += int(actual)
            c["tp"] += int(actual and predicted)
            c["fp"] += int(not actual and predicted)
            c["fn"] += int(actual and not predicted)
        items.append({"case_id": cid, "family": target.family, "expected_unsafe": target.unsafe,
                      "expected_categories": list(target.categories), "prediction": p.to_dict(),
                      "correct": correct, "rationale": target.rationale})
    tp, fp, tn, fn = (count[x] for x in ("tp", "fp", "tn", "fn"))
    sensitivity = ratio(tp, count["unsafe_total"])
    specificity = ratio(tn, count["safe_total"])
    balanced = round((sensitivity + specificity) / 2, 6) if sensitivity is not None and specificity is not None else None
    categories = {}
    for cat, c in by_category.items():
        categories[cat] = {"support": c["support"], "tp": c["tp"], "fp": c["fp"], "fn": c["fn"],
                           "precision": ratio(c["tp"], c["tp"] + c["fp"]),
                           "recall": ratio(c["tp"], c["tp"] + c["fn"]),
                           "f1": ratio(2*c["tp"], 2*c["tp"]+c["fp"]+c["fn"])}
    f1s = [v["f1"] or 0 for v in categories.values() if v["support"]]
    return {
        "metric_policy": "v1-full-denominator-no-error-credit",
        "n_cases": count["total"], "n_safe": count["safe_total"], "n_unsafe": count["unsafe_total"],
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "abstentions": count["abstain"], "errors": count["error"],
        "coverage": ratio(count["decided"], count["total"]),
        "accuracy": ratio(count["correct"], count["total"]),
        "precision": ratio(tp, tp+fp), "recall": sensitivity,
        "f1": ratio(2*tp, 2*tp+fp+fn), "specificity": specificity,
        "false_positive_rate": ratio(fp, count["safe_total"]),
        "balanced_accuracy": balanced,
        "category_exact_match": ratio(count["category_exact"], count["total"]),
        "macro_category_f1": round(sum(f1s)/len(f1s), 6) if f1s else None,
        "evidence_path_recall": ratio(count["localized"], count["unsafe_total"]),
        "by_category": categories, "cases": items,
    }
