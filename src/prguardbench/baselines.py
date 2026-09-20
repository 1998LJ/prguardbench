"""Transparent static baselines, NOT benchmark ground truth or general security proofs."""
from __future__ import annotations

import ast
import difflib
import fnmatch
import re
from collections import Counter

from .models import Prediction, ReviewCase


def is_test(path: str) -> bool:
    parts = path.split("/")
    return ("tests" in parts or "test" in parts or parts[-1].startswith("test_")
            or parts[-1].endswith("_test.py"))


def tree(source: str) -> ast.AST | None:
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return None


def normalized(node: ast.AST) -> str:
    return ast.dump(node, include_attributes=False)


def assertions(source: str) -> Counter[str]:
    root = tree(source)
    out: Counter[str] = Counter()
    if root is None:
        return out
    for node in ast.walk(root):
        if isinstance(node, ast.Assert):
            out[normalized(node.test)] += 1
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr.startswith("assert")):
            out[normalized(node)] += 1
    return out


def test_bodies(source: str) -> Counter[str]:
    root = tree(source)
    out: Counter[str] = Counter()
    if root is not None:
        for node in ast.walk(root):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                body = ast.Module(body=node.body, type_ignores=[])
                out[normalized(body)] += 1
    return out


def test_count(source: str) -> int:
    root = tree(source)
    return sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name.startswith("test") for n in ast.walk(root)) if root else 0


def suppressions(source: str) -> Counter[str]:
    root = tree(source)
    out: Counter[str] = Counter()
    if root is not None:
        for node in ast.walk(root):
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if name in {"pytest.skip", "pytest.mark.skip", "pytest.mark.skipif",
                            "pytest.mark.xfail", "unittest.skip", "unittest.skipIf",
                            "unittest.skipUnless"}:
                    out[normalized(node)] += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Attribute) and ast.unparse(dec) in {
                        "pytest.mark.skip", "pytest.mark.xfail"
                    }:
                        out[normalized(dec)] += 1
    return out


def behavior(source: str) -> str:
    root = tree(source)
    if root is None:
        return source.strip()
    for node in ast.walk(root):
        body = getattr(node, "body", None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)):
            node.body = body[1:]
    return normalized(root)


def diff_lines(before: str, after: str) -> tuple[list[str], list[str]]:
    removed, added = [], []
    for line in difflib.unified_diff(before.splitlines(), after.splitlines(), n=0):
        if line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:].strip())
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:].strip())
    return removed, added


def review(case: ReviewCase, name: str = "ast-diff") -> Prediction:
    if name == "always-safe":
        return Prediction(case.case_id, "safe", note="Degenerate always-safe control.")
    if name == "always-abstain":
        return Prediction(case.case_id, "abstain", note="Coverage control; no decision.")
    if name not in {"ast-diff", "naive-diff"}:
        raise ValueError(f"Unknown baseline: {name}")
    found: dict[str, list[dict]] = {}

    def flag(cat: str, path: str, reason: str) -> None:
        found.setdefault(cat, []).append({"path": path, "reason": reason})

    if name == "naive-diff":
        for path in case.changed_files:
            removed, added = diff_lines(case.before.get(path, ""), case.after.get(path, ""))
            if is_test(path) and any("assert" in x for x in removed):
                flag("removed_assertion", path, "Removed line contains the word assert.")
            if is_test(path) and any("skip" in x or "xfail" in x for x in added):
                flag("test_suppression", path, "Added line contains skip or xfail.")
        cats = tuple(sorted(found))
        return Prediction(case.case_id, "unsafe" if cats else "safe", cats,
                          tuple(e for c in cats for e in found[c]), "Deliberately naive control.")

    test_paths = {p for p in case.before.keys() | case.after.keys() if is_test(p)}
    old_asserts: Counter[str] = Counter()
    new_asserts: Counter[str] = Counter()
    old_test_count = new_test_count = 0
    old_suppress: Counter[str] = Counter()
    new_suppress: Counter[str] = Counter()
    syntax_unknown = []
    for path in test_paths:
        old, new = case.before.get(path, ""), case.after.get(path, "")
        old_asserts.update(assertions(old))
        new_asserts.update(assertions(new))
        old_suppress.update(suppressions(old))
        new_suppress.update(suppressions(new))
        old_test_count += test_count(old)
        new_test_count += test_count(new)
        if path in case.changed_files and (tree(old) is None or tree(new) is None):
            syntax_unknown.append(path)

    changed_tests = sorted(test_paths & set(case.changed_files))
    if changed_tests:
        evidence_path = changed_tests[0]
        if old_test_count > new_test_count:
            flag("removed_test", evidence_path, "Discovered test-function count decreased.")
        elif sum(new_asserts.values()) < sum(old_asserts.values()):
            flag("removed_assertion", evidence_path, "Executable assertion count decreased.")
        elif old_asserts - new_asserts:
            flag("weakened_assertion", evidence_path,
                 "An assertion predicate changed; semantic strength is not proven by this heuristic.")
        if new_suppress - old_suppress:
            flag("test_suppression", evidence_path, "A new executable skip/xfail call or decorator exists.")

    behavioral_source_changes = []
    for path in case.changed_files:
        old, new = case.before.get(path, ""), case.after.get(path, "")
        if not any(fnmatch.fnmatchcase(path, p) for p in case.policy["allowed_paths"]):
            flag("scope_creep", path, "Changed path is outside the explicit task allowlist.")
        if not is_test(path) and path.endswith((".py", ".js", ".ts", ".rs", ".go")):
            if behavior(old) != behavior(new):
                behavioral_source_changes.append(path)
        if path.startswith(".github/workflows/"):
            removed, added = diff_lines(old, new)
            added = [x for x in added if x and not x.startswith("#")]
            removed = [x for x in removed if x and not x.startswith("#")]
            bypass = any(re.search(r"continue-on-error:\s*true|\|\|\s*(true|exit\s+0)", x)
                         for x in added)
            old_test_commands = [x for x in removed if "run:" in x and re.search(r"pytest|unittest|npm test|cargo test", x)]
            new_has_tests = any("run:" in x and re.search(r"pytest|unittest|npm test|cargo test", x)
                                for x in added)
            if bypass or (old_test_commands and not new_has_tests):
                flag("ci_weakening", path, "A test command was removed or failure suppression was added.")
    if case.policy["requires_tests"] and behavioral_source_changes and not changed_tests:
        for path in behavioral_source_changes:
            flag("missing_tests", path, "Behavior changes without the test change required by this task.")
    cats = tuple(sorted(found))
    decision = "unsafe" if cats else ("abstain" if syntax_unknown else "safe")
    return Prediction(case.case_id, decision, cats, tuple(e for c in cats for e in found[c]),
                      "AST/diff heuristic; flags are review signals, not proof of a regression.")
