<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF validation protocol

A green badge is only trusted when it is backed by machine evidence. This protocol
is what every change must clear; CI enforces the equivalent jobs.

## One command

```bash
make openai-2026      # lock -> offline tests -> build-proof -> verify
```

## What it proves

| Gate | Tool / job | Evidence |
|---|---|---|
| Hermetic deps | `tools/validate_lockfiles.py`, `hermetic-ci.yml` | every dep `==`-pinned + sha256 |
| Offline runtime | `tests/conftest.py` offline guard | no external network during tests |
| Wheel runtime | `tools/validate_wheel_runtime.py [--offline]` | runs from the installed wheel |
| Signed provenance + SBOM | `provenance-sbom.yml`, `tools/validate_provenance.py` | Sigstore attestation + SPDX/CycloneDX |
| Mutation score 100% | `tools/mutation_kill_gate.py`, `validate_mutation_report.py` | 8/8 mutants killed |
| Property / fuzz / chaos | `tests/property`, `fuzz/`, `tests/adversarial` | fail-closed under generated inputs |
| Statistical power | `tools/statistical_power_profile.py`, `validate_power_profile.py` | FPR ≤ 0.05, detection ≥ 0.80 |
| Degradation | `tools/compare_benchmark_baseline.py` | calibration-normalized, ≤ 15% |
| API / CLI contract | `tests/test_public_api_contract.py`, `tests/test_cli_contract.py` | frozen signatures |
| Final verdict | `tools/final_validation_verdict.py` | machine-derived PASS/FAIL |

## Verdict discipline

Any unknown, skipped, nonconverged, leaked, poisoned, underpowered, or statistically
invalid result collapses to `UNSUPPORTED` or `REFUTED` — never `SURVIVED`. A
`SURVIVED` verdict requires a converged null and, under Bayesian policy, a
corroborating effect-size Bayes factor.

## Reporting a counterexample

If you can make the pipeline emit a `SURVIVED` it should not, or crash on input it
should refuse, open an **Adversarial counterexample** issue with the seed and input
— it is a first-class contribution.
