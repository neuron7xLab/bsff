<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Repository decomposition — specification, purpose, and seven-axis assessment

A factual map of everything in this repository: what each subsystem *specifies*, what it is
*for*, and how it scores on **accuracy · clarity · logic · factuality · aesthetics · simplicity ·
elegance**. Grounded in the actual tree (47 `src/bsff` modules, 57 `tools/` gates, 95 test files,
~90 docs, 16 workflows, ~95 artifacts), not in description. Scores are 1–5 (5 = best); where a
subsystem is weak the weakness is stated, not hidden — that is the point of a falsification repo.

---

## 0. Purpose (the one invariant)

```text
claim + signal + policy + ordered evidence stages  ->  immutable verdict contract
verdict ∈ {SURVIVED, REFUTED, UNSUPPORTED}     (never "true")
```

BSFF is a **falsification control plane**: it breaks weak signal/EEG/BCI claims cheaply,
reproducibly, and early, and refuses to let a result become "true" because someone wants a stronger
headline. Every public number is bound to a machine artifact; every claim has a gate that fails
closed. The repository's deeper purpose is **self-honesty**: the instrument is built so it cannot lie
about its own state — demonstrated this cycle when its own falsification downgraded a favorable-seed
pass and only restored "robust" after a reproduced + multi-null artifact earned it.

---

## 1. Runtime engine (`src/bsff/`, 47 modules)

**Specification.** `ClaimSpec + signal + PolicyProfile -> StageRegistry[stationarity, leakage,
surrogate, bayes] -> EvidenceGraph(sha256) -> PipelineVerdict(contract_sha256)`.

| Component | Spec / purpose |
|---|---|
| `schemas.py`, `api.py`, `json_schema.py` | Frozen domain contract: `ClaimSpec`, `VerdictJSON`, stable `evaluate_claim_pipeline`; blocks ambiguous claims |
| `policy.py`, `registry.py`, `stages.py` | Explicit geometry (alpha, surrogate budget, stationarity mode) + ordered stages; blocks hidden thresholds & execution drift |
| `verdict_engine.py`, `pipeline.py` | Single-claim and composable falsification; deterministic collapse to one of three states |
| `surrogate_engine.py`, `calibration.py`, `reference_surrogate.py` | MIAAFT surrogate generation + rank-order test; numpy AAFT/IAAFT reference baseline |
| `leakage_detector.py`, `leakage_deep.py`, `transfer_entropy.py` | Block-design / feature-selection / phase-coupling / directed-TE leakage probes (fatal by default) |
| `operating_characteristic.py`, `te_operating_characteristic.py`, `controls.py`, `stability.py` | Empirical power/FPR batteries; positive/negative self-controls; seed-stability certification |
| `evidence.py`, `validation.py`, `provenance.py`, `report.py` | Evidence graph + SHA256, artifact validation, provenance records, verdict output |
| `bids.py`, `moabb_adapter.py`, `datasets.py`, `case.py`, `eeg_artifacts.py` | Real-data ingestion with anti-leakage guards; artifact battery |
| `scope_guard.py`, `capability.py`, `release.py`, `cli.py`, `bench.py` | Out-of-scope quarantine, doctor/strict-readiness, release orchestration, CLI surface |
| `adjudication/` (10 modules) | Hash-chained truth ledger, falsifiability tiering, quote-anchored claims (refuses claims absent from source) |

**Assessment** — accuracy **5**, clarity **5**, logic **5**, factuality **5**, aesthetics **4**,
simplicity **3**, elegance **4**. *The stage/registry/evidence collapse is genuinely elegant and
the docstrings are precise. Simplicity drops because 47 modules carry some overlap (three surrogate
implementations; two operating-characteristic batteries) — defensible as cross-checks, but a reader
must hold a lot at once.*

---

## 2. Bonn bright-line benchmark (`examples/bonn_bright_line/`, 19 files)

**Specification.** Pre-declared thresholds frozen *before* run: G1 power (Set E SURVIVED ≥ 0.80;
A/B not-SURVIVED), G2 specificity (real-spectrum AR-null FPR ≤ 0.05), statistic
`sampen_lower_tail_m2_r015_v1`, MIAAFT null, convergence-gated.

| Phase | Files | Purpose |
|---|---|---|
| Loader / statistic / null | `loader.py`, `statistics_sampen.py`, `run_ar_negative.py` | Audited Bonn loader (per-file SHA256); SampEn lower-tail; AR(p) genuinely-linear null |
| S2 select→confirm | `s2_candidate_registry/evaluate/select/confirmatory/aggregate.py`, `s2_metrics.py` | Freeze exactly one candidate before confirmatory; BH-FDR; frozen G1/G2 logic |
| S3 robust gate | `s3_seed_averaged_confirmatory.py` | Seed-averaged: Set-E SURVIVED ≥ 0.80 **and** AR-null FPR Wilson-95-CI-upper ≤ 0.05 |
| Multi-null gate | `multi_null_robustness.py` | Same gate across AR / IAAFT / phase-randomized nulls (null model = researcher DOF) |
| Aggregate / release | `aggregate_verdict.py`, `check_consistency.py`, `finalize_release.py`, `release_check.py` | Honest verdict, cross-artifact consistency, fail-closed bundle |

