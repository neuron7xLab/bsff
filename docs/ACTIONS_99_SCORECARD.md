<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# ACTIONS-99 scorecard

The score is **computed** by `tools/compute_scorecard.py` from verifiable facts,
written to `artifacts/actions_99_scorecard.json`, and `--check`'d in CI. It is not
a number anyone types.

## The 99 rule

`can_claim_99` is true **only** when `artifacts/governance_status.json` reports
`required_checks_verified: true` **and** `admin_bypass_allowed: false`. While an
admin can bypass the gates, the score is capped below 99 no matter how green the
code is — because a bypassable gate does not stop human or agent error.

```bash
python tools/verify_branch_protection.py   # refresh governance_status.json (owner/agent)
python tools/compute_scorecard.py          # recompute the score
python tools/compute_scorecard.py --check  # CI: committed scorecard matches computed
```

## Current state

P0 and P1 are complete and main is green, but the live ruleset is missing required
checks and allows an always-on admin bypass (`tools/verify_branch_protection.py`
reports it). Therefore **`can_claim_99: false`** and the score is capped. Closing
that gap is the one owner-only step; see `docs/GOVERNANCE_REQUIRED_CHECKS.md`.
