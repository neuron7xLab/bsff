<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Governance — required checks

The `main` branch ruleset must require **every** check below, and must allow **no
admin bypass**, before governance is complete. Until the GitHub ruleset is
confirmed to match this list with bypass disabled, governance is **incomplete**
and the ACTIONS-99 score cannot reach 99 (see `docs/ACTIONS_99_SCORECARD.md`).

```text
test-py3.10
test-py3.11
test-py3.12
slow-tests
build-package
codeql-python
zizmor-actions-audit
dependency-review
pip-audit
local-security-policy
architecture-contract
truth-contract
ip-provenance
release-gate
```

## Why bypass matters

A required check that an admin can bypass at will does not block error — it only
documents it. This repository has twice seen an agent admin-merge on red (PRs #55,
#61). The point of governance is to make that **impossible**, not discouraged.

`tools/verify_branch_protection.py` reads the live ruleset, diffs it against this
list, and reports `admin_bypass_allowed`. It is honest by construction: it returns
`owner_action_required` when it cannot read the API and never reports verified
while a bypass path exists.

## Owner action

This is the one step the agent cannot perform — it is a repository-governance
decision. The owner must, in repository **Settings → Rules**:

1. add the missing required checks (currently: `slow-tests`,
   `zizmor-actions-audit`, `dependency-review`, `architecture-contract`,
   `truth-contract`, `ip-provenance`, `release-gate`);
2. remove the always-on admin bypass actor.

Until then, the system honestly reports `required_checks_verified: false`.
