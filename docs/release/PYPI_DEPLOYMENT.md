<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# PyPI deployment

BSFF publishes via **Trusted Publishing (OIDC)** — no API token is stored.

- Package: `bsff`  ·  version: from `pyproject.toml` (`[project].version`).
- **TestPyPI first** (`.github/workflows/publish-testpypi.yml`), then **PyPI**
  (`.github/workflows/publish-pypi.yml`).

## One-time setup (pypi.org + test.pypi.org)
Register a Trusted Publisher (pending publisher) for project `bsff`:
owner `neuron7xLab`, repo `bsff`, workflow filename, environment (`pypi` / `testpypi`).

## TestPyPI (dry-run)
Trigger: `workflow_dispatch` or push a `testpypi-v<version>` tag. Gates run before publish
(`validate_current_truth`, `validate_truth_contract`, `bsff evidence verify`, tag==version,
`twine check`). `skip-existing: true`.

## PyPI (real)
Trigger: a published GitHub Release or a `v<version>` tag. Protected `pypi` environment
(manual approval). Same gates; **no** `skip-existing` (a duplicate version fails).

## Tag / version policy
`v<version>` for PyPI, `testpypi-v<version>` for TestPyPI; the tag version MUST equal
`pyproject.toml` `[project].version` or the workflow fails.

## Rollback
PyPI is append-only; you cannot overwrite a version. To roll back, **yank** the bad version
on PyPI and publish a higher patch version. Never reuse a version number.

## Verification (consumer)
```bash
pip install bsff==0.4.0
bsff selftest
bsff evidence verify
```

## Secrets policy
No API token unless Trusted Publishing is unavailable. If a token is ever required, store it
as an environment secret on the protected `pypi` environment only.
