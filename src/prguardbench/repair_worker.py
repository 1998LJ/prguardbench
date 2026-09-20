"""Execution worker. The controller compares returned values with independent oracles.

Only use trusted-local mode for code you have inspected. Docker limits host exposure;
it is not a claim that arbitrary hostile candidates cannot manipulate observations.
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path


def main():
    mode, workspace = sys.argv[1], Path(sys.argv[2])
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(workspace / "src"))
    if mode == "native":
        suite = unittest.defaultTestLoader.discover(str(workspace / "tests"))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        # Zero collected tests must not appear as a passing test suite.
        return 0 if result.wasSuccessful() and result.testsRun > 0 else 1
    request = json.load(sys.stdin)
    spec = importlib.util.spec_from_file_location("candidate_solution", workspace / "src/solution.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function = getattr(module, request["function"])
    observations = []
    for args in request["arguments"]:
        try:
            observations.append({"value": function(*args)})
        except Exception as exc:
            observations.append({"exception": type(exc).__name__})
    print(json.dumps({"observations": observations}, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
