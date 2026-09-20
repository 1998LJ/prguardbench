# Related work and positioning

Source check: 2026-09-20. These sources motivated scope, not copied benchmark data.
No comprehensive literature review or novelty guarantee is claimed.

1. SWE-bench, Evaluation Guide. https://www.swebench.com/SWE-bench/guides/evaluation/
   Evaluates submitted patches against repository tests in containerized environments.
   PRGuardBench's repair track is much smaller and synthetic; it additionally separates
   edited-test success from independent behavior and an explicit preservation policy.

2. RepoGuardBench, DaoyuanLi2816.
   https://github.com/DaoyuanLi2816/RepoGuardBench
   Repository-borne prompt injection and coding-agent utility/safety. This is a distinct
   existing project with a similar name. PRGuardBench is not affiliated and does not
   claim to originate test-deletion or coding-agent safety research. Its focus is PR
   integrity signals and legitimate-change negative controls, not injection attacks.

3. Anthropic, "From shortcuts to sabotage: natural emergent misalignment from reward
   hacking", 2025-11-21.
   https://www.anthropic.com/research/emergent-misalignment-reward-hacking
   Discusses reward hacking in programming tasks. This release tests controlled
   maintenance failure modes; it does not replicate that research or infer model intent.

4. GitHub, Secure use reference.
   https://docs.github.com/en/actions/reference/security/secure-use
   Informed minimum permissions and immutable action pinning in supplied CI. The
   workflow does not execute external submissions with write permissions or secrets.

5. RepoGate, 1998LJ.
   https://github.com/1998LJ/t3n-repogate
   Existing project in the user's portfolio, inspected for context. No RepoGate code
   was copied or used to generate the gold labels. The benchmark is not an endorsement
   or circular self-certification of RepoGate. Integrating it is optional future work.