**Assessment** — accuracy **5**, clarity **5**, logic **5**, factuality **5**, aesthetics **5**,
simplicity **4**, elegance **5**. *This is the repository's strongest subsystem: the
select-before-confirm lock, the CI-upper gate (not point estimate), and the multi-null cross-check
are textbook pre-registration discipline. The S3 runner's earlier numpy-bool serialization crash was
a real defect, caught and reproduced — recorded, not hidden.*

---

## 3. Governance & gate battery (`tools/`, 57 scripts)

**Specification.** Every public claim has a fail-closed gate; no gate trusts another's word.

| Category | Representative gates | Blocks |
|---|---|---|
| Truth/state generators | `generate_current_truth`, `update_status`, `generate_manifest`, `regenerate`, `certify_release` | drift between state and docs; reordering (hash chain) |
| Anti-overclaim validators | `validate_forbidden_claims`, `validate_statistical_claims`, `validate_current_truth`, `validate_truth_contract`, `validate_claim_audit` | clinical/regulatory claims; point-estimate-as-pass; stale state; decorative VERIFIED rows |
| Surrogate / power gates | `cross_validate_surrogate`, `validate_surrogate_fidelity`, `validate_tisean_reference`, `statistical_power_profile`+`validate_power_profile` | algorithm property breaks; excess FPR; seed instability |
| Adversarial / mutation | `mutation_kill_gate`, `validate_mutation_report`, `mutation_probe` | a test suite that can't kill real regressions |
| Release / supply chain | `generate_sbom`, `validate_provenance`, `validate_wheel_runtime`, `validate_lockfiles`, `scan_secrets`, `triage_sarif` | non-reproducible wheel; unpinned deps; secrets; CodeQL high/critical |
| Honesty / governance | `verify_honesty`, `verify_grounding`, `verify_controls`, `verify_branch_protection`, `compute_scorecard`, `final_validation_verdict` | prose ≠ artifact; faked controls; admin-bypass over-credit |

**Assessment** — accuracy **5**, clarity **4**, logic **5**, factuality **5**, aesthetics **3**,
simplicity **2**, elegance **3**. *The fail-closed philosophy is rigorous and the grounding gates
(prose must equal artifact) are excellent. But 57 single-purpose scripts is the repository's main
**simplicity debt** — several validators overlap (`validate_forbidden_claims` vs
`validate_truth_contract` vs `validate_release_notes` all scan for forbidden phrases). A unified
gate registry with declarative rules would cut this surface markedly without losing coverage.*

---

## 4. Truth & evidence surfaces (`docs/`, top-level `*.md`, `artifacts/`)

**Specification.** A single machine-readable source of truth (`artifacts/release/CURRENT_TRUTH.json`)
that every prose surface must agree with; generated docs carry `--check` sync gates.

- **Generated** (sync-enforced): `STATUS.md`, `DECISION.md`, `CORE.md`, `DEMONSTRATION.md`,
  `ADVERSARIAL_VALIDATION.md`.
- **Canonical hand-authored**: `FORMAL_VERDICT.md`, `CLAIM_AUDIT.md`, `LIMITATIONS_HARD.md`,
  `REPRODUCE.md`, `README.md`.
- **Pre-registration** (frozen-before-run): `docs/preregistration/*`, `docs/validation/*PROTOCOL.md`,
  S3 / multi-null protocols.
- **Key artifacts**: `CURRENT_TRUTH.json`, `S3_CONFIRMATORY_VERDICT.json`,
  `MULTI_NULL_ROBUSTNESS.json`, `S2_SPECIFICITY_CALIBRATION.json`, `bnci2014_001/*`, `risk/*`.

**Assessment** — accuracy **5**, clarity **3**, logic **5**, factuality **5**, aesthetics **3**,
simplicity **2**, elegance **3**. *Factuality and logic are exemplary — the truth-contract /
grounding model is the heart of the repo. Clarity and simplicity suffer from **document sprawl**:
~90 docs with some near-duplicates (`ARCHITECTURE.md` vs lowercase `architecture.md`;
`VALIDATION.md` / `VALIDATION_TIERS.md` / `VALIDATION_PROTOCOL.md`) and several inferred-purpose
files. A reviewer entering cold needs a map — which `REVIEWER_PACKET.md` provides, but the long tail
dilutes it.*

---

