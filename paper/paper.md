---
title: 'BSFF: A falsification framework for neural signal claims'
tags:
  - Python
  - brain-computer interface
  - electroencephalography
  - surrogate data
  - falsification
  - reproducibility
authors:
  # NOTE before JOSS submission: replace the placeholder ORCID with a real one.
  - name: Yaroslav Vasylenko
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: neuron7xLab, Independent Research
    index: 1
date: 21 June 2026
bibliography: references.bib
---

# Summary

`BSFF` is a deterministic Python framework for surrogate-based stress testing of
claims made about neural signals — for example, that an electroencephalography
(EEG) or brain-computer interface (BCI) recording encodes an intention, a class
label, or nonlinear temporal structure. Given a machine-readable claim contract
and a signal, `BSFF` runs a fixed pipeline of falsification stages (stationarity
gating, data-leakage detection, a multivariate surrogate attack, and an optional
Bayesian effect-size check) and returns a single machine-readable verdict:
`SURVIVED`, `REFUTED`, or `UNSUPPORTED`. The framework treats `UNSUPPORTED` as a
first-class outcome, separating "the data positively support the null" from "the
test lacked the power to decide" — a distinction that is often collapsed in
applied reporting. The intended use is leakage-aware claim adjudication during
secondary analysis and method auditing, not production decoding.

# Statement of need

Surrogate-data methodology for testing nonlinearity in time series is well
established [@theiler1992; @schreiber2000], and the amplitude-adjusted
Fourier-transform construction, its iterative refinement [@schreiber1996], and
the multivariate common-phase extension [@prichard1994] are standard null
models. Separately, the neuroimaging and decoding literature documents how
results inflate when an analysis double-dips on the data used to select features
or a model [@kriegeskorte2009; @varoquaux2017]. What is usually missing is not
the statistics but the harness: a reproducible, contract-driven pipeline that
applies these tests uniformly across claims, records provenance, and refuses to
overstate its own conclusions.

`BSFF` provides that harness. It composes:

- a stationarity gate based on the KPSS test [@kwiatkowski1992], surfaced as a
  caveat rather than silently passed;
- leakage detectors for block-design and feature-selection contamination,
  addressing the circular-analysis failure modes described in
  [@kriegeskorte2009; @varoquaux2017];
- a multivariate iterative amplitude-adjusted Fourier-transform (MIAAFT)
  surrogate engine with a common-phase projection and an explicit, monitored
  convergence criterion, plus a covariance-preserving variance-phase fallback
  for high-dimensional, finite-sample regimes;
- a rank-order surrogate test and an optional Jeffreys–Zellner–Siow Bayes factor
  [@rouder2009; @kass1995], used only to distinguish `REFUTED` from
  `UNSUPPORTED`.

Every run emits a machine-readable verdict with the surrogate distribution,
p-value, and caveats, enabling downstream auditing. The package ships with a
deterministic synthetic validation corpus, SPDX and provenance metadata, and a
documented falsification protocol.

# Method

The MIAAFT engine preserves each channel's amplitude spectrum and the
inter-channel phase relationships while randomizing the common phase, then
rank-matches each channel to its empirical marginal. Convergence is defined as a
plateau in mean absolute spectral error below a tolerance and is reported in the
diagnostics (`converged`, `n_iter_actual`), so a non-converged surrogate is
never silently treated as valid. When the rank projection cannot jointly satisfy
all marginal and cross-spectral constraints — typical for many channels and
short records — the variance-phase fallback preserves the lag-0 covariance by
whitening, phase-randomizing, and recoloring through a Cholesky factor. Over an
ensemble, the mean surrogate covariance converges to the original covariance,
which the test suite verifies against a closed-form reference rather than an
external binary.

# Validation

The operating characteristic of the shipped decision rule is measured against
labelled synthetic generators with known ground truth and committed to the
repository (`artifacts/operating_characteristic.json`); a reduced battery is
recomputed on every continuous-integration run. The battery comprises two
generators with genuine nonlinear structure (deterministic Hénon-map and
logistic-map chaos, which should survive a linear-Gaussian surrogate null) and
three linear-Gaussian generators that should not survive (autocorrelated AR(1)
processes at two coefficients, and IID white noise). Figure 1 reports the
per-class survival rate under the frequentist rank-order rule and under the
shipped conjunction rule that additionally requires a corroborating effect-size
Bayes factor.

![Operating characteristic on labelled synthetic classes (alpha = 0.05, 99
surrogates, 60 seeds). The `henon` and `logistic` classes are power targets; the
`ar1_phi*` and `white` classes are false-positive-rate targets. Error bars on
the conjunction bars are the 95% confidence interval from the committed
artifact.](figures/operating_characteristic.png)

Power on both nonlinear classes is 1.000. The frequentist rank-order test is
anti-conservative on strongly autocorrelated linear-Gaussian processes — a
documented surrogate-fidelity bias rather than a coding defect [@kugiumtzis2002]
— so its false-positive rate on `ar1_phi0.75` exceeds the nominal level. The
conjunction rule restores the per-class false-positive rate to at or below the
nominal level on every null class while leaving power unchanged.

# Limitations

This is an instrument calibration of a statistical test on synthetic fixtures
with known ground truth. It is not a validation against an external surrogate
implementation, and it is not evidence about any specific neural recording. The
shipped corroboration gate is fail-closed: it can only demote a `SURVIVED`
verdict to `UNSUPPORTED`, never the reverse, and it is inert unless Bayesian
evidence is enabled. `BSFF` adjudicates a claim against a configured null; it
does not certify that a decoding model is correct, clinically usable, or
regulatory-compliant. A `SURVIVED` verdict means a claim was not refuted by the
configured battery, not that it is true.

# Reproducibility

`BSFF` outputs are deterministic for fixed seeds. The full operating
characteristic is regenerated with
`python tools/calibrate_operating_characteristic.py`, and Figure 1 is rendered
deterministically from the committed artifact with
`python paper/figures/generate_figures.py`. Each public claim is expected to
carry its claim contract, the command used, the package version, the validation
artifact JSON, that artifact's SHA-256, and the caveats it disclosed. The
package is tested with `pytest`, type-checked, and linted; continuous
integration runs on Python 3.10–3.12, and all randomized components are seeded.

# Acknowledgements

This work was carried out independently at neuron7xLab. No external funding
supported its development.

# References
