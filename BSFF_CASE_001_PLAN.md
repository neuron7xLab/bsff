<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# BSFF-CASE-001 — plan

**Target.** A within-/global-validation motor-imagery accuracy claim on the
PhysioNet EEG Motor Movement/Imagery dataset (PhysioNet `eegmmidb`, Schalk 2004),
of the kind associated with EEGNet-class pipelines. Note: PhysioNet `eegmmidb`
and BCI Competition IV 2a (`BNCI2014_001`) are **different datasets** — this case
uses PhysioNet.

**Scope decision (honest).** The deep-net (EEGNet) baseline requires
TensorFlow/Keras + GPU and is **out of the current repository's scope**. The
BSFF-aligned, model-agnostic version of this attack uses the existing harness
(`research/bci_generalization/run_experiment.py`, CSP+LDA via MOABB) and the same
LOSO logic already demonstrated on `BNCI2014_001`. An EEGNet baseline is a
separate, GPU-bearing effort, not a blocker for the falsification itself.

## Attack steps (each emits an artifact + status)

| step | action | output | status |
|------|--------|--------|--------|
| 1 | reproduce baseline (within-session) | accuracy + `result.json` | PENDING (server-blocked: physionet.org time-out) |
| 2 | within-subject CV | per-subject accuracy | PENDING |
| 3 | session split | cross-session accuracy | PENDING |
| 4 | leave-one-subject-out (LOSO) | cross-subject accuracy + gap | PENDING |
| 5 | subject-disjoint split | confirm no subject leakage | PENDING |
| 6 | label shuffle (negative control) | accuracy → chance | PENDING |
| 7 | MIAAFT surrogate | does structure survive a linear-Gaussian null? | harness ready (`bsff adjudicate-data`) |
| 8 | leakage probes (channel drop / shuffle) | accuracy sensitivity | PENDING |
| 9 | global-normalization leak check | accuracy delta with/without leak | PENDING |
| 10 | verdict contract | `SURVIVED` / `REFUTED` / `UNSUPPORTED` + caveats | PENDING |

## Outputs (the receipt)
- `verdict.json` (disposition + provenance hash)
- `report.md` (`bsff render`)
- plots (within vs LOSO, confusion matrices)
- `MANIFEST.json` (data version, code commit, command hashes)
- hash-chained ledger (`bsff ledger-verify`)

## Kill criterion
LOSO accuracy near chance while within-subject is high → the global-validation
claim does not generalize. Documented with data version, code commit, exact
commands, and hashes.

## Current blocker (verified)
PhysioNet download times out in our environment (`physionet.org` read-timeout);
Zenodo mirrors (Zhou2016, AlexMI) likewise. The case runs unchanged in a network
with normal throughput. The method is already proven on `BNCI2014_001`
(`research/bci_generalization/result_bnci2014_001_sub1-2.json`).
