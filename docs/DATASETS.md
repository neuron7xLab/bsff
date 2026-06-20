<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Datasets — ground-truth validation and the real-data socket

Empirical claims earn a real verdict only from real data. This module supplies
two halves of that: a labelled suite that proves the data-driven verdict is
*correct when the answer is known*, and a fail-closed loader so genuine
recordings plug into the same engine.

## Ground-truth validation

`bsff.datasets.GROUND_TRUTH` holds datasets whose answer is fixed by
construction. Adjudicating them is not a claim about any phenomenon — it is a
calibration: the verdict must match the label.

| dataset | structure | expected verdict | measured |
|---------|-----------|------------------|----------|
| `nonlinear_effect` | Hénon-map chaos | `SURVIVED` | `SURVIVED` (p≈0.01) |
| `nonlinear_null` | AR(1) noise | not `SURVIVED` | `REFUTED` (p≈0.38) |
| `coupling_effect` | linear X→Y | `source->target` | `source->target` (p≈0.01) |
| `coupling_null` | independent AR(1) | `none` | `none` (p≈0.51) |

A genuine effect survives; a matched null is killed. That two-sided correctness
is the precondition for trusting any verdict on data you have not seen.

## The real-data socket

```bash
# univariate recording → nonlinear-structure verdict
bsff adjudicate-data --data recording.npy --test nonlinear_structure

# two recordings → directed-coupling verdict
bsff adjudicate-data --data region_a.npy --target region_b.npy --test directed_coupling
```

`load_series` is fail-closed: a wrong shape, a non-finite value, or too few
samples aborts rather than coercing real data into a verdict. The data's sha256
is recorded in the result, so the verdict is traceable to the exact bytes.

### Raw signal only — not someone's preprocessing

BSFF must test a **raw or near-raw time-domain signal**. Feed it a feature
table, an accuracy/metric matrix, one-hot labels, or a cleaned result matrix and
it would be testing the authors' preprocessing decisions, not the neural signal —
which is lab cosplay, not science. By default `load_series` runs `check_rawness`
and **refuses** input that shows the signatures of pre-processed data:

- all-integer values (labels, counts, one-hot),
- few distinct values (categorical / quantized / an accuracy table),
- more series than samples (a transposed feature/result matrix),
- values confined to `[0,1]` with little variety (probabilities/accuracies).

Windowed float features that look numerically like a signal cannot be caught
here — that is a provenance question, so the override is **on the record**:
`require_raw=False` (CLI `--allow-nonraw`) loads the data anyway but stamps the
override and the rawness reasons into the verdict provenance. Default is reject;
an override is accountable, never silent.

## The honest boundary

This module does **not** ship real published datasets, and it does not invent
them. The synthetic suite proves the instrument is calibrated; turning a real
contested claim from `PENDING_EVIDENCE` into a verdict requires *its* raw data,
dropped into the socket above. The engines here are linear/spectral — nonlinear
directed coupling (k-NN transfer entropy) and non-time-series designs (two-group,
cohort) are out of scope and would need their own validated tests before any
claim that needs them could be adjudicated.
