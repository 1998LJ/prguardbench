"""Load authored cases separately from labels; validate content-addressed manifests."""
from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path

from .models import MAX_JSON_BYTES, ReviewCase, Truth, ValidationError, digest


def read_jsonl(path: Path) -> list[dict]:
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValidationError(f"Input file too large: {path.name}")
    out = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Invalid JSON at {path.name}:{line_no}") from exc
    return out


def load_review() -> tuple[list[ReviewCase], dict[str, Truth], dict]:
    root = files("prguardbench").joinpath("data")
    raw_inputs = [json.loads(x) for x in root.joinpath("review_inputs.jsonl")
                  .read_text(encoding="utf-8").splitlines() if x.strip()]
    raw_truth = [json.loads(x) for x in root.joinpath("review_truth.jsonl")
                 .read_text(encoding="utf-8").splitlines() if x.strip()]
    manifest = json.loads(root.joinpath("manifest.json").read_text(encoding="utf-8"))
    cases = [ReviewCase.from_dict(x) for x in raw_inputs]
    truths = [Truth.from_dict(x) for x in raw_truth]
    labels = {t.case_id: t for t in truths}
    ids = {c.case_id for c in cases}
    if len(ids) != len(cases) or len(labels) != len(truths) or ids != labels.keys():
        raise ValidationError("Dataset IDs are duplicated or labels are missing")
    if manifest["input_sha256"] != digest(raw_inputs) or manifest["truth_sha256"] != digest(raw_truth):
        raise ValidationError("Dataset content hash mismatch")
    if manifest["count"] != len(cases):
        raise ValidationError("Dataset size mismatch")
    for case in cases:
        if not set(labels[case.case_id].evidence_paths) <= set(case.changed_files):
            raise ValidationError(f"Truth evidence is not a changed file: {case.case_id}")
    return cases, labels, manifest


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in records), encoding="utf-8")
