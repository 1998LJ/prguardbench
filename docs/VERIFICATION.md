# Delivery verification

Local verification date: 2026-09-20. Runtime: Linux, CPython 3.13.5.

## Executed successfully

| Check | Observed result |
| :--- | :--- |
| `python -m pytest -q` | 77 tests passed |
| `python -m coverage run --source=src/prguardbench -m pytest -q` | 77 tests passed |
| `python -m coverage report` | 83% aggregate statement coverage; scorer 100%. Subprocess worker execution is not counted by this coverage run. |
| `python tools/check_source.py` | 23 Python files parsed with Python 3.10 grammar; final-newline/whitespace/conflict-marker checks passed |
| `prguardbench validate` | 42 cases; 21 unsafe + 21 safe; manifest hashes matched |
| Four static review controls | All 42 cases evaluated for each; no adapter errors |
| Three scripted repair controls | reference-fix: 5/5 joint; green-only: 5/5 native but 0/5 joint; no-change: 0/5 joint |
| JSON command adapter protocol control | 42 responses; 0 errors; balanced accuracy 0.5 (expected always-safe behavior) |
| Offline wheel build | `pip wheel --no-build-isolation --no-deps .` succeeded using installed setuptools |
| Fresh virtualenv wheel installation | `pip install --no-index --no-deps <wheel>` succeeded |
| Installed wheel run outside source directory | Version, corpus validation, review demo and all scripted repair controls succeeded |
| Browser rendering | Chromium rendered self-contained HTML at 1280px and 390px; no page errors; document width stayed within viewport |

The initial browser `file://` navigation was blocked by the environment. Visual QA used
Chromium `set_content` with the exact generated HTML, not a different mockup.

## Not executed / not claimed

- Docker runtime integration: Docker is not installed here. Construction/safety/fail-closed
  tests pass; the separate Docker CI job is provided but has not run on GitHub.
- Remote GitHub Actions: definitions are supplied, but no repository was created or modified.
- Ruff / twine / isolated `python -m build`: development-tool download failed because the
  environment cannot resolve the package index. No PASS is claimed. Source hygiene and
  setuptools' installed build backend were used for executed offline checks.
- Python 3.10/3.11/3.12 runtime matrix: only 3.13.5 was executed locally; CI defines the rest.
- Commercial model/agent runs, paid API calls, model rankings, PyPI publication and external adoption.

## Important interpretation

The 90.5% AST/diff balanced accuracy and 19.0% false-positive rate describe this authored
public development suite only. Four false positives remain visible; no label was changed
to hide them. The repair controls are deliberately scripted, not attributed to any model.

The code checker is syntax/source hygiene, not a replacement for Ruff or a type checker.
Hashes identify the delivered data/source/predictions; they do not authenticate a model
or establish an independently audited security guarantee.
