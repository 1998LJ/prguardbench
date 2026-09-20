# Data card

- Name/version: PRGuardBench development suite 0.1.0.
- Review size: 42 examples, 21 safe and 21 unsafe; seven families, three of each class
  per family. Explicitly authored examples and rationales; no downloaded PR corpus.
- Repair size: 5 self-contained tasks; 26 explicit I/O vectors; public tests and
  protected-file policy. Reference implementations and green-only/no-change controls
  are clearly marked scripted artifacts.
- Origin: newly written for this delivery with AI assistance. No claim of independent
  human annotation. Labels are independent of baseline output but not independent
  of the suite's authorship. Human adjudication and holdout collection remain future work.
- License: MIT for source and authored data in this package.
- Split: public development only. No validation/test split, no secret evaluation set.
- Personal data: none required. Fictional code fragments, no live credentials.
- Languages: primarily Python; one JavaScript presence-policy case and workflow YAML excerpts.
- Intended use: evaluator development, regression testing, reproducible demonstrations.
- Not intended: proof of security, eligibility certification, ranking agent vendors
  from scripted controls, commercial-grade tamper-proof benchmarking.
- Known challenge: authorized edits, stronger assertion replacements, rename/move and
  formatting negative controls produce meaningful false-positive pressure.
- Maintenance: regenerate with tools/build_review_dataset.py and tools/build_repair_dataset.py;
  preserve a reviewed version/hash change when modifying inputs or labels.
