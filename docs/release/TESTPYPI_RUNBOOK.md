<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# TestPyPI runbook

1. Ensure `pyproject.toml` `[project].version` is the intended version (e.g. `0.4.0`).
2. Confirm gates locally: `bsff evidence verify` (PASS), `python tools/validate_current_truth.py`.
3. Register the TestPyPI Trusted Publisher (one-time) for `bsff` / `neuron7xLab/bsff` /
   `publish-testpypi.yml` / environment `testpypi`.
4. Trigger:
   - `gh workflow run publish-testpypi.yml`, or
   - `git tag testpypi-v0.4.0 && git push origin testpypi-v0.4.0`.
5. Confirm the run published to `https://test.pypi.org/p/bsff`.
6. Smoke-test the install:
   ```bash
   pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple bsff==0.4.0
   bsff selftest
   ```
7. Only after TestPyPI succeeds, proceed to real PyPI (`publish-pypi.yml`).
