import pytest
from prguardbench.models import Prediction, ReviewCase, Truth, ValidationError, files_map, safe_path

@pytest.mark.parametrize("bad", ["", "../x", "/tmp/x", "C:/x", "a\\b", "a//b", "a/./b", ".git/config", "a\nfoo", "x:stream", "a/../b"])
def test_reject_unsafe_paths(bad):
    with pytest.raises(ValidationError):
        safe_path(bad)

@pytest.mark.parametrize("good", ["src/main.py", "tests/test_x.py", ".github/workflows/ci.yml"])
def test_safe_paths(good):
    assert safe_path(good) == good

@pytest.mark.parametrize("mapping", [{"A.py":"", "a.py":""}, {"src":"", "src/a.py":""}, {"x":123}])
def test_invalid_snapshot(mapping):
    with pytest.raises(ValidationError):
        files_map(mapping)

def test_prediction_round_trip():
    p = Prediction("pg-0001", "unsafe", ("removed_assertion",), ({"path":"tests/test_x.py", "reason":"lost exact check", "line":5},))
    assert Prediction.from_dict(p.to_dict()) == p

@pytest.mark.parametrize("mutate", [
    {"decision":"maybe"}, {"categories":["not_real"]}, {"decision":"safe", "categories":["removed_assertion"]},
    {"categories":[]}, {"evidence":[{"path":"../a", "reason":"bad"}]},
    {"evidence":[{"path":"tests/a.py", "reason":"bad", "line":0}]}, {"extra":True},
])
def test_invalid_predictions(mutate):
    p = {"case_id":"pg-0001", "decision":"unsafe", "categories":["removed_assertion"], "evidence":[]}
    p.update(mutate)
    with pytest.raises(ValidationError):
        Prediction.from_dict(p)

def test_false_truth_label_rejected():
    with pytest.raises(ValidationError):
        Truth.from_dict({"case_id":"pg-0001", "unsafe":False, "categories":["removed_test"],
                         "evidence_paths":[], "rationale":"bad", "family":"x"})

def test_case_rejects_label_leak_field():
    with pytest.raises(ValidationError):
        ReviewCase.from_dict({"case_id":"pg-0001", "task":"x", "policy":{"allowed_paths":["src/*"],"requires_tests":False},
                              "before":{}, "after":{}, "unsafe":True})
