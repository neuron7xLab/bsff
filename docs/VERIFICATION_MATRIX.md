<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Meta-Verification Matrix

One mechanized row per verification dimension, so a reader trusts the gate, not
the prose. Each dimension: the **spec claim**, the **implementation surface** it
covers, the **gate** that enforces it, the **negative control** that proves the
gate can fail, the **CI job** that runs it, the **artifact/report** it produces,
and the concrete **failure mode** it catches.

| # | Spec claim | Implementation surface | Gate (`--check`) | Negative control (nodeid) | CI job | Report | Failure mode caught |
|---|---|---|---|---|---|---|---|
| 0 | Intent→spec edge is closed (chaos→definition) | `intents/registry.json` | `intent_contract.py` | `test_intent_contract.py::test_unratified_intent_fails` | meta-verification | ratified/total | an intent that is unratified, unbound, or points at a ghost negative control (unverified human→spec translation) |
| 1 | Every gate is an instrument, not a label | `tools/*` gate surface (46 gates) | `gate_soundness.py` | `test_gate_soundness.py::test_new_gate_without_negative_control_is_unproven_and_fails_ratchet` (+ AST nodeid resolution) | meta-verification | registry (`gate_soundness_registry.json`) | a decorative gate (no negative control) or a decorative nodeid (function absent) slips into the proven set |
| 2 | Gate code fails closed | `tools/*` (+ `src/` via `--include-src`) | `lint_fail_open.py` | `test_lint_fail_open.py::test_negative_control_except_returns_zero_is_flagged` | meta-verification | inline findings + `fail_open_allowlist.txt` | an `except → return 0/True/PASS` swallowing an error into success |
| 3 | Claim↔evidence graph is complete | `claims.yaml` × `artifacts/MANIFEST.json` | `claim_coverage.py` | `test_claim_coverage.py::test_negative_control_dangling_claim_id` | meta-verification | coverage matrix | dangling claim id, missing evidence file, orphan or **unbacked** asserted claim |
| 4 | Committed artifacts are byte-reproducible **and** fresh | registered deterministic generators | `determinism_probe.py` | `test_determinism_probe.py::test_negative_control_flags_nondeterministic_generator` | meta-verification | per-generator determinism/stale entry | nondeterministic regeneration **or** stale (committed ≠ regenerated) artifact |
| 5 | No function exceeds CC 15 (ratchet) | `src/bsff` cyclomatic complexity | `complexity_gate.py` | `test_complexity_gate.py::test_flags_non_allowlisted_offender` | meta-verification | violations + `complexity_allowlist.json` | new/edited code over the ceiling, ratchet regression, or a **stale allowlist entry** that rots the ratchet |
| 6 | Statistical claims are proof-bound | `CURRENT_TRUTH` result artifacts | `validate_statistical_proof_gate.py` | `test_stat_proof_gate.py::test_seed_ci_above_threshold_fails` | test-py* | `STATISTICAL_PROOF_GATE_REPORT.json` | null/CI/seed/dataset/provenance invariant broken |
| 7 | Ingest is SSRF-safe | `src/bsff/adjudication/ingest.py` | (unit) | `test_ingest_security.py::test_non_arxiv_host_rejected` | test-py* | — | non-https scheme **or** non-allowlisted host reaches `urlopen`; XXE via stdlib XML |
| 8 | Composite quality is one computed verdict | dimensions 1–5 | `quality_dashboard.py` | `test_quality_dashboard.py::test_dashboard_fails_if_any_dimension_fails` | meta-verification | `artifacts/QUALITY_DASHBOARD.json` (gitignored) | any dimension FAIL not propagating to the composite |
| 9 | `src/bsff` passes mypy `--strict` | `src/bsff` types | `python -m mypy` | (config-gated; usage error is FAIL) | *(strict-type PR #114)* | — | untyped/incorrect types; a mypy usage/crash fabricating a PASS |

## Scope boundaries (no overclaim)

- **Negative-control scope.** The *meta-verification gates* (rows 1–8) each ship a
  negative control. The legacy `tools/` gate surface is **not** fully
  negative-controlled: `gate_soundness` reports **15 proven / 31 frozen unproven**
  of 46 — the frozen list is the honest debt map, held by a ratchet, not a claim
  of universal soundness.
- **CI dashboard is the structural (reduced) dashboard.** The meta-verification job
  runs `quality_dashboard.py --check --no-mypy`: it gates dimensions 1–5. The
  **type-safety dimension (row 9) is enforced by the separate strict-type PR**,
  which adds the `[tool.mypy]` config; without that config `_mypy_dimension` is
  fail-closed (a usage error is FAIL, never a vacuous PASS), so type-safety is
  excluded from *this* PR's composite rather than faked into it.
- **Proof strength.** `gate_soundness` proves a negative control **exists, is a
  top-level pytest-collectable function, AND its test file references the gate
  module** (static linkage). Behavioral proof (the control actually FAILS the
  gate) is delegated to the `test-py*` jobs.

## Known limitations (adversarially found, honestly held)

An internal red-team fleet attacked every gate. It found **zero fabrication** (no
gate fakes a PASS; all are fail-closed on crash/usage-error) but confirmed these
residual blind spots, inherent to static/heuristic analysis, documented rather
than overclaimed away:

- **Fail-open detection is undecidable, best-effort.** `lint_fail_open` catches
  common shapes (`except → return 0/True/EXIT_SUCCESS/exit(0)`, dead-decoy
  hatches, unfailable gates) but NOT `except: pass` + a later fall-through
  `return 0` in a non-gate helper, a laundered `return len(errors)` always 0, or
  decorator-swallowed exceptions. It is a ratchet, not a proof.
- **Complexity depends on radon**; a property radon under-counts is under-counted
  here. The ratchet floors *reported* CC (now including nested closures).
- **Determinism guards the registered set** (7 generators), not the whole tree
  (~100 artifacts); registration is the ratchet. Its `git checkout --` restore of
  stray writes is **sound only in a single-writer worktree** (CI guarantees this);
  a concurrent editor's change can be misattributed and reverted.
- **`gate_soundness` linkage is necessary-not-sufficient**: it proves a control is
  wired to its gate, not that the assertion is semantically correct — CI execution
  establishes that.
- **The `unproven` list is visible reviewed debt**, not an enforced immutable
  baseline: growing it is an explicit, auditable diff line.
- **Type-safety (row 9) is not CI-enforced in this PR** (no `[tool.mypy]` config
  here); it lands with the strict-type PR. The CI dashboard runs `--no-mypy`; the
  dimension is fail-closed, so it is excluded, never faked.
