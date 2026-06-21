<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Regeneration — one convergent, idempotent orchestrator

The generated surfaces form a dependency DAG:

```text
pytest ─▶ STATUS ─▶ MANIFEST
                └─▶ scorecard
gates  ─▶ DEMONSTRATION ─▶ (via decision.json) DECISION ─▶ CORE
```

`tools/regenerate.py` encodes this once and applies two first principles from
desired-state configuration management (Microsoft DSC, Terraform, Ansible):

- **topological order** — a generator runs only after its inputs are fresh, so the
  manual "regenerate X before Y" slips that bit earlier work are impossible;
- **idempotence / fixpoint** — one pass must reach a state where every `--check`
  passes, and a *second* pass must change nothing. The tool **verifies** this
  rather than assuming it.

```bash
python tools/regenerate.py                  # converge to fixpoint (1 pass when clean)
python tools/regenerate.py --check          # assert the whole system is at fixpoint
python tools/regenerate.py --verify-idempotent  # prove a second pass changes nothing
```

Measured: 5 surfaces converge in **1 pass**; the idempotence fingerprint is stable
across passes. Absent generators are skipped, so the scorecard joins automatically
once `tools/compute_scorecard.py` lands. The simplicity is the point — one
declarative command replaces a fragile hand-ordered chain, and it cannot drift
because it proves its own fixpoint.
