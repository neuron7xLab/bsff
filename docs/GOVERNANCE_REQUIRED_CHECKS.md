<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Governance — required checks

The `main` branch ruleset requires **every** check below. Each name is the exact
GitHub **check-run context** that reports on a pull request — not a workflow or
job display name — so the list can be required without dead-locking merges on a
check that never arrives.

```text
architecture-contract
build-package
codeql-python
dependency-review
local-security-policy
pip-audit
provenance
release-gate-dry-run
slow-tests
test-py3.10
test-py3.11
test-py3.12
zizmor-actions-audit
```

`tools/verify_branch_protection.py` reads the live ruleset, diffs its required
status checks against this fenced list, and reports `admin_bypass_allowed`. It is
honest by construction: it returns `owner_action_required` when it cannot read the
API, and never reports `verified` while a bypass path exists.

## Names are check-run contexts, not job names

Two enforcement steps are intentionally **not** standalone required checks because
GitHub never emits a check-run under those names:

- **truth contract** (`tools/validate_truth_contract.py`) runs as a *step* inside
  the `provenance` check (and the `test` matrix). Requiring a phantom
  `truth-contract` context would block every merge forever.
- **IP / SPDX provenance** (`tools/validate_ip_provenance.py`) likewise runs as a
  step inside the `provenance` check. The reporting context is `provenance`, which
  transitively gates both validators.

`scorecard` and `nightly-extended` are **schedule/push-only** (no `pull_request`
trigger); they cannot report on a PR head, so requiring them would also dead-lock
merges. They are deliberately excluded from the required set.

## Admin bypass — break-glass posture (decided)

The ruleset retains a single admin bypass actor (`RepositoryRole` admin,
`bypass_mode: always`). This is a **deliberate break-glass recovery path, not a
normal merge path.** Normal merges go green-then-merge through the 13 required
checks above; the bypass exists only to recover the branch from a stuck or broken
governance state.

Because a bypass path exists, `tools/verify_branch_protection.py` correctly and
honestly reports `required_checks_verified: false` / `admin_bypass_allowed: true`,
and the ACTIONS-99 score **stays at 92 (`BELOW_99`)**. Governance is *not* claimed
verified while any override remains — that honesty is the point, not a defect.

History: this repository has twice seen an agent admin-merge on red (PRs #55,
#61). Keeping bypass as documented break-glass — rather than removing it
prematurely — is a calibrated trade-off: the brand-new `release-gate-dry-run`
(~20 min) and `slow-tests` (~11 min) gates must first prove **non-flaky over a
stable run of green history** before the recovery path is withdrawn.

## Removal condition (when governance reaches `VERIFIED` / 99)

The single remaining step is owner-only and is **deferred by policy**, not blocked
by capability. Remove the always-on admin bypass actor in **Settings → Rules**
once **both** hold:

1. the 13 required checks have a repeated, stable green history on `main`;
2. `release-gate-dry-run` and `slow-tests` are demonstrably non-flaky (no
   spurious red over that history).

Until then, the system honestly reports `required_checks_verified: false`.
