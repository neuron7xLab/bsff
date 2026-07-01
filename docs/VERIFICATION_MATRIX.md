<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Meta-Verification Matrix

One mechanized row per verification dimension, so a reader trusts the gate, not
the prose. Each dimension: the **spec claim**, the **implementation surface** it
covers, the **gate** that enforces it, the **negative control** that proves the
gate can fail, the **CI job** that runs it, the **artifact/report** it produces,
and the concrete **failure mode** it catches.

| # | Spec claim | Implementation surface | Gate (`--check`) | Negative control (nodeid) | CI job | Report | Failure mode caught |
|---|---|---|---|---|---|---|---|
| 1 | Every gate is an instrument, not a label | `tools/*` gate surface (43 gates) | `gate_soundness.py` | `test_gate_soundness.py::test_new_gate_without_negative_control_is_unproven_and_fails_ratchet` (+ AST nodeid resolution) | meta-verification | registry (`gate_soundness_registry.json`) | a decorative gate (no negative control) or a decorative nodeid (function absent) slips into the proven set |
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
  negative-controlled: `gate_soundness` reports **14 proven / 29 frozen unproven**
  of 43 — the frozen list is the honest debt map, held by a ratchet, not a claim
  of universal soundness.
- **CI dashboard is the structural (reduced) dashboard.** The meta-verification job
  runs `quality_dashboard.py --check --no-mypy`: it gates dimensions 1–5. The
  **type-safety dimension (row 9) is enforced by the separate strict-type PR**,
  which adds the `[tool.mypy]` config; without that config `_mypy_dimension` is
  fail-closed (a usage error is FAIL, never a vacuous PASS), so type-safety is
  excluded from *this* PR's composite rather than faked into it.
- **Proof strength.** `gate_soundness` proves a negative control **exists and is a
  defined test function** (file + AST-resolved nodeid). It does not execute the
  full pytest run at audit time; execution is delegated to the `test-py*` jobs.
