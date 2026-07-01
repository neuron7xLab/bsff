<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->
<!-- GENERATED FILE — edit tools/update_adversarial_validation.py, then run it. Do not edit by hand. -->

# Adversarial validation

Falsification-power report for the BSFF verdict pipeline. A green CI badge is
only meaningful if the suite **kills** behavioural regressions; this document
is regenerated from machine facts by
`python tools/update_adversarial_validation.py` and verified in CI with
`--check`. It is never hand-edited.

**Final validation verdict: PASS — adversarial gates killed the intended regressions and the deterministic gates hold.**

Mutation score: **11/11** (1.0). Surrogate seed policy: _all stochastic tests must use explicit seeds_. Network policy: _no test may require network access_.

## Baseline command matrix

Reproduce every gate locally, in order:

```bash
python -m pip install -e '.[dev,leakage,stats,yaml]'
python -m ruff check src tests tools
python -m ruff format --check src tests tools
python -m pytest tests/ -m "not slow" --tb=short
python -m pytest tests/ -m slow --tb=short
python -m pytest tests/test_adversarial_operating_characteristics.py -v
python -m pytest tests/test_verdict_engine_fuzz.py -v
python tools/mutation_kill_gate.py
python tools/validate_wheel_runtime.py
python tools/generate_sbom.py --check
bsff-validate --output artifacts/bsff_phase1_validation.json
python tools/verify_all.py
python tools/update_adversarial_validation.py --check
```

## Killed mutants

Each mutant is a single-point behavioural regression in the verdict-collapse
path. `tools/mutation_kill_gate.py` applies it to an isolated copy and requires
the targeted oracle test to FAIL. A survivor is a hole in the suite.

| Mutant | File | Behaviour it breaks | Status |
|---|---|---|---|
| `MUT-001` | `src/bsff/pipeline.py` | a nonconverged surrogate null must demote the verdict to UNSUPPORTED | ✅ killed |
| `MUT-002` | `src/bsff/stages.py` | flagged leakage must short-circuit claim promotion to REFUTED | ✅ killed |
| `MUT-003` | `src/bsff/stages.py` | a nonstationary signal under fail_closed must REFUTE before surrogates | ✅ killed |
| `MUT-004` | `src/bsff/surrogate_engine.py` | rank-order rejection requires p_value <= alpha (correct one-sided semantics) | ✅ killed |
| `MUT-005` | `src/bsff/pipeline.py` | an uncorroborated frequentist rejection (BF10 < threshold) must not promote | ✅ killed |
| `MUT-006` | `src/bsff/surrogate_engine.py` | NaN/Inf input must be refused before any statistic is computed | ✅ killed |
| `MUT-007` | `src/bsff/pipeline.py` | every verdict must carry a 64-hex evidence contract hash | ✅ killed |
| `MUT-008` | `src/bsff/schemas.py` | ClaimSpec must reject an underpowered surrogate_count (no silent schema drift) | ✅ killed |
| `MUT-009` | `src/bsff/surrogate_engine.py` | rank-order ties must count as not-exceeded, so a flat signal is never rejected | ✅ killed |
| `MUT-010` | `src/bsff/leakage_detector.py` | a malformed leakage record (dict missing 'flagged') must fail closed, not be ignored | ✅ killed |
| `MUT-011` | `src/bsff/surrogate_engine.py` | surrogate budget must use ceil(1/alpha)-1 so the minimum can actually reject at alpha | ✅ killed |

## Oracle fixtures

Deterministic operating-characteristic oracles in
`tests/test_adversarial_operating_characteristics.py`. Each pins one decision
the pipeline must make on an adversarial fixture.

