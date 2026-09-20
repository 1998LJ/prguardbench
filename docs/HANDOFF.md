# Handoff to the maintainer / 派灵

> Historical handoff note: the project has since been published at
> `1998LJ/prguardbench`. Remote CI status is recorded in `docs/VERIFICATION.md`.
> The instructions below preserve the original handoff boundary.

## Completed here

A working source package, authored data, static review controls, command/replay interface,
five repair tasks, independent I/O/policy grading, actual local demonstrations, automated
tests and build/install checks. See VERIFICATION.md for the exact executed commands.
At the original local handoff, no existing user repository had been changed and no
release/tag/remote PR had been created. Publication happened later as a separate step.

## First reproduce, then publish

1. Unpack and inspect; install from source or the included wheel.
2. Run validate, tests, the offline demo and the explicit trusted bundled repair demo.
3. In a disposable Linux host with Docker, run the default Docker repair smoke. Record
   image ID and results. Do not remove Docker safety flags to make an error disappear.
4. Create a NEW public repository only after owner approval. Never upload virtualenvs,
   credentials, local caches, failed temporary runs or third-party code as original work.
5. Push source, review the remote diff, then verify CI on the actual destination. The
   shipped workflows are not evidence of a completed remote CI run.
6. Publish the static report through Pages only after checking that every row is marked
   as scripted/static control. No fake model entries, badges or download counts.

## Next useful experiment

Run one real agent on the five exported tasks and one real reviewer on the 42 inputs.
Record exact agent/model version, instructions, token/time budget, command, date,
number of repeats, data hashes, all failures, and unfiltered outputs. Review and repair
scores belong in separate tables. Do not call these few toy tasks a definitive ranking.

Before public comparison, obtain independent label review and add a disjoint locked
holdout. Characterize false positives on legitimate test edits. Do not optimize the
baseline by editing gold labels. Do not describe local fork experiments as adoption.

## What not to do

- Do not wire paid nightly runs, publication, social posts, or PR comments without approval.
- Do not use this as a reason to mass-submit promotional CI changes to third-party repos.
- Do not assert that the project guarantees growth in stars or qualification for grants.
- Do not confuse model agreement with truth or a green workflow with a successful repair.
- Do not copy RepoGate's verdicts into ground-truth labels.

## Release boundary

Suggested initial release: v0.1.0 as a public development benchmark. The source package
name is not a claim to an available PyPI namespace. Source installation works; check
namespace and ownership before any package publication. Only move a stable tag after
its exact source/wheel and remote CI have been independently verified.
