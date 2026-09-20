"""Measured runs with separate inputs/labels, deterministic case order and provenance."""
from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .adapters import command_prediction
from .baselines import review
from .dataset import load_review, read_jsonl, write_json, write_jsonl
from .models import Prediction, ValidationError, digest
from .scoring import score


def run_review(adapter="ast-diff", *, name=None, command=None, timeout=60,
               pass_env=(), predictions_path=None, model_id=None):
    cases, truth, manifest = load_review()
    start = time.monotonic()
    if predictions_path:
        predictions = [Prediction.from_dict(x) for x in read_jsonl(Path(predictions_path))]
        kind = "external-supplied"
    elif adapter == "command":
        predictions = [command_prediction(c, command, timeout, pass_env) for c in cases]
        kind = "external-command"
    else:
        predictions = [review(c, adapter) for c in cases]
        kind = "static-control"
    metrics = score(truth, predictions)
    return {
        "schema": "prguardbench.review-report.v1", "benchmark_version": __version__,
        "name": name or adapter, "kind": kind, "model_id": model_id,
        "model_identity_note": "Externally supplied identity, not authenticated by the harness." if model_id else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.monotonic() - start, 6),
        "implementation_sha256": digest({p.name: p.read_text(encoding="utf-8") for p in Path(__file__).parent.glob("*.py")}),
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "dataset": manifest, "metrics": metrics,
        "predictions_sha256": digest([p.to_dict() for p in predictions]),
        "adapter_config": {"adapter": adapter, "command_sha256": digest(command) if command else None,
                           "timeout_seconds": timeout if adapter == "command" else None,
                           "environment_names": list(pass_env)},
    }, predictions


def save_run(out, report, predictions):
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValidationError("Output directory is not empty; use a fresh run directory")
    write_json(out / "report.json", report)
    write_jsonl(out / "predictions.jsonl", [p.to_dict() for p in predictions])


def load_report(path):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if report.get("schema") != "prguardbench.review-report.v1":
        raise ValidationError("Not a review report")
    _, truth, manifest = load_review()
    if report.get("dataset") != manifest:
        raise ValidationError("Report dataset does not match installed suite")
    predictions = [Prediction.from_dict(x["prediction"]) for x in report["metrics"]["cases"]]
    if score(truth, predictions) != report["metrics"]:
        raise ValidationError("Report aggregate metrics do not match per-case predictions")
    return report
