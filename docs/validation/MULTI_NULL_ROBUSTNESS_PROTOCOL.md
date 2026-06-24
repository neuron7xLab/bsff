<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Multi-null-model robustness protocol (predeclared)

The choice of null model is a **researcher degree of freedom**. The bright line so far uses one
null family (spectrum-matched AR for G2, MIAAFT inside the statistic). A PI-grade specificity claim
must hold across **independent null models**, not just AR order.

## Predeclared null models (to run after S3, frozen)
1. **AR(p)** spectrum-matched (current).
2. **IAAFT** (iterative amplitude-adjusted Fourier transform) surrogates.
3. **Phase-randomized** (FT) surrogates.
4. **CAAFT** / cyclic-AAFT (optional).

## Gate (same as S3, applied per null model)
Pooled seed-averaged FPR Wilson 95% CI upper bound ≤ 0.05 **for every null model**. A specificity
claim is robust only if it survives all of them; failing any one ⇒ specificity is null-model-dependent
(not robust).

## Forbidden
Selecting the null model that passes; changing thresholds; post-hoc null choice. The null-model set
is frozen here before execution.
