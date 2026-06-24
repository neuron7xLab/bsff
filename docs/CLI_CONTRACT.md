<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF CLI contract

The `bsff` command line is the operational surface of the falsifier. This
document is the contract for that surface: the three-command quickstart, the full
command table, and the exact flags of the core verdict commands. The authoritative
list of registered subcommands is always
[`src/bsff/cli.py`](../src/bsff/cli.py) — and [`../STATUS.md`](../STATUS.md)
records the live count parsed from it.

The console entry points are `bsff` and `bsff-validate` (both map to
`bsff.cli:main`). With no subcommand, the tool runs the operational-kernel
self-validation and writes the Phase-1 artifact.

## Three-command quickstart

```bash
# 1. install
pip install bsff                 # or: pip install -e '.[dev]' from a checkout

# 2. check the environment is wired correctly (fail-closed preflight)
bsff doctor

# 3. confirm the build is release-ready (aggregated gate)
bsff release-check
```

`bsff doctor` is the environment/capability preflight; `bsff release-check`
aggregates the readiness gates into a single pass/fail. Run both before trusting
any verdict.

## Command table

Commands marked **(core)** are registered today in `src/bsff/cli.py`. Commands
marked **(operational)** are the orchestration/release surface being added
alongside the core verdict commands; consult `bsff <command> --help` for the
authoritative flags of any command in your installed version.

| Command | Tier | Purpose |
|---|---|---|
| `bsff doctor` | operational | Fail-closed environment + capability preflight (deps, extras, versions). |
| `bsff capabilities` | operational | Report which optional features are available given installed extras. |
| `bsff validate` | operational | Run the self-validation / contract gates and emit a machine-readable report. |
| `bsff release-check` | operational | Aggregate readiness gates into a single release pass/fail. |
| `bsff reproduce` | operational | Re-run a recorded case (`--case`), or the Bonn S2 bright-line (`reproduce bonn-s2`). |
| `bsff benchmark` | operational | Run a real-data benchmark (`benchmark bonn-bright-line`) and emit its verdict. |
| `bsff evidence` | operational | Verify the committed evidence bundle (`evidence verify`): coherence, hashes, release gate. |
| `bsff bids-app` | operational | BIDS-App entry point for the deterministic real-EEG ingestion path. |
| `bsff selftest` | core | Run the operational-kernel self-validation; write the Phase-1 artifact. |
| `bsff falsify` | core | Aim BSFF at an external claim + signal; emit a provenance-stamped verdict case-file. |
| `bsff adjudicate` | core | Anchor, classify, route, and ledger the claims of an external source. |
| `bsff adjudicate-batch` | core | Adjudicate a corpus from a manifest; consolidate dispositions. |
| `bsff adjudicate-data` | core | Adjudicate a raw series file (bring-your-own-data) to a real verdict. |
| `bsff adjudicate-moabb` | core | Adjudicate a MOABB EEG recording (needs the `moabb` extra + network). |
| `bsff normalize` | core | Read a raw EDF/EDF+/BDF file into a canonical signal array. |
| `bsff render` | core | Render an adjudication/batch report as HTML or Markdown. |
| `bsff ledger-verify` | core | Verify the hash-chain integrity of a truth ledger. |
| `bsff ingest` | core | Fetch an arXiv abstract as a provenance-stamped source. |

## Core command flags

Exact flags for the core verdict commands (from `src/bsff/cli.py`).

### `bsff falsify`

Falsify an external claim against a signal file.

| Flag | Required | Default | Meaning |
|---|---|---|---|
| `--claim` | yes | — | `ClaimSpec` file (`.json`/`.yaml`). |
| `--signal` | yes | — | Signal file (`.npy`/`.csv`/`.tsv`). |
| `--policy` | no | `strict` | One of `smoke`, `standard`, `strict`. |
| `--seed` | no | `123` | Deterministic surrogate seed. |
| `--out` | no | — | Path to write the verdict case-file JSON. |

```bash
bsff falsify --claim claim.json --signal recording.npy --policy strict --out verdict.json
```

### `bsff adjudicate-data`

Adjudicate a raw series file to a real verdict.

| Flag | Required | Default | Meaning |
|---|---|---|---|
| `--data` | yes | — | Series file (`.npy`/`.csv`); 1 or 2 rows. |
| `--test` | yes | — | `nonlinear_structure` or `directed_coupling`. |
| `--target` | no | — | Target series for `directed_coupling`. |
| `--name` | no | `real-data` | Dataset name for the record. |
| `--allow-nonraw` | no | off | Override the raw-signal guard (recorded in provenance). |
| `--surrogates` | no | `99` | Surrogate count. |
| `--seed` | no | `123` | Deterministic seed. |
| `--stability-seeds` | no | `0` | Certify the verdict across N seeds; fail-closed to `UNSTABLE` if it flips. |
| `--min-agreement` | no | `1.0` | Required modal-verdict fraction (1.0 = unanimous). |
| `--out` | no | — | Path to write the verdict JSON. |

```bash
bsff adjudicate-data --data recording.npy --test nonlinear_structure --out verdict.json
```

### `bsff normalize`

Read a raw EDF/EDF+/BDF file into a canonical array (pure Python, no `mne`).

| Flag | Required | Default | Meaning |
|---|---|---|---|
| `--input` | yes | — | Path to an `.edf`/`.bdf` file. |
| `--out` | no | — | Write the signal as `.npy` (+ a provenance sidecar). |
| `--channel` | no | — | Select one channel (label or index). |
| `--list` | no | off | List channels + rates without extracting. |

### `bsff adjudicate` / `adjudicate-batch` / `render` / `ledger-verify` / `ingest`

| Command | Key flags |
|---|---|
| `adjudicate` | `--source-text` \| `--arxiv`, `--claims` (required), `--source-id`, `--kind`, `--uri`, `--ledger`, `--out`. |
| `adjudicate-batch` | `--manifest` (required), `--ledger`, `--out`. |
| `render` | `--report` (required), `--format` (`html`\|`md`), `--out`. |
| `ledger-verify` | `--ledger` (required). |
| `ingest` | `--arxiv` (required), `--out`. |

## Determinism contract

Every core verdict command is deterministic: the same inputs and the same
`--seed` produce the same verdict and the same SHA-256 manifest. Verdicts,
surrogate ranges, leakage flags, and caveats are serialised to JSON; the manifest
hash is recomputed and verified on load. Raw-data ingestion is fail-closed
(`load_series` / BIDS ingestion refuse malformed or feature-like input), and any
override (`--allow-nonraw`) is stamped into provenance, never silent.

## See also

- [`METHODOLOGY.md`](METHODOLOGY.md) — what a verdict means.
- [`DATASETS.md`](DATASETS.md) — the real-data socket and raw-signal guard.
- [`REAL_EEG_VALIDATION.md`](REAL_EEG_VALIDATION.md) / [`BIDS_APP.md`](BIDS_APP.md) — the BIDS path.
- [`ADJUDICATION.md`](ADJUDICATION.md) — the adjudication/ledger model.
- [`../STATUS.md`](../STATUS.md) — live command count + readiness.
