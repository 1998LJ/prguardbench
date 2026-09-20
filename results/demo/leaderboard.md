# PRGuardBench - measured development results

> Public synthetic development suite. Scripted/static baselines are NOT coding-agent rankings.

Dataset: `prguardbench-review-dev` v0.1.0.
Input SHA-256: `c00de2189cf6e144479fc9332c1db641204178f8762d4a32cd52c6bf3573c4cb`.

## Review track

| Evaluator | Kind | Balanced accuracy | Precision | Recall | False-positive rate | Coverage | Errors |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| ast-diff | static-control | 90.5% | 84.0% | 100.0% | 19.0% | 100.0% | 0 |
| naive-diff | static-control | 54.8% | 54.5% | 57.1% | 47.6% | 100.0% | 0 |
| always-safe | static-control | 50.0% | n/a | 0.0% | 0.0% | 100.0% | 0 |
| always-abstain | static-control | 0.0% | n/a | 0.0% | 0.0% | 0.0% | 0 |

Missing results, errors and abstentions do not count as correct. Precision is n/a when no positive predictions exist.
These are point estimates on a small authored suite, not population-level safety estimates.

## Repair track: green CI is not enough

| Submission | Backend | Native tests pass | Held-out behavior pass | Policy intact | Joint pass |
| :--- | :--- | ---: | ---: | ---: | ---: |
| reference-fix | trusted-local | 5/5 | 5/5 | 5/5 | 5/5 |
| green-only | trusted-local | 5/5 | 0/5 | 0/5 | 0/5 |
| no-change | trusted-local | 0/5 | 0/5 | 5/5 | 0/5 |

Repair controls are explicitly scripted examples, not results from Claude, Codex, or another live agent.

## Reproducibility

Each evaluator's JSON report includes per-case predictions, labels, evidence, configuration and corpus hashes.
No live model API is called by the default demo. No self-hosted or production code is scanned.
