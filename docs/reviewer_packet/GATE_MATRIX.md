# OpenAI-2026 Validation Grid — Gate Matrix

> **Disclaimer.** The "OpenAI-2026 Validation Grid" is an **internal
> OpenAI-grade research-validation target**, **NOT** an OpenAI certification.
> BSFF is **not affiliated with, certified by, or endorsed by OpenAI.**

All 18 gates. Jobs 01–13 run as workflow jobs in
`.github/workflows/openai-2026-validation-grid.yml`; gates 14–18 are derived in
the final roll-up (`gate_results`) from their dedicated artifacts and validators.
Every gate contributes to the machine-derived verdict in
`artifacts/final/openai_2026_validation_verdict.json`.

| Gate | Dimension | What it proves | How it fails | Evidence artifact | Local command |
| --- | --- | --- | --- | --- | --- |
| 01-lock-integrity | Supply chain | Locks valid, hash-pinned, resolvable | Lockfile invalid or unresolvable under hashes | `requirements/*.lock` (hashed into `dependency_lock_hashes`) | `python tools/validate_lockfiles.py && python -m pip install --require-hashes --dry-run -r requirements/ci.lock` |
| 02-hermetic-offline-tests | Offline correctness | Suite passes with network denied | Any non-slow test fails or network reachable | `artifacts/hermetic/offline_evidence.json` | `python -m pytest tests/ -m "not slow" --disable-network` |
| 03-adversarial-oracles | Adversarial | Adversarial operating-characteristic + oracle invariants hold | Adversarial test fails or `--check` drift | `artifacts/adversarial/corpus_matrix.json` | `python -m pytest tests/test_adversarial_operating_characteristics.py tests/adversarial && python tools/update_adversarial_validation.py --check` |
| 04-property-tests | Property | Property-based invariants hold | Any property test fails | `tests/property` results | `python -m pytest tests/property` |
| 05-fuzz-smoke | Fuzz | No crash on signal/verdict/policy inputs | A fuzz target crashes within budget | fuzz run logs | `python fuzz/fuzz_signal_inputs.py --max-runs 1000 --seed 2026` (and `fuzz_verdict_json.py`, `fuzz_policy_profiles.py`) |
| 06-mutation-kill | Mutation | Mutation score 1.0 vs live mutant set | Survivor, score `< 1.0`, `< 8` mutants, or stale report | `artifacts/adversarial/mutation_kill_report.json` | `python tools/mutation_kill_gate.py --strict && python tools/validate_mutation_report.py artifacts/adversarial/mutation_kill_report.json` |
| 07-wheel-runtime | Build | Wheel imports and runs offline | Wheel import/run fails offline | built wheel | `python tools/validate_wheel_runtime.py --offline` |
| 08-sbom-provenance | Supply chain | SBOM reproducible, provenance verifies | SBOM `--check` mismatch or provenance fails | `artifacts/sbom/*` | `python tools/generate_sbom.py --outdir artifacts/sbom && python tools/validate_provenance.py` |
| 09-security | Security | No secrets, Actions policy holds, no known CVE | Secret found, policy violation, or vulnerability | scan output | `python tools/scan_secrets.py && python tools/check_github_actions_policy.py && python -m pip_audit --strict` |
| 10-statistical-power | Statistics | Power profile meets threshold | Profile missing or below threshold | `artifacts/statistics/power_profile.json` | `python tools/statistical_power_profile.py --output artifacts/statistics/power_profile.json && python tools/validate_power_profile.py artifacts/statistics/power_profile.json` |
| 11-degradation | Performance | Valid baseline, no regression | Baseline missing/malformed or regression | `artifacts/benchmarks/baseline.json`, `current.json` | `python -m pytest benchmarks --benchmark-json=artifacts/benchmarks/current.json && python tools/compare_benchmark_baseline.py artifacts/benchmarks/baseline.json artifacts/benchmarks/current.json` |
| 12-api-cli-contract | Contract | Public API/CLI surface frozen and importable | `bsff.api.__all__` drift, non-callable symbol, or test fail | `src/bsff/api.py`, contract tests | `python -m pytest tests/test_public_api_contract.py tests/test_cli_contract.py` |
| 13-final-verdict | Roll-up | Machine-derives consolidated PASS/FAIL | Any sub-gate FAIL or schema error | `artifacts/final/openai_2026_validation_verdict.json` | `python tools/final_validation_verdict.py --output artifacts/final/openai_2026_validation_verdict.json` |
| 14-replayability | Determinism | Seed-stable across ≥3 seeds, hashes match | `< 3` seed sets, verdict class unstable, or hashes diverge | `artifacts/replay/replayability_report.json` | (re-run deterministic subset across seeds; see `REPLAY_INSTRUCTIONS.md`) |
| 15-meta-validation | Meta | Validators themselves are tested | `tests/meta_validation` absent or failing | `tests/meta_validation` | `python -m pytest tests/meta_validation` |
| 16-red-team-corpus | Red team | Every red-team category killed | Matrix missing/invalid or a category not killed | `artifacts/redteam/redteam_matrix.json` | `python tools/validate_redteam_matrix.py` |
| 17-claim-integrity | Claims | No forbidden/unsupported claim present | Any forbidden-claim violation | `claim_audit` in the verdict | `python tools/validate_openai_2026_claims.py --json` |
| 18-artifact-digest-binding | Integrity | Every required artifact present and sha256-bound | Any required artifact missing from digest map | `artifact_digests` in the verdict | `python tools/final_validation_verdict.py` (computes digests) |

The full grid runs locally with `make openai-2026`.
