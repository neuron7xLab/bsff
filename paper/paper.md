---
title: 'BSFF: A Falsification-First Framework for BCI/EEG Signal Claims'
tags:
  - Python
  - brain-computer interface
  - electroencephalography
  - surrogate data
  - falsification
  - reproducibility
authors:
  # NOTE before JOSS submission: add a real ORCID for the corresponding author.
  - name: Yaroslav Vasylenko
    affiliation: 1
affiliations:
  - name: neuron7xLab, Independent Research
    index: 1
date: 19 June 2026
bibliography: paper.bib
---

# Summary

`BSFF` (BCI Signal Falsification Framework) is a deterministic Python kernel that
stress-tests claims made about neural signals — that a recording encodes an
intention, a class label, or a nonlinear structure — before those claims are
trusted. Given a machine-readable claim contract and a signal, `BSFF` runs a
fixed pipeline of falsification stages (stationarity gating, data-leakage
detection, multivariate surrogate attack, and Bayesian evidence) and returns a
single machine-readable verdict: `SURVIVED`, `REFUTED`, or `UNSUPPORTED`. The
framework treats `UNSUPPORTED` as a first-class outcome, separating "the data
positively support the null" from "the test lacked the power to decide" — a
distinction routinely collapsed in applied BCI reporting.

# Statement of need

Claims of decoding intention, emotion, or cognitive state from EEG/BCI signals
are published and demonstrated continuously, yet many collapse to chance once a
single leakage path, temporal artifact, global-normalization leak, or
non-stationarity assumption is removed. The surrogate-data methodology for
testing nonlinearity is well established [@theiler1992; @schreiber2000], and the
amplitude-adjusted Fourier-transform (AAFT/IAAFT) construction and its
multivariate common-phase extension are standard null models
[@prichard1994]. What is usually missing is not the statistics but the
*plumbing*: a reproducible, contract-driven harness that applies these tests
uniformly, records provenance, and refuses to overstate its own conclusions.

`BSFF` provides that harness. It composes:

- a stationarity gate based on the KPSS test [@kwiatkowski1992], surfaced as a
  caveat rather than silently passed;
- leakage detectors for block-design and feature-selection contamination;
- a multivariate MIAAFT (multivariate iterative AAFT) surrogate engine with a
  common-phase projection and an explicit, monitored convergence criterion, plus
  a covariance-preserving variance-phase fallback for high-dimensional,
  finite-sample regimes;
- a rank-order surrogate test and an optional Jeffreys–Zellner–Siow Bayes factor
  [@rouder2009; @kass1995] used only to distinguish `REFUTED` from `UNSUPPORTED`.

Every run emits a machine-readable verdict with the surrogate distribution,
p-value, and caveats, enabling downstream auditing. The package ships with a
deterministic synthetic validation corpus, full SPDX/provenance metadata, and a
falsification protocol, targeting reproducible secondary analysis and method
auditing rather than production decoding.

# Method

The MIAAFT engine preserves each channel's amplitude spectrum and the
inter-channel phase relationships while randomizing the common phase, then
rank-matches to each channel's empirical marginal. Convergence is defined as a
plateau in mean absolute spectral error below a tolerance and is reported in the
diagnostics (`converged`, `n_iter_actual`), so a non-converged surrogate is
never silently treated as valid. When the rank projection cannot jointly satisfy
all marginal and cross-spectral constraints — typical for many channels and
short records — the variance-phase fallback preserves the lag-0 covariance by
whitening, phase-randomizing, and recoloring through a Cholesky factor. Over an
ensemble, the mean surrogate covariance converges to the original covariance to
within a fraction of a percent, which the test suite verifies against a
closed-form reference instead of an external binary.

# Quality control

`BSFF` is tested with `pytest`, type-checked, and linted; the public CI runs on
Python 3.10–3.12. Verdict logic, surrogate convergence, covariance fidelity, and
the three-way verdict trichotomy are each pinned by deterministic tests. A
performance matrix (4–32 channels, 512–8192 samples) is published as measured
wall-clock rather than asserted, and all randomized components are seeded.

# References
