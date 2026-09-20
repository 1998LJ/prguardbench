import copy
import json
import pytest
from prguardbench.cli import main
from prguardbench.dataset import write_json
from prguardbench.models import ValidationError
from prguardbench.reporting import html_report, markdown
from prguardbench.runner import load_report, run_review


def test_validate_and_export(tmp_path, capsys):
    assert main(["validate"]) == 0
    assert "42" in capsys.readouterr().out
    assert main(["export", "--out", str(tmp_path/"requests.jsonl")]) == 0
    assert len((tmp_path/"requests.jsonl").read_text().splitlines()) == 42
    assert main(["export", "--out", str(tmp_path/"requests.jsonl")]) == 2


def test_full_run_report_and_no_overwrite(tmp_path):
    out = tmp_path / "run"
    assert main(["run", "--out", str(out)]) == 0
    r = load_report(out/"report.json")
    assert r["metrics"]["n_cases"] == 42
    assert (out/"index.html").exists()
    assert main(["run", "--out", str(out)]) == 2


def test_output_escaping():
    r,_ = run_review(name='<script>alert("x")</script>')
    html = html_report([r])
    assert '<script>alert' not in html
    assert '&lt;script&gt;' in html
    assert 'Content-Security-Policy' in html


def test_mismatched_corpora_refused():
    a,_ = run_review()
    b = copy.deepcopy(a)
    b["name"] = "other"
    b["dataset"]["input_sha256"] = "bad"
    with pytest.raises(ValidationError):
        markdown([a,b])


def test_duplicate_names_refused():
    a,_=run_review()
    with pytest.raises(ValidationError):
        markdown([a,a])


def test_tampered_aggregate_refused(tmp_path):
    r,p = run_review()
    r["metrics"]["accuracy"] = 1
    write_json(tmp_path/"bad.json",r)
    with pytest.raises(ValidationError, match="metrics"):
        load_report(tmp_path/"bad.json")


def test_command_requires_opt_in(tmp_path):
    assert main(["run", "--adapter", "command", "--out", str(tmp_path/"out")]) == 2


def test_missing_predictions_returns_error_but_writes_report(tmp_path):
    p = tmp_path/"pred.jsonl"
    p.write_text("")
    out=tmp_path/"run"
    assert main(["run", "--predictions", str(p), "--out", str(out)]) == 2
    report=json.loads((out/"report.json").read_text())
    assert report["metrics"]["errors"] == 42


def test_export_and_grade_cli(tmp_path):
    assert main(["repair-export", "--out", str(tmp_path/"tasks")]) == 0