| Test | Fixture | Policy | Required decision |
|---|---|---|---|
| `test_linear_null_never_survives_under_strict` | AR(1) linear-Gaussian null | strict | never SURVIVED (REFUTED/UNSUPPORTED) |
| `test_linear_null_false_positive_rate_within_binomial_guard` | AR(1) linear-Gaussian null battery | standard | SURVIVED count <= binomial guard |
| `test_nonlinear_positive_control_survives_with_exposed_evidence` | Hénon / logistic deterministic chaos | standard | SURVIVED on a converged null; evidence exposed |
| `test_leakage_short_circuits_to_refuted` | flagged block-design leakage | standard/strict | REFUTED; surrogate stage SKIP |
| `test_nonstationary_random_walk_fails_strict_gate_fatally` | random-walk (nonstationary) | strict | REFUTED; stationarity FAIL fatal; surrogate SKIP |
| `test_nonconverged_null_cannot_exceed_unsupported` | starved MIAAFT budget (invalid null) | custom strict | UNSUPPORTED; never SURVIVED/REFUTED |
| `test_poisoned_input_raises_and_emits_no_verdict` | NaN / Inf / too-short / wrong-shape | standard | ValueError; no VerdictJSON emitted |

## Self-breaking (property / fuzz) gate

`tests/test_verdict_engine_fuzz.py` drives Hypothesis-generated signals, policies,
leakage flags, and seeds through `evaluate_claim_pipeline` and asserts the
fail-closed contract for every input: the only acceptable refusal is a
`ValueError`; any returned verdict is one of the three terminal verdicts bound
to a 64-hex contract hash; and **SURVIVED is unforgeable** — it requires a
converged null and, under Bayesian policy, BF10 at or above the corroboration
threshold. The search is `derandomize=True`, so any defect it finds is a
deterministic, replayable artifact — the system breaks itself on purpose.

## Supply-chain inventory (SBOM)

`python tools/generate_sbom.py` emits a deterministic CycloneDX 1.5 SBOM of the
runtime dependency closure (extras excluded; components sorted; no wall-clock
timestamp or random serial, so it is hash-stable). `--check` is a fail-closed
structural gate: valid envelope, BSFF as root, every component carrying
name+version+purl, and the runtime essentials (numpy, scipy, statsmodels)
present in the closure. It rides the `build` job alongside the SLSA build-
provenance attestation, CodeQL/SARIF triage, pip-audit, and OpenSSF Scorecard
already enforced by the repository.

## Operating-characteristic thresholds

| Quantity | standard | strict |
|---|---|---|
| Surrogate count | 99 | 999 |
| Alpha | 0.05 | 0.05 |
| Bayesian corroboration min (BF10) | 3.0 | 10.0 |
| Stationarity mode | warn | fail_closed |
| Bayesian evidence | True | True |

The linear-null false-positive guard is the 99.9% upper binomial quantile
`binom.ppf(0.999, N, alpha)` over the seed battery — calibrated to nominal
alpha, not loosened. A corroboration-gate regression that inflates the
SURVIVED rate exceeds it and turns the oracle red.

## Deterministic seed policy

- all stochastic tests must use explicit seeds.
- no test may require network access; the oracle module installs an autouse fixture
  that severs `socket.connect`/`connect_ex` to prove it.
- SURVIVED requires converged surrogate evidence and corroboration where policy demands it.
- No wall-clock assertions; no nondeterministic timestamps in hash-critical
  output (mutation report and evidence artifacts are hash-stable).
- Target interpreters: 3.10, 3.11, 3.12, 3.13.

## Artifacts

- `artifacts/adversarial/baseline.json`
- `artifacts/adversarial/mutation_kill_report.json`
- `artifacts/wheel_validation.json`
- `artifacts/bsff_phase1_validation.json`
- `artifacts/sbom.cdx.json`

## CI jobs enforcing the gates

`.github/workflows/adversarial-validation.yml` — jobs: `oracle-adversarial-py312`, `mutation-kill-py312`, `wheel-runtime-py312`, `future-python-py313`.

`.github/workflows/ci.yml` — jobs: `lint`, `test`, `meta-verification`, `slow-tests`, `build`, `nightly-extended`.

The report is machine-derived: this file is regenerated from the artifacts
above and re-verified by `tools/update_adversarial_validation.py --check` in
the `oracle-adversarial-py312` job. PASS holds only while every machine gate
passes.
