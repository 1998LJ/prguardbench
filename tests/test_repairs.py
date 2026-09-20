import pytest
from prguardbench.models import ValidationError
from prguardbench.repairs import demo_submissions, docker_command, export_tasks, grade_repairs, parse_submission


@pytest.fixture(scope="module")
def measured():
    return {name: grade_repairs(s, backend="trusted-local") for name,s in demo_submissions().items()}


def test_reference_repair_passes_every_contract(measured):
    r = measured["reference-fix"]
    assert r["n_tasks"] == r["native_passes"] == r["functional_passes"] == r["policy_passes"] == r["joint_passes"] == 5
    assert sum(x["oracle_checks_total"] for x in r["tasks"]) == 26


def test_ci_green_can_still_be_bad(measured):
    r = measured["green-only"]
    assert r["native_passes"] == 5
    assert r["functional_passes"] == r["policy_passes"] == r["joint_passes"] == 0


def test_no_change_not_rewarded(measured):
    r = measured["no-change"]
    assert r["native_passes"] == r["functional_passes"] == r["joint_passes"] == 0
    assert r["policy_passes"] == 5


def test_default_does_not_silently_execute_on_host(monkeypatch):
    monkeypatch.setattr("prguardbench.repairs.shutil.which", lambda _: None)
    with pytest.raises(ValidationError, match="No automatic unsafe fallback"):
        grade_repairs(demo_submissions()["reference-fix"])


def test_docker_security_flags():
    cmd = docker_command("sha256:123", "/tmp/a", "/tmp/w.py", "oracle", "container-test")
    for flag in ("--read-only", "--cap-drop", "--network", "--pids-limit", "--memory", "--user", "--security-opt"):
        assert flag in cmd
    assert cmd[cmd.index("--network")+1] == "none"
    assert not any("docker.sock" in x or x == "--privileged" for x in cmd)


def test_export_excludes_oracle_answers(tmp_path):
    export_tasks(tmp_path)
    assert (tmp_path/"repair-001/TASK.md").exists()
    assert not list(tmp_path.rglob("*oracle*"))
    with pytest.raises(ValidationError):
        export_tasks(tmp_path)

@pytest.mark.parametrize("path", ["../escape", ".git/config", "/etc/passwd", "C:\\bad"])
def test_submission_paths_rejected(path):
    s = demo_submissions()["reference-fix"]
    s["submissions"][0]["files"] = {path:"hello"}
    with pytest.raises(ValidationError):
        parse_submission(s)


def test_missing_submission_has_no_credit():
    s = demo_submissions()["reference-fix"]
    s["submissions"] = []
    r = grade_repairs(s, backend="trusted-local")
    assert r["joint_passes"] == 0 and r["n_tasks"] == 5
    assert all(x["status"] == "missing" for x in r["tasks"])


def test_zero_native_tests_not_pass(tmp_path):
    s = demo_submissions()["reference-fix"]
    s["submissions"] = s["submissions"][:1]
    s["submissions"][0]["files"]["tests/test_solution.py"] = "# no tests\n"
    r = grade_repairs(s, backend="trusted-local")
    assert r["tasks"][0]["native_pass"] is False
    assert r["tasks"][0]["functional_pass"] is True
    assert r["tasks"][0]["joint_pass"] is False
