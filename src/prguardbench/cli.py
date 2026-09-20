"""Command-line interface. Default demo is offline and executes no submitted code."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .dataset import load_review, write_json, write_jsonl
from .models import MAX_JSON_BYTES, ValidationError
from .repairs import demo_submissions, export_tasks, grade_repairs
from .reporting import save_reports
from .runner import load_report, run_review, save_run


def parser():
    p = argparse.ArgumentParser(prog="prguardbench", description="Green CI is not enough. Reproducible PR-integrity development benchmarks.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("validate", help="Validate the authored review corpus and hashes")
    export = sub.add_parser("export", help="Export review inputs without labels")
    export.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("run", help="Evaluate a static baseline, command wrapper, or recorded predictions")
    run.add_argument("--adapter", choices=["ast-diff", "naive-diff", "always-safe", "always-abstain", "command"], default="ast-diff")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--name")
    run.add_argument("--model-id")
    run.add_argument("--predictions", type=Path)
    run.add_argument("--command-json", help='JSON argv array, not a shell command')
    run.add_argument("--allow-command", action="store_true", help="Explicitly trust and execute the selected wrapper")
    run.add_argument("--timeout", type=float, default=60)
    run.add_argument("--pass-env", action="append", default=[], help="Pass one named env var to the trusted wrapper; values are never stored")
    rep = sub.add_parser("report", help="Recompute metrics and render comparable measured reports")
    rep.add_argument("reports", type=Path, nargs="+")
    rep.add_argument("--out", type=Path, required=True)
    demo = sub.add_parser("demo", help="Run measured controls and create Markdown/HTML report")
    demo.add_argument("--out", type=Path, default=Path("results/demo"))
    demo.add_argument("--include-repairs", action="store_true")
    demo.add_argument("--backend", choices=["docker", "trusted-local"], default="docker")
    demo.add_argument("--image", default="python:3.12-slim")
    rex = sub.add_parser("repair-export", help="Export five repair task workspaces, no oracle answers")
    rex.add_argument("--out", type=Path, required=True)
    rgrade = sub.add_parser("repair-grade", help="Execute and grade submitted repairs (Docker by default)")
    rgrade.add_argument("--submission", type=Path, required=True)
    rgrade.add_argument("--out", type=Path, required=True)
    rgrade.add_argument("--backend", choices=["docker", "trusted-local"], default="docker")
    rgrade.add_argument("--image", default="python:3.12-slim")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.action == "validate":
            cases, _, manifest = load_review()
            print(f"VALID: {len(cases)} cases / {manifest['unsafe_count']} unsafe / {manifest['count']-manifest['unsafe_count']} safe")
            print(f"Input SHA-256: {manifest['input_sha256']}")
        elif args.action == "export":
            if args.out.exists():
                raise ValidationError("Refusing to overwrite an existing export")
            cases, _, _ = load_review()
            write_jsonl(args.out, [{"schema": "prguardbench.adapter.v1", "case": c.to_dict()} for c in cases])
            print(f"Exported {len(cases)} label-free requests to {args.out}")
        elif args.action == "run":
            command = None
            if args.adapter == "command" and not args.predictions:
                if not args.allow_command or not args.command_json:
                    raise ValidationError("Command adapters require --allow-command and --command-json")
                command = json.loads(args.command_json)
                if not isinstance(command, list):
                    raise ValidationError("--command-json must be an argv array")
            if args.out.exists() and any(args.out.iterdir()):
                raise ValidationError("Use a new output directory")
            report, predictions = run_review(args.adapter, name=args.name, command=command,
                                            timeout=args.timeout, pass_env=tuple(args.pass_env),
                                            predictions_path=args.predictions, model_id=args.model_id)
            save_run(args.out, report, predictions)
            save_reports(args.out, [report])
            m = report["metrics"]
            print(f"{report['name']}: {m['n_cases']} cases, {m['errors']} errors; balanced accuracy={m['balanced_accuracy']}")
            return 2 if m["errors"] else 0
        elif args.action == "report":
            reports = [load_report(p) for p in args.reports]
            save_reports(args.out, reports)
            print(f"Report: {args.out / 'index.html'}")
        elif args.action == "demo":
            if args.out.exists() and any(args.out.iterdir()):
                raise ValidationError("Use a fresh demo output directory")
            if args.include_repairs and args.backend == "trusted-local":
                print("TRUSTED-LOCAL: executing only the bundled, inspectable scripted repair controls.", file=sys.stderr)
            reports, repairs = [], []
            for adapter in ("ast-diff", "naive-diff", "always-safe", "always-abstain"):
                report, predictions = run_review(adapter)
                save_run(args.out / adapter, report, predictions)
                reports.append(report)
            if args.include_repairs:
                for name, submission in demo_submissions().items():
                    result = grade_repairs(submission, backend=args.backend, image=args.image)
                    write_json(args.out / "repairs" / f"{name}-submission.json", submission)
                    write_json(args.out / "repairs" / f"{name}-report.json", result)
                    repairs.append(result)
            save_reports(args.out, reports, repairs)
            print(f"Measured demo complete: {args.out / 'index.html'}")
        elif args.action == "repair-export":
            export_tasks(args.out)
            print(f"Repair tasks exported to {args.out}")
        elif args.action == "repair-grade":
            if args.out.exists():
                raise ValidationError("Use a new output report path")
            if args.submission.stat().st_size > MAX_JSON_BYTES:
                raise ValidationError("Submission is too large")
            if args.backend == "trusted-local":
                print("WARNING: trusted-local executes submitted Python on this host. It is NOT a sandbox.", file=sys.stderr)
            raw = json.loads(args.submission.read_text(encoding="utf-8"))
            result = grade_repairs(raw, backend=args.backend, image=args.image)
            write_json(args.out, result)
            print(f"Joint pass: {result['joint_passes']}/{result['n_tasks']}")
            return 2 if result["execution_errors"] else 0
        return 0
    except (ValidationError, ValueError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
