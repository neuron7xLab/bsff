<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# LIMITATIONS_HARD

No softening. What BSFF v0.4.0 is **not**, and what is not yet proven.

1. **Not externally validated against TISEAN.** Surrogate fidelity is validated
   *intrinsically* (marginal exact, spectrum ≈1%, covariance ≈0). A byte-level
   comparison against the TISEAN reference C implementation has not been run.
   Status: `NEEDS_EXTERNAL_CHECK`.

2. **No real human EEG dataset is shipped.** The repository contains synthetic
   fixtures and a synthetic validation corpus only. Real EEG is downloaded at
   runtime via MOABB; none is committed. Any verdict on real data is the user's
   run, not a repository artifact.

3. **Not regulatory. Not clinical.** BSFF makes no medical, diagnostic, or
   regulatory claim and must not be used for one.

4. **Linear / spectral scope.** The signal engines are IAAFT/MIAAFT surrogates
   and linear (Gaussian) transfer entropy. Nonlinear directed coupling (e.g.
   k-NN transfer entropy) and non-time-series designs (two-group, cohort) are
   out of scope and would need their own calibrated tests before any claim that
   relies on them.

5. **The real LOSO result is minimal, not a benchmark conquest.** It is two
   subjects of one dataset (BNCI2014_001), within 0.807 → cross-subject 0.603,
   gap +0.204. It demonstrates the generalization gap is real and measurable; it
   does **not** establish a population-level claim about BCI. A second dataset
   was attempted and blocked by external server time-outs, not by the tool.

6. **It does not prove claims true.** The strongest disposition is *survived
   falsification under stated conditions*. BSFF refutes or fails to refute; it
   never confirms.

7. **The instrument can be wrong.** See `REVIEWER_PACKET.md` § "What would
   falsify BSFF itself" — the conditions under which BSFF's own verdicts should
   not be trusted.
