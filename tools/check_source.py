"""Offline source hygiene check. Not a replacement for a full linter/type checker."""
import ast
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
failures = []
checked = 0
for directory in ("src", "tests", "tools", "examples"):
    for path in sorted((root / directory).rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        checked += 1
        try:
            ast.parse(source, filename=str(path), feature_version=(3, 10))
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(root)}: Python 3.10 syntax: {exc}")
        if not source.endswith("\n"):
            failures.append(f"{path.relative_to(root)}: missing final newline")
        for number, line in enumerate(source.splitlines(), 1):
            if line.rstrip() != line:
                failures.append(f"{path.relative_to(root)}:{number}: trailing whitespace")
            if line.startswith(("<<<<<<< ", ">>>>>>> ")):
                failures.append(f"{path.relative_to(root)}:{number}: conflict marker")
if failures:
    print("\n".join(failures), file=sys.stderr)
    raise SystemExit(1)
print(f"Source syntax/whitespace check: PASS ({checked} Python files; 3.10 syntax grammar)")
