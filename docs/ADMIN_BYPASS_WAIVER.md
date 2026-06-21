<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Admin-bypass waiver protocol

An admin merge over a red or skipped required check is a **procedural failure**
unless a waiver exists. This session recorded two such events without a waiver
(PRs #55, #61) — this protocol exists so that never happens silently again.

If an admin bypass is genuinely unavoidable, the merging admin MUST add a
`WAIVER.md` entry (or a row below) with every field:

```text
pr_number:        #NN
merge_commit:     <sha>
failed_check:     <name of the red/skipped required check>
reason:           <why the bypass was unavoidable>
risk:             <what could break>
rollback_plan:    <exact revert/rollback steps>
expiry:           <date by which the underlying issue is fixed>
follow_up_pr:     #NN (the fix)
owner_approval:   <owner handle + date>
```

Without a complete waiver, the merge is **procedurally invalid** and must be
reverted or retroactively waived. The goal is not to forbid bypass absolutely —
it is to make every bypass leave a signed, expiring, owner-approved trace.

## Recorded events (retroactive, honest)

| pr | failed check | waiver |
|----|--------------|--------|
| #55 | test-py3.11 / 3.12 timeout | none at the time — fixed by #56 (slow/fast split) |
| #61 | zizmor cache-poisoning (high) | none at the time — fixed by #62 (drop cache:pip) |

Both are logged here rather than hidden. The branch-protection step in
`docs/GOVERNANCE_REQUIRED_CHECKS.md` is what makes future un-waived bypass
technically impossible.
