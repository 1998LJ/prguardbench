"""Validated, versioned interchange types. No target code is executed here."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

SCHEMA = "prguardbench.review.v1"
CATEGORIES = frozenset({
    "removed_assertion", "weakened_assertion", "removed_test", "test_suppression",
    "scope_creep", "missing_tests", "ci_weakening",
})
MAX_CONTENT_BYTES = 256_000
MAX_FILES = 100
MAX_JSON_BYTES = 8_000_000


class ValidationError(ValueError):
    """Untrusted input violated the benchmark contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def safe_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 240:
        raise ValidationError("File path must be a nonempty relative POSIX path (<=240 chars)")
    # Reject Windows drives/ADS, backslashes, control characters and ambiguous normalization.
    if "\\" in value or ":" in value or any(ord(c) < 32 for c in value):
        raise ValidationError(f"Unsafe file path: {value!r}")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        raise ValidationError(f"Unsafe file path: {value!r}")
    if any(x.casefold() == ".git" for x in p.parts):
        raise ValidationError("Writing Git internals is prohibited")
    return value


def text(value: Any, name: str, limit: int = MAX_CONTENT_BYTES) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > limit:
        raise ValidationError(f"{name} must be text of at most {limit} UTF-8 bytes")
    return value


def object_value(value: Any, name: str) -> dict:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be a JSON object")
    return value


def string_list(value: Any, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValidationError(f"{name} must be a list of strings")
    if len(value) != len(set(value)):
        raise ValidationError(f"{name} contains duplicates")
    return tuple(value)


def files_map(value: Any) -> dict[str, str]:
    obj = object_value(value, "files")
    if len(obj) > MAX_FILES:
        raise ValidationError("Too many files")
    normalized = {safe_path(k): text(v, f"content of {k}") for k, v in obj.items()}
    names = list(normalized)
    if len({n.casefold() for n in names}) != len(names):
        raise ValidationError("Case-insensitive file path collision")
    if any(a != b and b.startswith(a + "/") for a in names for b in names):
        raise ValidationError("A file cannot also be a directory")
    return normalized


@dataclass(frozen=True)
class ReviewCase:
    case_id: str
    task: str
    policy: dict[str, Any]
    before: dict[str, str]
    after: dict[str, str]

    @classmethod
    def from_dict(cls, raw: Any) -> ReviewCase:
        obj = object_value(raw, "case")
        if set(obj) != {"case_id", "task", "policy", "before", "after"}:
            raise ValidationError("Review input has missing or unexpected fields")
        cid = obj["case_id"]
        if not isinstance(cid, str) or not re.fullmatch(r"pg-\d{4}", cid):
            raise ValidationError("Invalid opaque case ID")
        pol = object_value(obj["policy"], "policy")
        if set(pol) != {"allowed_paths", "requires_tests"}:
            raise ValidationError("Policy requires allowed_paths and requires_tests")
        paths = string_list(pol["allowed_paths"], "allowed_paths")
        if not paths or type(pol["requires_tests"]) is not bool:
            raise ValidationError("Invalid policy")
        for path in paths:
            safe_path(path)
        return cls(cid, text(obj["task"], "task", 10_000), pol,
                   files_map(obj["before"]), files_map(obj["after"]))

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "task": self.task, "policy": self.policy,
                "before": self.before, "after": self.after}

    @property
    def changed_files(self) -> tuple[str, ...]:
        return tuple(sorted(p for p in self.before.keys() | self.after.keys()
                            if self.before.get(p) != self.after.get(p)))


@dataclass(frozen=True)
class Truth:
    case_id: str
    unsafe: bool
    categories: tuple[str, ...]
    evidence_paths: tuple[str, ...]
    rationale: str
    family: str

    @classmethod
    def from_dict(cls, raw: Any) -> Truth:
        obj = object_value(raw, "truth")
        cats = string_list(obj.get("categories"), "truth categories")
        unsafe = obj.get("unsafe")
        if type(unsafe) is not bool or unsafe != bool(cats) or not set(cats) <= CATEGORIES:
            raise ValidationError("Truth unsafe flag and categories disagree")
        paths = string_list(obj.get("evidence_paths"), "evidence_paths")
        for path in paths:
            safe_path(path)
        return cls(text(obj.get("case_id"), "case_id"), unsafe, cats, paths,
                   text(obj.get("rationale"), "rationale"), text(obj.get("family"), "family"))


@dataclass(frozen=True)
class Prediction:
    case_id: str
    decision: str
    categories: tuple[str, ...] = ()
    evidence: tuple[dict, ...] = ()
    note: str = ""

    @classmethod
    def from_dict(cls, raw: Any) -> Prediction:
        obj = object_value(raw, "prediction")
        required = {"case_id", "decision", "categories", "evidence"}
        if not required <= obj.keys() or obj.keys() - required - {"note"}:
            raise ValidationError("Prediction has missing or unexpected fields")
        cid = text(obj["case_id"], "case_id", 80)
        decision = obj["decision"]
        if decision not in {"safe", "unsafe", "abstain", "error"}:
            raise ValidationError("Decision must be safe, unsafe, abstain or error")
        cats = string_list(obj["categories"], "categories")
        if not set(cats) <= CATEGORIES:
            raise ValidationError("Unknown prediction category")
        if decision == "unsafe" and not cats:
            raise ValidationError("Unsafe predictions must name at least one category")
        if decision != "unsafe" and cats:
            raise ValidationError("Only unsafe decisions can contain categories")
        evidence = obj["evidence"]
        if not isinstance(evidence, list) or len(evidence) > 100:
            raise ValidationError("Evidence must be a bounded list")
        for item in evidence:
            object_value(item, "evidence item")
            if set(item) - {"path", "reason", "line"} or not {"path", "reason"} <= item.keys():
                raise ValidationError("Evidence requires path and reason; line is optional")
            safe_path(item["path"])
            text(item["reason"], "evidence reason", 4000)
            if "line" in item and (type(item["line"]) is not int or item["line"] < 1):
                raise ValidationError("Evidence line must be a positive integer")
        return cls(cid, decision, cats, tuple(evidence), text(obj.get("note", ""), "note", 4000))

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "decision": self.decision,
                "categories": list(self.categories), "evidence": list(self.evidence),
                "note": self.note}
