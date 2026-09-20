import sys
import pytest
from prguardbench.adapters import command_prediction
from prguardbench.dataset import load_review
from prguardbench.models import ValidationError


def command(script):
    return [sys.executable, "-I", "-S", "-c", script]


def test_wrapper_label_free_and_correct_id():
    case = load_review()[0][0]
    script = """import json,sys
r=json.load(sys.stdin)
assert set(r)=={'schema','case'}
assert not {'unsafe','rationale','family','categories'} & r['case'].keys()
print(json.dumps({'case_id':r['case']['case_id'],'decision':'safe','categories':[],'evidence':[]}))
"""
    assert command_prediction(case, command(script)).decision == "safe"

@pytest.mark.parametrize("script", ["print('not-json')", "raise SystemExit(3)",
    "print('{}')", "print('{\"case_id\":\"pg-9999\",\"decision\":\"safe\",\"categories\":[],\"evidence\":[]}')"])
def test_adapter_errors_not_safe(script):
    assert command_prediction(load_review()[0][0], command(script)).decision == "error"


def test_timeout_is_error():
    p = command_prediction(load_review()[0][0], command("import time;time.sleep(5)"), timeout=.05)
    assert p.decision == "error" and "timed out" in p.note


def test_output_limit_is_error():
    p = command_prediction(load_review()[0][0], command("print('x'*1100000)"))
    assert p.decision == "error"


def test_secrets_not_inherited(monkeypatch):
    monkeypatch.setenv("BENCH_TEST_SECRET", "sensitive-token")
    p = command_prediction(load_review()[0][0], command("import os;assert 'BENCH_TEST_SECRET' not in os.environ;print('{}')"))
    assert "code" not in p.note
    assert "sensitive-token" not in p.note


def test_explicit_env_missing_is_validation_error():
    with pytest.raises(ValidationError):
        command_prediction(load_review()[0][0], command("pass"), pass_env=("PG_NO_SUCH_ENV_987",))
