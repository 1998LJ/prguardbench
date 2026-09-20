# Security and trust boundaries

## Safe-by-default operations

Review validation, static baseline runs, prediction replay and report rendering treat
file snapshots as data. They do not execute snapshot code. HTML escapes user text and
contains a restrictive content-security policy, no scripts and no network dependencies.
The default demo performs only this offline review track.

## Explicit execution paths

`run --adapter command --allow-command` executes a user-selected trusted wrapper.
It uses an argv array (no shell), a temporary working directory, time/output bounds and
an environment allowlist. These are hygiene controls, **not a sandbox**. A wrapper can
still access host files/network available to its user. Do not run an untrusted wrapper.

`repair-grade` uses Docker by default and never automatically falls back to local
execution. The image must be explicitly installed in advance. The container uses no
network, read-only candidate/worker mounts, non-root execution, dropped capabilities,
no-new-privileges, a tmpfs, and CPU/memory/process limits. No Docker socket, repository
root, HOME, personal secrets or SSH agent is mounted. Docker daemon ownership itself
is privileged; run grading on a disposable machine for genuinely untrusted code.

`--backend trusted-local` executes submitted Python **on your host**. It is intended
only for inspected, maintainer-authored fixtures and deliberate local development.
It inherits no arbitrary secrets, but is still not isolation. Never use it for
unreviewed agent output or third-party benchmark submissions.

## What is NOT guaranteed

- Resource flags do not prove a container escape is impossible.
- Held-out tests are withheld from the exported generation workspace, not a secret
  in the published dataset. This public development release has no hidden evaluation set.
- The Python observation worker is not a formally tamper-resistant oracle. Hostile
  submissions may introspect/control their process. Docker mitigates host exposure;
  it does not prove observations cannot be manipulated. Do not accept high-stakes
  leaderboard submissions without a separately hardened evaluator and review.
- Static heuristics cannot generally prove test equivalence or malicious intent.
- Corpus/implementation hashes prove byte identity, not model provenance.

Docker was not available in the original build environment. Command construction and
fail-closed tests ran, but the actual Docker smoke remains to be run after handoff.
The supplied CI workflow includes this smoke and must not be advertised as passing
until it has actually run on the destination repository.

## Reporting a security issue

Do not post live credentials or exploitation instructions against third-party systems.
For a new public repository, configure a maintainer-approved private reporting channel
before inviting external submissions. Until then, do not run sensitive workloads here.
