<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->
<!-- GENERATED FILE — edit tools/update_status.py, then run it. Do not edit by hand. -->

# BSFF status

Single source of truth for release status. Regenerated from repository
facts (version, live test count, CLI surface, extras) by
`python tools/update_status.py`. CI enforces sync with
`python tools/update_status.py --check`.

## Current state

| Field | Value |
|---|---|
| Package version | `0.4.0` |
| Live test count | **318** (collected by `pytest tests/`) |
| CLI subcommands | 16 (parsed from `src/bsff/cli.py`) |
| Optional extras | `dev`, `full`, `leakage`, `moabb`, `stats`, `yaml` |

## CI state

CI is defined by [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (workflow `CI`): test +
build + nightly-extended jobs. This file does **not** assert a pass/fail
result — consult the GitHub Actions run for the relevant commit for the
authoritative status:

> See **GitHub Actions** for the live CI verdict of the current commit.

## Validation level

Instrument calibration on synthetic ground truth + independent numpy surrogate reference. NOT clinical, regulatory, or external-suite validated.

See [`docs/VALIDATION.md`](docs/VALIDATION.md) for the full evidence tier
table and [`docs/OPERATING_CHARACTERISTIC.md`](docs/OPERATING_CHARACTERISTIC.md)
for the measured false-positive / power profile.

## Release readiness

| Gate | Status |
|---|---|
| Deterministic test suite | green when CI `test` job passes (see Actions) |
| Truth contract (`tools/validate_truth_contract.py`) | enforced in CI |
| Markdown contract (`tools/validate_markdown.py`) | enforced in CI |
| Status sync (`tools/update_status.py --check`) | enforced in CI |
| Operating-characteristic calibration | committed artifact + CI smoke |
| TISEAN reference gate | numpy reference is the in-CI oracle |

## CLI surface

Subcommands registered in `src/bsff/cli.py` (source order). See
[`docs/CLI_CONTRACT.md`](docs/CLI_CONTRACT.md) for purposes and flags.

| Command |
|---|
| `bsff selftest` |
| `bsff falsify` |
| `bsff adjudicate` |
| `bsff adjudicate-batch` |
| `bsff render` |
| `bsff adjudicate-data` |
| `bsff adjudicate-moabb` |
| `bsff normalize` |
| `bsff ledger-verify` |
| `bsff ingest` |
| `bsff doctor` |
| `bsff capabilities` |
| `bsff validate` |
| `bsff release-check` |
| `bsff reproduce` |
| `bsff bids-app` |

## Known blockers / limitations

- **Not externally validated against TISEAN.** BSFF ships an independent
  numpy surrogate reference as its in-CI oracle; the real TISEAN binary is
  an optional out-of-band cross-check and is recorded as `tisean_was_run:
  false` whenever it is absent.
- **No real published dataset is shipped.** The validation corpus and the
  BIDS example are synthetic, deterministic, EEG-shaped fixtures. A verdict
  on them is a calibration, **not** a finding about real neural data.
- **Statistical scope is linear / spectral.** Nonlinear directed coupling
  (k-NN transfer entropy) and non-time-series designs (two-group, cohort)
  require their own validated tests before any claim that needs them can be
  adjudicated.
- **Not regulatory validation and does not prove BCI claims.** BSFF is a
  falsifier: it can refute or fail to refute a claim under stated attacks.
