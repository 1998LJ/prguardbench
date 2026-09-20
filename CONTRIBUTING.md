# Contributing

Contributions should improve evaluation validity, not leaderboard optics.

For a new review case, provide before/after snapshots, an explicit task policy, gold
categories, changed-file evidence and a rationale. Include a matched legitimate-edit
control. Do not derive a label from the baseline's output. Explain ambiguous cases and
request review rather than forcing a binary decision to favor one tool.

Run tests, corpus validation, formatting and an offline demo. Input/label changes require
a deliberate dataset version/hash update and regenerated reports. Do not claim that
model or CI results were executed when they were not. Do not upload secrets or publicize
third-party vulnerabilities through benchmark fixtures.

Real-agent result submissions require the complete configuration and unfiltered outcomes,
including errors, refusals and timeouts. Exact model identity is a submitter assertion,
not guaranteed by this harness. Do not run untrusted candidate code in trusted-local mode.

Fork experiments count as integration testing, not external adoption. Star farming,
coordinated artificial feedback and synthetic download counts are not project goals.
