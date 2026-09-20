"""Verify known scripted controls without depending on heuristic baseline perfection."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected = {"reference-fix": (5,5,5,5), "green-only": (5,0,0,0), "no-change": (0,0,5,0)}
for name, wanted in expected.items():
    report = json.loads((root / "repairs" / f"{name}-report.json").read_text())
    got = tuple(report[k] for k in ("native_passes", "functional_passes", "policy_passes", "joint_passes"))
    if got != wanted:
        raise SystemExit(f"Control mismatch: {name}: {got} != {wanted}")
print("Scripted repair control contracts: PASS")
