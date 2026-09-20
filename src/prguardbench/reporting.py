"""Dependency-free, escaped Markdown/HTML reports from measured result objects."""
from __future__ import annotations

import html
from pathlib import Path

from .models import ValidationError


def pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def md(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def check_comparable(reports):
    if not reports:
        raise ValidationError("At least one review result is required")
    identity = {(r["dataset"]["input_sha256"], r["dataset"]["truth_sha256"],
                 r["metrics"]["metric_policy"]) for r in reports}
    if len(identity) != 1:
        raise ValidationError("Refusing to compare different datasets, labels or metric policies")
    names = [r["name"] for r in reports]
    if len(names) != len(set(names)):
        raise ValidationError("Leaderboard display names must be distinct")


def markdown(reports, repair_reports=()):
    check_comparable(reports)
    lines = ["# PRGuardBench - measured development results", "",
             "> Public synthetic development suite. Scripted/static baselines are NOT coding-agent rankings.", "",
             f"Dataset: `{reports[0]['dataset']['suite']}` v{reports[0]['dataset']['version']}.",
             f"Input SHA-256: `{reports[0]['dataset']['input_sha256']}`.", "",
             "## Review track", "",
             "| Evaluator | Kind | Balanced accuracy | Precision | Recall | False-positive rate | Coverage | Errors |",
             "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for report in sorted(reports, key=lambda r: r["metrics"]["balanced_accuracy"] or 0, reverse=True):
        m = report["metrics"]
        lines.append(f"| {md(report['name'])} | {md(report['kind'])} | {pct(m['balanced_accuracy'])} | "
                     f"{pct(m['precision'])} | {pct(m['recall'])} | {pct(m['false_positive_rate'])} | "
                     f"{pct(m['coverage'])} | {m['errors']} |")
    lines.extend(["", "Missing results, errors and abstentions do not count as correct. Precision is n/a when no positive predictions exist.",
                  "These are point estimates on a small authored suite, not population-level safety estimates.", ""])
    if repair_reports:
        lines += ["## Repair track: green CI is not enough", "",
                  "| Submission | Backend | Native tests pass | Held-out behavior pass | Policy intact | Joint pass |",
                  "| :--- | :--- | ---: | ---: | ---: | ---: |"]
        for r in repair_reports:
            lines.append(f"| {md(r['name'])} | {md(r['backend'])} | {r['native_passes']}/{r['n_tasks']} | "
                         f"{r['functional_passes']}/{r['n_tasks']} | {r['policy_passes']}/{r['n_tasks']} | "
                         f"{r['joint_passes']}/{r['n_tasks']} |")
        lines += ["", "Repair controls are explicitly scripted examples, not results from Claude, Codex, or another live agent.", ""]
    lines += ["## Reproducibility", "", "Each evaluator's JSON report includes per-case predictions, labels, evidence, configuration and corpus hashes.",
              "No live model API is called by the default demo. No self-hosted or production code is scanned.", ""]
    return "\n".join(lines)


def html_report(reports, repair_reports=()):
    check_comparable(reports)
    def esc(value):
        return html.escape(str(value), quote=True)
    ordered = sorted(reports, key=lambda r: r["metrics"]["balanced_accuracy"] or 0, reverse=True)
    rows, details = [], []
    for r in ordered:
        m = r["metrics"]
        rows.append("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in (
            r["name"], r["kind"], pct(m["balanced_accuracy"]), pct(m["precision"]),
            pct(m["recall"]), pct(m["false_positive_rate"]), pct(m["coverage"]), m["errors"])) + "</tr>")
        failures = [c for c in m["cases"] if not c["correct"]]
        items = []
        for c in failures:
            p = c["prediction"]
            items.append(f"<li><strong>{esc(c['case_id'])}</strong> / {esc(c['family'])}: "
                         f"expected {'unsafe' if c['expected_unsafe'] else 'safe'}, got {esc(p['decision'])}"
                         f"<p>{esc(c['rationale'])}</p></li>")
        details.append(f"<details><summary>{esc(r['name'])}: {len(failures)} incorrect / abstained / missing</summary>"
                       f"<ul>{''.join(items) if items else '<li>No binary errors on this development suite.</li>'}</ul></details>")
    repairs = ""
    if repair_reports:
        rr = []
        for r in repair_reports:
            rr.append("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in (
                r["name"], r["backend"], f"{r['native_passes']}/{r['n_tasks']}",
                f"{r['functional_passes']}/{r['n_tasks']}", f"{r['policy_passes']}/{r['n_tasks']}",
                f"{r['joint_passes']}/{r['n_tasks']}")) + "</tr>")
        repairs = ("<section><h2>02 / Repair controls</h2><p>Passing the edited test suite is not the same as fixing the issue.</p>"
                   "<div class='scroll'><table><thead><tr><th>Submission</th><th>Backend</th><th>Native tests</th>"
                   "<th>Held-out behavior</th><th>Policy intact</th><th>Joint pass</th></tr></thead><tbody>" +
                   "".join(rr) + "</tbody></table></div><p class='muted'>Scripted controls, not live coding agents. "
                   "Trusted-local runs execute inspected bundled code only. Docker mode is a separate execution path.</p></section>")
    manifest = reports[0]["dataset"]
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>PRGuardBench | Measured development results</title><style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#131c30;--ink:#edf2ff;--muted:#b7c4dd;--line:#2e3c58;--accent:#7be1bc}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 system-ui,sans-serif}
main{max-width:1160px;margin:auto;padding:52px 28px 80px}header{border-bottom:1px solid var(--line);padding-bottom:36px}
.eyebrow{font-size:13px;letter-spacing:.16em;color:var(--accent);text-transform:uppercase}h1{font-size:clamp(36px,6vw,65px);letter-spacing:-.045em;line-height:1.08;margin:14px 0 22px}h2{font-size:24px;margin:0 0 14px}p{max-width:900px}
.lead{font-size:21px;color:var(--muted)}.badge{display:inline-block;border:1px solid var(--line);border-radius:30px;padding:4px 13px;margin:8px 8px 0 0;font-size:13px}.notice{border-left:3px solid var(--accent);padding:12px 18px;background:var(--panel);margin-top:28px}
section{padding:34px 0;border-bottom:1px solid var(--line)}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th{text-align:left;color:var(--muted);font-weight:500;border-bottom:1px solid var(--line)}td,th{padding:15px 12px;white-space:nowrap}tbody tr:nth-child(odd){background:var(--panel)}td:first-child{font-weight:650}code{overflow-wrap:anywhere;white-space:normal;color:var(--accent);font-size:13px}.muted{color:var(--muted);font-size:14px}details{background:var(--panel);border:1px solid var(--line);border-radius:8px;margin:12px 0;padding:14px 18px}summary{cursor:pointer;font-weight:600}li{margin:14px 0}li p{font-size:14px;color:var(--muted);margin:4px 0}footer{margin-top:30px;color:var(--muted);font-size:13px}
</style></head><body><main><header><div class="eyebrow">PR integrity / Development benchmark / v0.1</div>
<h1>Green CI.<br>Still a bad PR?</h1><p class="lead">Measure what a passing test suite does not tell you: lost assertions, suppressed tests, unauthorized changes, and weakened CI.</p>
""" + f"<span class='badge'>{manifest['count']} review cases</span><span class='badge'>7 risk families</span><span class='badge'>No model API required</span>" + """
<div class="notice"><strong>Measured controls, not a model leaderboard.</strong> This report contains actual local baseline results. No Claude, Codex, or Gemini ranking has been invented.</div></header>
<section><h2>01 / Review integrity</h2><p>Balanced positive and negative examples. Normal refactors matter as much as obvious bad changes.</p>
<div class="scroll"><table><thead><tr><th>Evaluator</th><th>Kind</th><th>Balanced acc.</th><th>Precision</th><th>Recall</th><th>False positives</th><th>Coverage</th><th>Errors</th></tr></thead><tbody>""" + "".join(rows) + """</tbody></table></div><p class="muted">All expected cases remain in the denominator. Errors and abstentions do not earn correctness credit. n/a means an undefined metric, not 100%.</p></section>""" + repairs + "<section><h2>03 / Inspect the misses</h2>" + "".join(details) + "</section>" + f"<section><h2>04 / Evidence, not marketing</h2><p>Dataset: <code>{esc(manifest['suite'])}</code>, version <code>{esc(manifest['version'])}</code>.</p><p class='muted'>Input SHA-256<br><code>{esc(manifest['input_sha256'])}</code></p><p class='muted'>Small public development suite, no hidden holdout, no statistical claim about real-world agent safety. Static heuristics are baselines; they are not the label oracle. Repair results and review metrics are deliberately not merged into one score.</p></section>" + "<footer>PRGuardBench v0.1.0 / Self-contained report / No analytics, scripts, fonts, or network requests</footer></main></body></html>"


def save_reports(out: Path, reports, repairs=()):
    out.mkdir(parents=True, exist_ok=True)
    (out / "leaderboard.md").write_text(markdown(reports, repairs), encoding="utf-8")
    (out / "index.html").write_text(html_report(reports, repairs), encoding="utf-8")
