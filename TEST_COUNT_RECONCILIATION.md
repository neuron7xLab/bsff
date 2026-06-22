<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# TEST_COUNT_RECONCILIATION

## The canonical rule

The live test count is **never hand-typed in any document.** Its single source
is the generated `STATUS.md`:

```bash
python tools/update_status.py          # regenerate STATUS.md from the live tree
python tools/update_status.py --check   # CI gate: fail if STATUS.md is stale
```

`update_status.py` is fail-closed: a non-zero pytest exit or an unparseable
summary aborts rather than emitting a guessed number. Any document that needs to
refer to the count cites `STATUS.md`; it does not embed a literal. This rule is
enforced for prose by `tools/validate_markdown.py` (no hardcoded `<N> passed` /
`<N> tests collected`) and for governed JSON artifacts by
`tools/validate_artifact_schema.py` (the `test_count` field must match
`STATUS.md`).

## Why the absolute number is environment-relative

The collected count legitimately varies with which optional test dependencies
are installed: a leaner pinned CI image collects fewer parametrised /
dependency-gated cases than a full-extras developer machine. `update_status.py`
records whatever the *current* environment collects, and `--check` **masks the
count** when comparing on-disk vs regenerated — the version, CLI surface, and
extras (the facts that must not silently drift) are still compared byte-exact,
and the on-disk count is separately asserted to be a present, positive integer.
So two honest environments can hold two different counts in `STATUS.md` without
either being "stale". The number is a measurement, not a constant.

## Historical episode (resolved)

An earlier `STATUS.md` carried a stale count while the live tree collected more.
Root cause: `STATUS.md` is a generated file, and the branch that first
introduced it had branched from a base predating PR #42's added tests, so its
generated snapshot recorded the pre-#42 number. It was a
stale-generated-file-from-branching artifact, not a flake, and was resolved by
regenerating `STATUS.md` on merged `main`. The `--check` gate now runs on merged
`main` so a future drift of this kind fails CI instead of shipping.

## Action

`STATUS.md` is regenerated from the live tree and `--check` guards it in CI.
Consult `STATUS.md` (and the GitHub Actions run for the relevant commit) for the
authoritative current count; this document deliberately quotes no literal.
