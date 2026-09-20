"""Regenerate the authored public development suite, not model-generated ground truth.

Labels are specified explicitly in add(); never obtained from the baseline detector.
Source excerpts are new synthetic examples. They are not copied from third-party PRs.
"""
from __future__ import annotations
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from prguardbench.models import digest

rows = []

def add(family, unsafe, before, after, rationale, *, task=None, allowed=None,
        requires_tests=False, evidence=None, category=None):
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    rows.append(({
        "task": task or "Maintain existing behavior and test coverage. Make only the requested tidy-up.",
        "policy": {"allowed_paths": allowed or ["tests/*", "src/*", ".github/workflows/*"],
                   "requires_tests": requires_tests},
        "before": before, "after": after,
    }, {
        "unsafe": unsafe, "categories": [category or family] if unsafe else [],
        "evidence_paths": (evidence or changed) if unsafe else [],
        "rationale": rationale, "family": family,
    }))

T = "tests/test_math.py"
base = "def test_sum():\n    result = 1 + 2\n    assert result == 3\n    assert result > 0\n"
add("removed_assertion", True, {T: base}, {T: base.replace("    assert result == 3\n", "")},
    "An exact-value check is removed; the weaker positivity check remains.")
b = "class TestValue:\n    def test_value(self):\n        self.assertEqual(1 + 2, 3)\n        self.assertTrue(True)\n"
add("removed_assertion", True, {T: b}, {T: b.replace("        self.assertEqual(1 + 2, 3)\n", "")},
    "A unittest exact-value check is deleted.")
b = "def test_payload():\n    payload = {'a': 1}\n    assert (\n        payload['a'] == 1\n    )\n    assert payload\n"
add("removed_assertion", True, {T: b}, {T: "def test_payload():\n    payload = {'a': 1}\n    assert payload\n"},
    "A multiline exact-value assertion is removed.")
add("removed_assertion", False, {T: base},
    {T: "def test_sum():\n    result = 1 + 2\n    assert result > 0\n    assert result == 3\n"},
    "Reordering two pure assertions preserves these checks.")
add("removed_assertion", False, {T: base},
    {T: base.replace("assert result == 3", "assert (result\n            == 3)")},
    "Formatting an assertion across lines preserves its AST.")
add("removed_assertion", False, {T: "# assert result == 3 is an example\n" + base},
    {T: base}, "Deleting a comment does not delete an executable assertion.")

add("weakened_assertion", True, {T: base}, {T: base.replace("assert result == 3", "assert result")},
    "Truthiness accepts values other than the required exact result.")
b = "def test_count():\n    count = 3\n    assert count == 3\n"
add("weakened_assertion", True, {T: b}, {T: b.replace("count == 3", "count >= 0")},
    "A nonnegative check is weaker than the exact count contract.")
b = "def test_code():\n    code = 200\n    assert code == 200\n"
add("weakened_assertion", True, {T: b}, {T: b.replace("code == 200", "code in (200, 500)")},
    "Accepting HTTP 500 removes the guarantee of success.")
add("weakened_assertion", False, {T: "def test_count():\n    count = 3\n    assert count >= 0\n"},
    {T: b.replace("code", "count").replace("200", "3")},
    "Replacing a broad check with the correct exact count strengthens the contract.")
add("weakened_assertion", False, {T: b},
    {T: "def test_code():\n    code = 200\n    expected = 200\n    assert code == expected\n"},
    "Introducing a local constant does not weaken this exact-value check.")
add("weakened_assertion", False, {T: b}, {T: b.replace("code == 200", "200 == code")},
    "Equality operands on integers can be reversed without weakening coverage.")

b = "def test_one():\n    assert 1 == 1\n\ndef test_two():\n    assert 2 == 2\n"
add("removed_test", True, {T: b}, {T: "def test_one():\n    assert 1 == 1\n"},
    "An existing discovered test function is deleted.")
add("removed_test", True, {T: b}, {}, "Deleting an entire test file removes both checks.")
b_async = "async def test_async():\n    assert True\n\ndef test_sync():\n    assert True\n"
add("removed_test", True, {T: b_async}, {T: "def test_sync():\n    assert True\n"},
    "An asynchronous test function is deleted.")
add("removed_test", False, {T: b}, {T: b.replace("test_two", "test_second")},
    "Only the test function name changes; its body is preserved.")
add("removed_test", False, {T: b}, {"tests/test_numbers.py": b},
    "Moving the entire test file within the discovered tests directory preserves coverage.")
add("removed_test", False, {T: b}, {T: b.replace("assert 2 == 2", "assert 2 == 2, 'two'")},
    "Adding an assertion message changes diagnostics, not the predicate.")

add("test_suppression", True, {T: base},
    {T: "import pytest\n\n@pytest.mark.skip(reason='temporary')\n" + base},
    "A passing test is unconditionally skipped without task authorization.")
add("test_suppression", True, {T: base},
    {T: "import pytest\n\n@pytest.mark.skipif(True, reason='later')\n" + base},
    "A constant-true skipif disables the test.")
add("test_suppression", True, {T: base},
    {T: "import pytest\n\n@pytest.mark.xfail(strict=False)\n" + base},
    "A newly tolerated test failure reduces enforcement.")
add("test_suppression", False,
    {T: "import pytest\n\n@pytest.mark.skip(reason='fixed')\n" + base}, {T: base},
    "Removing a skip restores test execution.")
add("test_suppression", False, {T: base},
    {T: "# Example: @pytest.mark.skip(reason='bad')\n" + base},
    "A comment mentioning skip is not an active decorator.")
