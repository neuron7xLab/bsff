<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

<!--
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
-->

# Invalid Use and Scope Boundary

BSFF is a falsification framework for a narrow, well-defined class of claims. It
is not a general-purpose verifier. This document states the valid scope, the
categories of claim that fall outside it, how out-of-scope claims are disposed
of, and the guarantee that an out-of-scope claim never receives a misleading
positive verdict.

The boundary is enforced in code by `src/bsff/scope_guard.py` and exercised by
`tests/test_scope_guard.py`. The classification is deterministic and lexical:
every decision is driven by explicit metadata flags and a small, auditable token
table. There is no hidden model.

## Valid scope

BSFF validly adjudicates exactly one kind of claim:

> A **falsifiable, empirical, time-series signal claim** that can be attacked
> with surrogate testing and leakage detection.

In practice this means a claim about temporal structure in a neural/biosignal
time series (EEG, ECoG, sEEG, spike, LFP), of the form the engine can refute
with a spectral/covariance-preserving surrogate null and a leakage audit.

Only an in-scope claim can receive a `SURVIVED` verdict, and only after passing
the leakage-first and surrogate-test logic in `verdict_engine.py`.

A scope verdict has one of three dispositions:

| Disposition   | Meaning                                                              |
| ------------- | ------------------------------------------------------------------- |
| `IN_SCOPE`    | The claim is admissible; the falsification battery may run.          |
| `UNSUPPORTED` | Out of scope; the engine has no evidence to offer. Informative.     |
| `QUARANTINED` | Out of scope and harm-bearing; hard-isolated, never re-routed.      |

## Out-of-scope categories

Each category below is rejected before any surrogate test runs. The example
shows a claim that triggers it.

### `CLINICAL` — quarantined

Diagnosis, treatment, prognosis, or any medical-outcome claim. BSFF does not
diagnose, treat, or evaluate medical outcomes and has no instrument that bears
on such a claim.

> Example: "This headset diagnoses depression from the EEG."

### `REGULATORY` — quarantined

Approval, clearance, certification, or compliance claims. BSFF is not a
certifying authority and cannot establish regulatory standing.

> Example: "Our device is FDA-approved for clinical use."

### `EMOTION_WITHOUT_SIGNAL` — unsupported

An emotion- or mental-state-reading claim with no declared signal basis. With no
time series there is no surrogate null to attack, so no falsification is
possible. (An affect claim that *is* grounded in a declared EEG signal is in
scope and is not rejected here.)

> Example: "The app reads your emotions and detects sadness." (no signal)

### `NON_TIME_SERIES` — unsupported

A claim that is not over time. The surrogate-null battery requires a temporal
signal; a static or tabular assertion has no admissible null.

> Example: "Survey scores correlate across subjects."

### `CAUSAL_WITHOUT_ROUTE` — unsupported

A causal claim with no declared causal route (e.g. transfer entropy or an
intervention design). A surrogate test of association cannot license causation.

> Example: "Alpha power causes improved memory." (no causal route declared)

### `LOGICAL_WITHOUT_DATA` — unsupported

A logical, mathematical, or definitional claim with no empirical data. A theorem
is not falsifiable by surrogate testing; nothing empirical bears on a deductive
assertion.

> Example: "By definition the theorem holds: 2 + 2 equals 4."

## Quarantine dispositions

- **`QUARANTINED`** is reserved for the harm-bearing categories (`CLINICAL`,
  `REGULATORY`). A falsification engine that appears to endorse a clinical or
  regulatory claim can cause real-world harm, so these are hard-isolated.
- **`UNSUPPORTED`** is used for the remaining categories. The engine simply has
  no evidence to offer — informative, but not dangerous.

Both dispositions carry an explicit, human-readable caveat naming the reason for
rejection.

## Guarantee

The module enforces a single invariant:

> **No out-of-scope claim can ever return `SURVIVED`.**

`guard_verdict(scope_verdict, proposed_verdict)` is the enforcement point. When a
claim is out of scope, any proposed `SURVIVED` is downgraded to the scope
disposition (`UNSUPPORTED` or `QUARANTINED`); a non-positive verdict passes
through unchanged. In-scope verdicts are not altered.

For call sites that prefer to refuse rather than downgrade, `enforce_scope(claim)`
raises `ScopeError` for any out-of-scope claim and returns `None` when in scope.

This is the fail-closed direction: an assertion outside the engine's competence
must never masquerade as something that was tested and survived.

## BIDS-EEG ingestion refusals

The real-data entry point `bsff.bids.load_bids_eeg` adds two ingestion guards on
top of the scope boundary above. They are enforced in code (`src/bsff/bids.py`)
and exercised by `tests/test_bids_ingestion.py`.

### No hidden labels (no-hidden-labels policy)

A raw BIDS-EEG `*_eeg.tsv` holds **electrode channels only**. If the data file
carries a column whose name looks like a class label or experimental target —
`label`, `target`, `class`, `y`, `condition`, `stimulus`, `event`,
`trial_type`, `marker`, ... — ingestion raises `bsff.bids.InvalidUseError`.

A falsifier that can read the label has already leaked the answer: the surrogate
null and the verdict would be contaminated by information the model must not see.
Put labels in BIDS `events.tsv`, never in the signal file.

### No feature-table leakage (no-feature-table-leakage policy)

If the data file looks like a **precomputed feature matrix** — column names such
as `feat_*`, `mean_*`, `std_*`, `psd_*`, `bandpower`, `csp_*`, `ica_comp*`,
`wavelet_*`, `spectral_*`, `embedding*` — ingestion is refused. Those features
are downstream of preprocessing choices (band, window, normalization) that are
exactly where leakage hides. BSFF falsifies the **raw signal** so the surrogate
null is built on the same object the claim is about; a feature table is not a
falsifiable raw recording.

### Layout fail-closed refusals (`BidsLayoutError`)

`load_bids_eeg` also aborts on: a missing `sub-XX/eeg/` directory, missing
`*_eeg.json` sidecar or `*_channels.tsv`; a missing/invalid `SamplingFrequency`;
an `*_eeg.tsv` header that does not match the `*_channels.tsv` names; non-numeric
or non-finite (`NaN`/`Inf`) samples; or fewer than 16 samples. None of these are
warnings — a contract violation aborts the run.