## 5. Research, replication & BNCI (`research/`, `cases/`, `docs/replication/`)

**Specification.** Honest cross-subject / cross-dataset falsification, kept strictly out of the
validated claim set until artifacts exist.

- `research/bci_generalization/*` — LOSO on PhysioNet/MOABB; `run_bnci_confirmatory.py` (locked
  finite-N method); `audit_bnci_lock.py` (EXECUTABLE | BLOCKED_*); current state **`BNCI_BLOCKED_METHOD`**.
- `cases/001_physionet_eegnet/*` — within-subject vs LOSO collapse, decoder-agnostic, self-verifying dossier.
- `docs/replication/{CHO2017,LEE2019}_PROTOCOL.md` + `artifacts/replication/*` — scaffolds only;
  **`multi_dataset_replication_state = NOT_DONE`**.

**Assessment** — accuracy **5**, clarity **4**, logic **5**, factuality **5**, aesthetics **4**,
simplicity **4**, elegance **4**. *Discipline is the strength: BNCI stays method-blocked and
replication stays NOT_DONE — no claim outruns its artifact. The honest `BLOCKED_METHOD` over a
tempting run-to-result is exactly the intended behavior.*

---

## 6. Tests, workflows, supply chain (`tests/` 95, `.github/workflows/` 16, `fuzz/`, `benchmarks/`)

**Specification.** Every invariant has an executable test; every gate has a workflow; the package
builds reproducibly offline.

- Tests by area: surrogate/statistics, claim-safety/statistical-claims/truth-sync, adversarial/
  property/fuzz, public-execution/cli-contract, bci_generalization, evidence.
- Workflows: `ci`, `hermetic-ci`, `architecture`, `adversarial-validation`, `degradation-statistics`,
  `mutation-kill`, `provenance-sbom`, `release-dry-run`, `release`, `publish-{testpypi,pypi}`,
  `security`, `scorecard`, …
- Invariants (`docs/INVARIANTS.md`): 7 axioms (determinism, no-promotion, fail-closed monotonicity,
  anchor, provenance closure, raw-signal guard, seed-stability).

**Assessment** — accuracy **5**, clarity **4**, logic **5**, factuality **5**, aesthetics **4**,
simplicity **3**, elegance **4**. *Mutation-kill + offline-hermetic + property/fuzz is a serious
test posture. Simplicity is dented by the same multiplicity as the gates (16 workflows, overlapping
offline/hermetic jobs), and the slow `release-gate-dry-run` is a wall-clock tax.*

---

## 7. Honest weaknesses (the falsification turned inward)

1. **Simplicity is the weakest axis.** 57 tools + 16 workflows + ~90 docs is a large surface for one
   instrument. Overlapping validators and near-duplicate docs (`ARCHITECTURE.md`/`architecture.md`,
   the `VALIDATION*` trio) are real redundancy. *Fix:* a declarative gate registry + a doc index that
   marks each file canonical / generated / historical.
2. **Three surrogate implementations** (`surrogate_engine`, `reference_surrogate`, `multi_null`'s
   standalone IAAFT) are justified as independent cross-checks but should be labelled as such in one
   place so they don't read as drift.
3. **External validation is still open** (`LIMITATIONS_HARD.md`): TISEAN parity NEEDS_EXTERNAL_CHECK;
   real-EEG only partial (small-n LOSO); multi-dataset replication NOT_DONE; BNCI method-blocked.
   These are correctly *not* claimed — the gap is in coverage, not in honesty.
4. **Provenance self-reference**: `CURRENT_TRUTH.main_commit` is structurally one commit behind HEAD
   (committing the refresh advances HEAD). It anchors the correct merge commit; exact equality is
   impossible by construction, and this is documented rather than papered over.

## Scorecard summary

| Subsystem | Acc | Clar | Logic | Fact | Aesth | Simpl | Eleg |
|---|---|---|---|---|---|---|---|
| Runtime engine | 5 | 5 | 5 | 5 | 4 | 3 | 4 |
| Bonn bright-line | 5 | 5 | 5 | 5 | 5 | 4 | 5 |
| Gate battery (tools) | 5 | 4 | 5 | 5 | 3 | 2 | 3 |
| Truth & docs | 5 | 3 | 5 | 5 | 3 | 2 | 3 |
| Research / BNCI | 5 | 4 | 5 | 5 | 4 | 4 | 4 |
| Tests / workflows | 5 | 4 | 5 | 5 | 4 | 3 | 4 |

**Verdict.** Accuracy, logic, and factuality are uniformly maximal — the repository's reason to
exist. The Bonn bright-line is its most elegant subsystem. The standing debt is **simplicity**:
the gate, workflow, and document surfaces have grown faster than they have been consolidated. None of
this inflates a claim; it raises the cost of reading. Consolidation is the highest-leverage next
investment.