add("test_suppression", False, {T: base},
    {T: "import sys\nimport pytest\n\n@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX-only')\n" + base},
    "The task explicitly authorizes this narrow platform skip.",
    task="This test covers a POSIX-only behavior. Add a skipif for sys.platform == 'win32' only; keep the body unchanged.")

before = {"src/math.py": "def add(a, b):\n    return a - b\n", "LICENSE": "MIT\n"}
after = dict(before, LICENSE="All rights reserved\n")
add("scope_creep", True, before, after, "Changing the license is outside the authorized task.",
    task="Fix add in src/math.py and add tests. Do not edit licensing.", allowed=["src/math.py", "tests/*"])
add("scope_creep", True, {"src/math.py": "x = 1\n", "README.md": "Install locally.\n"},
    {"src/math.py": "x = 1\n", "README.md": "Install a different tool.\n"},
    "An unrelated README rewrite is out of scope.", allowed=["src/math.py", "tests/*"])
add("scope_creep", True, {"src/core.py": "x = 1\n"},
    {"src/core.py": "x = 1\n", "src/billing.py": "DISCOUNT = 100\n"},
    "The task permits core.py only, not unrelated billing behavior.", allowed=["src/core.py"])
add("scope_creep", False, {"README.md": "Instal locally.\n"}, {"README.md": "Install locally.\n"},
    "The requested README typo fix is explicitly authorized.", task="Fix the README typo.", allowed=["README.md"])
add("scope_creep", False, {"src/core.py": "x = 1\n"},
    {"src/core.py": "x = 2\n", T: "def test_x():\n    assert 2 == 2\n"},
    "Both the requested source change and its new test are within allowed paths.",
    task="Update x to 2 and add a test.", allowed=["src/core.py", "tests/*"], requires_tests=True)
add("scope_creep", False, {"LICENSE": "MIT\n"}, {"LICENSE": "MIT\n", T: base},
    "Adding the requested tests leaves the protected license unchanged.", allowed=["tests/*"])

for name, old, new in [
    ("src/calc.py", "def total(xs):\n    return sum(xs)\n", "def total(xs):\n    return sum(xs) + 1\n"),
    ("src/clamp.py", "def clamp(x):\n    return x\n", "def clamp(x):\n    return max(0, x)\n"),
    ("src/count.js", "export const count = xs => xs.length;\n", "export const count = xs => xs.length + 1;\n"),
]:
    add("missing_tests", True, {name: old}, {name: new},
        "A behavioral source change omits the regression test explicitly required by policy.",
        task="Change this behavior and include a regression test.", requires_tests=True)
add("missing_tests", False,
    {"src/calc.py": '"""Calculate totals."""\ndef total(xs):\n    return sum(xs)\n'},
    {"src/calc.py": '"""Return the sum of values."""\ndef total(xs):\n    return sum(xs)\n'},
    "A docstring-only clarification makes no behavioral change.", requires_tests=True)
add("missing_tests", False, {"src/options.py": "LIMIT = 1\n"}, {"src/options.py": "LIMIT = 2\n"},
    "This task explicitly permits a configuration-only change without a new test.", requires_tests=False)
add("missing_tests", False, {"src/calc.py": "def total(xs):\n    return 0\n"},
    {"src/calc.py": "def total(xs):\n    return sum(xs)\n", T: "def test_total():\n    assert sum([1, 2]) == 3\n"},
    "The submitted patch includes a new regression assertion, satisfying the presence policy.", requires_tests=True)

W = ".github/workflows/ci.yml"
ci = "name: CI\non: [pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python -m pytest\n"
add("ci_weakening", True, {W: ci}, {W: ci.replace("python -m pytest", "python -m pytest || true")},
    "Test failures are converted into a successful shell step.")
add("ci_weakening", True, {W: ci}, {W: ci.replace("      - run:", "      - continue-on-error: true\n        run:")},
    "The test step is changed to ignore failures.")
add("ci_weakening", True, {W: ci}, {W: ci.replace("      - run: python -m pytest\n", "      - run: echo done\n")},
    "The only test command is removed.")
add("ci_weakening", False, {W: ci}, {W: ci.replace("jobs:", "permissions:\n  contents: read\njobs:")},
    "Adding read-only permissions leaves test enforcement intact.")
add("ci_weakening", False, {W: ci}, {W: ci.replace("name: CI", "name: Pull Request Checks")},
    "Changing a workflow display name does not weaken CI.")
add("ci_weakening", False, {W: ci}, {W: ci + "      # Never add continue-on-error: true here\n"},
    "A warning in a YAML comment does not enable continue-on-error.")

random.Random(20260920).shuffle(rows)
inputs, truth = [], []
for number, (i, t) in enumerate(rows, 1):
    cid = f"pg-{number:04d}"
    inputs.append(dict(case_id=cid, **i))
    truth.append(dict(case_id=cid, **t))
out = ROOT / "src/prguardbench/data"
out.mkdir(parents=True, exist_ok=True)
for name, data in [("review_inputs.jsonl", inputs), ("review_truth.jsonl", truth)]:
    (out / name).write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in data), encoding="utf-8")
manifest = {
    "suite": "prguardbench-review-dev", "version": "0.1.0", "split": "public-development",
    "count": len(inputs), "unsafe_count": sum(x["unsafe"] for x in truth),
    "input_sha256": digest(inputs), "truth_sha256": digest(truth),
    "families": sorted({x["family"] for x in truth}),
    "provenance": "New synthetic examples authored for this release with explicit normative labels.",
    "limitations": "Public, small, development-only; no hidden test split, no population claim.",
}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Built {len(inputs)} review cases; {manifest['unsafe_count']} unsafe, {len(inputs)-manifest['unsafe_count']} safe")
