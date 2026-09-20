import pytest
from prguardbench.dataset import load_review, read_jsonl
from prguardbench.models import CATEGORIES, Prediction, ValidationError
from prguardbench.scoring import score


def test_dataset_manifest_counts_and_balanced_families():
    cases, truth, manifest = load_review()
    assert len(cases) == manifest["count"] == 42
    assert sum(t.unsafe for t in truth.values()) == 21
    assert {t.family for t in truth.values()} == CATEGORIES
    for category in CATEGORIES:
        members = [t for t in truth.values() if t.family == category]
        assert len(members) == 6
        assert sum(t.unsafe for t in members) == 3
    for case in cases:
        assert not {"unsafe", "rationale", "family", "categories"} & case.to_dict().keys()


def perfect_predictions(truth):
    return [Prediction(t.case_id, "unsafe" if t.unsafe else "safe", t.categories,
                       tuple({"path":p,"reason":"test oracle"} for p in t.evidence_paths)) for t in truth.values()]


def test_scorer_independent_oracle_sanity():
    _, truth, _ = load_review()
    m = score(truth, perfect_predictions(truth))
    assert m["accuracy"] == m["balanced_accuracy"] == m["f1"] == 1
    assert m["category_exact_match"] == m["macro_category_f1"] == m["evidence_path_recall"] == 1
    assert m["fp"] == m["fn"] == m["errors"] == 0


def test_missing_predictions_are_not_dropped():
    _, truth, _ = load_review()
    m = score(truth, [])
    assert m["n_cases"] == 42
    assert m["errors"] == 42
    assert m["accuracy"] == m["balanced_accuracy"] == m["coverage"] == 0
    assert m["precision"] is None


def test_always_safe_is_not_perfect():
    _, truth, _ = load_review()
    m = score(truth, [Prediction(t, "safe") for t in truth])
    assert m["balanced_accuracy"] == .5 and m["recall"] == 0
    assert m["precision"] is None


def test_abstain_never_earns_accuracy_credit():
    _, truth, _ = load_review()
    m = score(truth, [Prediction(t, "abstain") for t in truth])
    assert m["abstentions"] == 42 and m["errors"] == 0
    assert m["balanced_accuracy"] == m["coverage"] == m["accuracy"] == 0


def test_duplicate_and_unknown_predictions_rejected():
    _, truth, _ = load_review()
    p = perfect_predictions(truth)[0]
    for preds in ([p,p], [Prediction("pg-9999", "safe")]):
        with pytest.raises(ValidationError):
            score(truth, preds)


def test_single_class_dataset_does_not_fabricate_balanced_accuracy():
    _, truth, _ = load_review()
    safe = {k:v for k,v in truth.items() if not v.unsafe}
    m = score(safe, [Prediction(k,"safe") for k in safe])
    assert m["balanced_accuracy"] is None


def test_bad_jsonl_line_number(tmp_path):
    path = tmp_path / "x.jsonl"
    path.write_text('{}\n{\n')
    with pytest.raises(ValidationError, match="x.jsonl:2"):
        read_jsonl(path)


def test_truth_is_not_derived_from_baseline():
    from prguardbench.baselines import review
    cases, truth, _ = load_review()
    m = score(truth, [review(c) for c in cases])
    assert m["fp"] > 0
    assert m["accuracy"] < 1
    assert len(m["cases"]) == len(cases)
