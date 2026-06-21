<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# TEST_COUNT_RECONCILIATION

## The discrepancy

- `STATUS.md` claimed **306** "live test count".
- The live tree collects and passes **310**.

Both measurement methods agree on 310:

```bash
python -m pytest tests/ --collect-only -p no:cacheprovider | grep collected   # 310 tests collected
python -m pytest tests/ -q                                                     # 310 passed
```

## Root cause (not a flake)

`STATUS.md` is a generated file (`tools/update_status.py`). The committed value
306 was the count **before PR #42** (`feat(validation): surrogate fidelity`),
which added exactly **4** tests (`tests/test_surrogate_fidelity.py`). PR #43,
which introduced `STATUS.md`, branched from a tree that did not yet contain
those 4 tests, so its generated `STATUS.md` recorded 306. `306 + 4 = 310`.

It is a stale-generated-file-from-branching artifact, resolved by regenerating
`STATUS.md` on merged `main` (now 310).

## The rule (enforced)

The test count is **never hand-typed**. Its single source is:

```bash
python tools/update_status.py          # regenerate STATUS.md from the live tree
python tools/update_status.py --check   # CI gate: fail if STATUS.md is stale
```

`update_status.py` is fail-closed: a non-zero pytest exit or an unparseable
summary aborts rather than emitting a guessed number. Any document quoting a
test count must cite `STATUS.md` (which is regenerated), not a literal.

## Action taken

`STATUS.md` regenerated to **310** in this change. The `--check` gate must run on
merged `main` (not a stale branch base) so a future drift of this kind fails CI
instead of shipping.
