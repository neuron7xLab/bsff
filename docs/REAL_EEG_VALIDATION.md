<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

<!--
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
-->

# Real-EEG validation path (deterministic BIDS ingestion)

BSFF falsifies a claim about a **raw neural signal**. This document defines the
deterministic, fail-closed path from a BIDS-EEG dataset to a machine-readable
verdict, the policy that keeps the ingestion honest, and the four expected
verdict cases.

> **HONESTY — read first.** The dataset shipped under
> `examples/real_eeg_bids/bids/` is a **SYNTHETIC, EEG-SHAPED FIXTURE**
> (deterministic Hénon-map traces), **not** a real human recording. It exists so
> the path runs offline with zero setup. Nothing about a verdict on this fixture
> is a finding about real neural data. The section
> [Substituting a real dataset](#substituting-a-real-dataset) shows how to point
> the same loader at a real public BIDS dataset.

## Deterministic ingestion

`bsff.bids.load_bids_eeg(bids_dir, subject=..., task=...)` reads a minimal
BIDS-EEG layout with pure stdlib + numpy (no mandatory `mne`):

```
<bids_dir>/sub-<subject>/eeg/
    sub-<subject>_task-<task>_eeg.tsv[.gz]   # raw channels x time
    sub-<subject>_task-<task>_eeg.json       # sidecar: SamplingFrequency
    sub-<subject>_task-<task>_channels.tsv   # channel names
```

It returns a `BidsRecording` (subject, task, channels, fs, data, source path,
**sha256 of the raw data file**). Ingestion is **fail-closed**: a missing
sidecar, missing channels file, missing/invalid sampling rate, header/channel
mismatch, non-finite sample, or fewer than 16 samples aborts the run (raising
`BidsLayoutError`) rather than coercing a recording into a passing verdict.

`bsff.bids.run_bids_case(...)` then builds a `ClaimSpec`, calls the real
fail-closed engine (`bsff.verdict_engine.evaluate_claim`), and returns a
`{verdict, manifest}` dict. The manifest records input hashes, software versions
(via `importlib.metadata`), and the reproducible command.

## Dataset declaration (source / checksum / preprocessing)

Every real run must record, in the manifest or alongside it:

| Field            | Meaning                                                        |
| ---------------- | ------------------------------------------------------------- |
| dataset source   | DOI / OpenNeuro accession (e.g. `ds00XXXX`) + dataset version |
| input checksum   | sha256 of the raw `_eeg.tsv[.gz]` (emitted as `data_sha256`)  |
| sampling rate    | from the `_eeg.json` sidecar (`SamplingFrequency`)            |
| preprocessing    | declared explicitly; BSFF falsifies the signal **as given**   |

BSFF does **not** silently filter, re-reference, or resample. Any preprocessing
is the operator's responsibility and must be declared, because preprocessing
choices are exactly where leakage hides.

## No hidden labels / no feature-table leakage

Two ingestion guards keep the path honest (full text in
[`INVALID_USE.md`](INVALID_USE.md)):

- **No hidden labels.** A label-like column (`label`, `target`, `class`, `y`,
  `condition`, `event`, `trial_type`, ...) in the `_eeg.tsv` is **refused**
  (`InvalidUseError`). A falsifier that can read the label has leaked the answer.
- **No feature-table leakage.** A precomputed-feature column (`feat_*`, `psd_*`,
  `bandpower`, `csp_*`, `ica_comp*`, ...) is **refused**. BSFF falsifies the raw
  signal, not an already-engineered feature matrix.

## The four expected verdict cases

Reproduced offline by `python examples/real_eeg_bids/run.py` and gated by
`python tools/validate_real_eeg_case.py`. Every rejection comes from the real
guard/engine — none are hardcoded.

| # | Case                  | Path                                   | Outcome                  |
| - | --------------------- | -------------------------------------- | ------------------------ |
| 1 | valid signal          | nonlinear (Hénon) raw trace            | **SURVIVED** (engine)    |
| 2 | feature-table input   | `psd_*`/`bandpower` columns            | **REFUSED** (ingest guard)|
| 3 | label leakage         | flagged leak → engine short-circuit    | **REFUTED** (engine)     |
| 4 | nonstationarity       | trended trace trips KPSS gate          | verdict + **KPSS caveat**|

A `SURVIVED` here means only that the nonlinear-structure claim was not refuted
by the surrogate null on this fixture; it is **not** evidence about real EEG.

## Substituting a real dataset

The loader works on any minimal BIDS-EEG tree. To validate on real data:

1. Download a public BIDS-EEG dataset, e.g. an OpenNeuro `ds-XXXXXX` EEG dataset.
   Record its DOI, version, and checksum.
2. For one run, lay out `sub-XX/eeg/sub-XX_task-YY_eeg.tsv` (channels × time),
   its `_eeg.json` (`SamplingFrequency`), and `_channels.tsv` as above. Many
   OpenNeuro EEG datasets are already BIDS; convert the chosen run's
   channels-by-time matrix to the `_eeg.tsv` shape if it ships as EDF/BrainVision.
3. Run:

   ```python
   from bsff.bids import run_bids_case
   out = run_bids_case("/path/to/ds-XXXXXX", subject="01", task="rest")
   print(out["verdict"]["verdict"])
   ```

4. Keep `out["manifest"]` next to the verdict for provenance (see
   [`BIDS_APP.md`](BIDS_APP.md) and [`DATALAD_PROVENANCE.md`](DATALAD_PROVENANCE.md)).

The shipped fixture stays synthetic so CI never depends on the network.
