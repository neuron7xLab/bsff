<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Development

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
python -m pip install --upgrade pip
# Reproducible, hash-pinned (matches CI):
python -m pip install --require-hashes -r requirements/ci.lock
python -m pip install --no-deps -e .
# Or, for quick local iteration:
python -m pip install -e '.[dev,leakage,stats,yaml]'
```

## Dependency locks

Locks live in `requirements/` and are fully hash-pinned. Regenerate after changing
`pyproject.toml` dependencies:

```bash
python -m pip install pip-tools
pip-compile pyproject.toml --extra dev --extra leakage --extra stats --extra yaml --generate-hashes -o requirements/ci.lock
pip-compile pyproject.toml --extra dev --generate-hashes -o requirements/dev.lock
pip-compile pyproject.toml --extra dev --extra fuzz --generate-hashes -o requirements/fuzz.lock
pip-compile pyproject.toml --extra dev --extra security --generate-hashes -o requirements/security.lock
python tools/validate_lockfiles.py
```

## Running the gates locally

```bash
python -m ruff check src tests tools benchmarks fuzz
python -m ruff format --check src tests tools benchmarks fuzz
python -m pytest tests/ -m "not slow"
python -m pytest tests/property tests/adversarial
python tools/mutation_kill_gate.py
python tools/validate_wheel_runtime.py
python tools/generate_sbom.py --check
python tools/statistical_power_profile.py && python tools/validate_power_profile.py artifacts/statistics/power_profile.json
python tools/final_validation_verdict.py
```

The offline guard (`tests/conftest.py`) denies external network during tests by
default; mark an exception with `@pytest.mark.allow_network`.

## Conventions

- Everything ships ruff-clean (lint + format) and fail-closed.
- Generated docs/artifacts are produced by tools, never edited by hand
  (`STATUS.md`, `MANIFEST.json`, `ADVERSARIAL_VALIDATION.md`, SBOMs, reports).
- New public API goes through `bsff.api` and updates `docs/API_CONTRACT.md`.
- See `docs/VALIDATION_PROTOCOL.md` for the full evidence matrix.
