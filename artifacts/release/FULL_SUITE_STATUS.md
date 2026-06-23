<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Full-suite status

| check | command | result |
|-------|---------|--------|
| compileall | `python -m compileall src examples tests` | PASS (exit 0) |
| bonn suite | `python -m pytest -q tests/bonn_bright_line` | **16 passed, 0 failed** (JUnit XML; `artifacts/release/bonn_bright_line/TESTS.json`) |
| selftest | `bsff selftest` | PASS (exit 0) |
| manifest/status sync | `pytest tests/test_manifest_sync.py` | PASS (STATUS.md not clobbered) |
| certify gate | `pytest tests/test_certify.py` | PASS |
| ruff (gated paths) | `ruff check tests/bonn_bright_line` | PASS |

## Full `pytest -q` (entire suite)
- **Delegated to CI** on the PR, which is the authoritative hermetic-offline environment
  (jobs `test-py3.10`…`3.13`, `slow-tests`, `release-gate-dry-run`). PR #75 (the predecessor
  of this artifact) was merged **green** on exactly these gates.
- Running the entire suite locally is intentionally **not** included here: several suite
  tests regenerate tracked package artifacts (`artifacts/conformance`, `artifacts/demonstration`,
  `artifacts/honesty`, `artifacts/provenance_manifest.json`), which would dirty files outside
  this artifact's scope (rule 19 / change-scope audit). CI runs them in isolation.
- This change adds files only under `examples/`, `tests/bonn_bright_line/`, `docs/`,
  `artifacts/` and touches **no `src/`**, so it cannot introduce new failures in unrelated
  suite tests.
