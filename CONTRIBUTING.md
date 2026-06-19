<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Contributing to BSFF

BSFF accepts contributions that make BCI/EEG claims harder to fake, easier to reproduce, or cheaper to falsify. Decorative architecture prose without executable gates belongs in the museum of human optimism.

## Development loop

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,stats,leakage]'
python -m pytest tests/ -v --tb=short
bsff-validate --output artifacts/bsff_phase1_validation.json
python tools/validate_truth_contract.py
python tools/validate_open_source_readiness.py
python tools/check_github_actions_policy.py
python tools/scan_secrets.py
```

## Pull request contract

Every PR must state:

1. what false claim it prevents,
2. what deterministic test proves it,
3. what caveat remains,
4. whether it changes verdict semantics.

## Evidence rules

- Do not claim clinical, regulatory, or TISEAN validation without a machine-readable artifact.
- Do not hide non-convergence, leakage warnings, stationarity failures, or small-n caveats.
- Do not add dependencies without explaining their falsification value.
- New detectors need at least one positive and one negative test fixture.

## Test naming

Use behavior names, not implementation trivia:

```text
test_stationarity_gate_flags_random_walk
test_miaaft_budget_calibration_selects_first_accepted_budget
test_truth_contract_rejects_missing_phase1_status
```
