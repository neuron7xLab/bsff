<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Statistical Proof Gate — System Design (GAP1/2)

Design-before-implementation schema for the artifact-bound statistical proof
gate introduced in PR #113. It is a **new layer over** the narrow
`tools/validate_statistical_claims.py`, never a replacement.

## 1. Purpose & non-goals

**Purpose.** For every claim that asserts a *statistical measurement*, prove —
by recomputation over hash-bound result artifacts — that the numbers the claim
rests on actually exist, pass their null models, carry uncertainty, are stable
across seeds, are dataset-specific (not aggregate-laundered), and sit on the
declared failure threshold. Proof = the gate can and does FAIL when any of these
is absent.

**Non-goals (change boundary).**
- Does **not** replace `validate_statistical_claims.py` (forbidden-language /
  shape layer stays, runs independently).
- Does **not** recompute the science from raw EEG — it binds and cross-checks the
  *frozen* result artifacts; it never regenerates `bonn_bright_line/*` etalons.
- Does **not** touch rank boundary: CLAIM-004 stays `unverified`, CLAIM-003 stays
  scope-control. Gate SKIPS non-statistical claims explicitly.

## 2. Components

| Component | File | Role |
|---|---|---|
| Engine | `src/bsff/statistics/proof_gate.py` | pure `evaluate(root) -> report`, no I/O side effects except report write |
| CLI gate | `tools/validate_statistical_proof_gate.py` | `--check` (compare) / write; exit 1 on FAIL |
| Report | `artifacts/release/STATISTICAL_PROOF_GATE_REPORT.json` | PASS snapshot, schema `bsff.statistical_proof_gate/v1` |
| Falsification suite | `tests/test_stat_proof_gate.py` | positive + **negative controls** (see §7) |
| CI wiring | `.github/workflows/ci.yml` | `validate_statistical_proof_gate.py --check` |
| Integrity binding | `artifacts/MANIFEST.json` | proof-gate inputs hash-bound (GAP3 mechanism) |

## 3. Interfaces

- `evaluate(root=ROOT) -> dict` — report:
  `{schema, status: PASS|FAIL, proof_count, skipped_claims[], claim_proofs[], violations[]}`
  where each `claim_proofs[i] = {claim_id, status, artifact_hashes[], violations[]}`.
- CLI: `--check` (recompute + compare committed snapshot; never mutate on check),
  `--output PATH`. Exit `0` iff `status == PASS`.
- Selection predicate `_is_measured(claim)`: `internally_verified` ∧ metric names
  include `wilson|cluster|fpr`. Everything else → `skipped_claims` with reason.

## 4. Data flow

```
claims.yaml ──select measured──► {CLAIM-001, CLAIM-002}
       │
       ▼
CURRENT_TRUTH.json.artifact_paths ──► { s2_summary, s3_confirmatory,
       │                                multi_null, cluster_robust_ci,
       │                                dataset_manifest, selection_lock }
       ▼
bind+sha256 each artifact ──► artifact_hashes[]
       ▼
per-claim invariant battery (§5) ──► violations[]
       ▼
report{status} ──► CLI exit ──► CI gate ; report hash-bound in MANIFEST
```

## 5. Invariants (each MUST be independently falsifiable)

- **I1 null-model**: `multi_null.all_nulls_pass is True` ∧ `nulls` non-empty.
- **I2 uncertainty**: Wilson 95% CI upper (`s3.G2.wilson_95ci`) ∧ cluster-robust
  t 95% CI upper present.
- **I3 seed-sensitivity**: `≥2` per-seed points in both `s3.per_seed` and
  `cluster.per_seed_fpr`.
- **I4 dataset-specificity**: `s2_summary.S2_BRIGHT_LINE_PASSED is True` (dataset
  result, not aggregate).
- **I5 aggregate↔dataset consistency**: `truth.s2_seed_averaged_fpr ==
  s3.G2.ar_null_fpr` (no aggregate laundering).
- **I6 threshold identity**: `s3.G2.ci_upper_threshold == 0.05` ∧
  `cluster.threshold == 0.05`.
- **I7 artifact presence+integrity**: every bound path exists; sha256 recorded.
- **Meta-I**: `proof_count ≥ 1` (a gate that proves nothing FAILs).

## 6. Change boundaries

- **May write**: `STATISTICAL_PROOF_GATE_REPORT.json`, its own source/tests/docs,
  CI step, MANIFEST binding entry.
- **Must never mutate**: frozen `bonn_bright_line/*`, `controls/*`, `CURRENT_TRUTH.json`
  values, `validate_statistical_claims.py`, claims' rank/status.
- **Determinism**: report is `sort_keys`, hash-bound; must survive `--check` byte-stable.

## 7. Deficits in the current skeleton (to close in this PR)

1. **Duplicate test file** — `tests/test_statistical_proof_gate.py` only re-calls
   `test_stat_proof_gate.py`. Collapse to one (remove the duplicate).
2. **Positive-only tests = latent facade** — both tests only assert PASS on committed
   artifacts. There is NO proof the gate can FAIL. Add a **negative-control matrix**:
   for each invariant I1–I7, a fixture that violates exactly that invariant and asserts
   the gate returns `FAIL` with the matching violation. This is the falsifiability plane
   that turns a "table label" into an "instrument".
3. **Provenance under-bound** — `DATASET_MANIFEST.json` (dataset identity / source /
   license boundary / zip + per-file hashes / sample counts) is referenced but not
   cross-checked. Add **I8 provenance-binding**: bound dataset manifest's per-file
   hashes must match, and sample counts must be > 0 and consistent with the summary.
4. **Weak snapshot check** — `validate_report_in_sync` only checks schema + `status==PASS`.
   Strengthen to compare the full recomputed report (like MANIFEST `--check`) so a stale
   PASS snapshot cannot mask a regressed live evaluation.

## 8. Implementation order

1. Land this design doc (done — this file).
2. Remove duplicate test; add negative-control matrix (I1–I7) — prove FAIL-ability first.
3. Add I8 provenance binding + strengthen snapshot check.
4. Hash-bind the proof-gate inputs in MANIFEST (`CRITICAL_ARTIFACTS`).
5. Freshness regen (STATUS/MANIFEST/DEMONSTRATION), full local gate battery, ruff
   check+format, push, drive to terminal green. No merge without explicit `MERGE`.
