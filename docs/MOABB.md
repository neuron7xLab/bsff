<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# MOABB — external-benchmark adjudication

MOABB (the Mother of All BCI Benchmarks) is where the BCI community keeps its
open EEG datasets. This is the path from a MOABB recording to a reproducible
BSFF verdict — the form an external-benchmark contribution would take.

## Reproducible verdict

```bash
pip install 'bsff[moabb]'        # optional extra: moabb + mne (heavy, not in core)

bsff adjudicate-moabb \
  --dataset Schirrmeister2017 --subject 1 \
  --channels C3 --test nonlinear_structure \
  --out verdicts/schirrmeister2017_sub1_C3.json

# directed coupling between two channels
bsff adjudicate-moabb --dataset Schirrmeister2017 --subject 1 \
  --channels C3 C4 --test directed_coupling
```

The verdict JSON records the channels, sampling rate, `preprocessing: none`, and
the sha256 of the exact extracted samples, so anyone with the same MOABB version
can reproduce it byte for byte.

## What the adapter guarantees

- **No silent channel fallback** — a requested channel that does not exist aborts
  the run; it never substitutes a different one.
- **No hidden preprocessing** — the raw signal is extracted as-is; nothing is
  filtered or re-referenced inside BSFF.
- **The raw-signal guard still applies** — if the extracted array looks like
  labels/features rather than a signal, it is refused (override is recorded).
- **Tested without the heavy deps** — the conversion is duck-typed against the
  `mne.io.Raw` interface, so its logic is validated with a stand-in; `moabb`/`mne`
  are imported only when a dataset is actually loaded.

## The honest boundary

A verdict here is *survived/refuted falsification under stated conditions* on one
channel's signal — it is **not** a claim that a dataset's published BCI result is
true or false, and BSFF does **not** prove BCI claims. The engines are
linear/spectral; nonlinear coupling and non-time-series designs are out of scope.
A real run requires `moabb` installed and network access to fetch the dataset;
this repository ships the adapter and the recipe, not the downloaded data. Once a
real verdict is produced and reproduced, it is the kind of artifact that belongs
in an external benchmark discussion — backed by its hash, not by assertion.
