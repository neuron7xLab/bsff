<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Bonn bright-line statistic registry

A pre-registered, append-only record of every nonlinearity statistic tried against
the Bonn positive control. Failed statistics are **preserved**, not deleted — a
negative result is evidence.

## S0 — `lagged_quadratic` (FAILED, preserved)

- statistic: `|corr(x[t]^2, x[t+1])|` (lag-1 quadratic coupling), BSFF default.
- null: MIAAFT; verdict via `evaluate_claim_pipeline` (corroborated instrument).
- **observed: Set E (ictal) SURVIVED ≈ 20%** (exploratory, n=10–30, standard policy).
- verdict: **insufficient power** — ictal nonlinearity is burst/determinism
  structure, not lag-1 quadratic coupling.
- status: **PRESERVED negative result.** Evidence:
  `artifacts/bonn_bright_line/bonn_bright_line_EXPLORATORY.json`,
  `examples/bonn_bright_line/run_bonn_bright_line.py`.

## S1 — `sampen_lower_tail_m2_r015_v1` (under test)

- statistic: Sample Entropy (Richman & Moorman 2000), `m=2`, `r=0.15·std`,
  `subsample=1024` (fixed before confirmatory).
- null: MIAAFT (preserves spectrum + marginals, destroys temporal determinism),
  convergence-gated (≥90% must converge or verdict = UNSUPPORTED).
- test direction: **lower tail** (`orig < surrogates` ⇒ more deterministic ⇒ reject ⇒ SURVIVED).
- alpha = 0.05; n_surrogates exploratory = 99; **n_surrogates confirmatory = 199**
  (999 is infeasible: MIAAFT on 4097-sample segments costs ~60 ms/surrogate, so
  999×500 segments ≈ hours; 199 gives p-resolution 0.005, adequate for alpha=0.05).
- rationale: `lagged_quadratic` tests quadratic coupling; Bonn ictal structure
  requires a regularity/complexity statistic. SampEn is a **candidate, not
  guaranteed** to pass.
- implementation: `examples/bonn_bright_line/statistics_sampen.py`.

### Exploratory (n=20, 99 surrogates) — observed, NOT the verdict

- G1: Set E SURVIVED 100%, Set B not-SURVIVED 100%, **Set A not-SURVIVED 75%**.
- G2: real-spectrum AR null FPR = 0.05.
- The confirmatory (below) is the verdict; thresholds are fixed here BEFORE it runs.

### Methodological caveat (⊛): SampEn measures REGULARITY, not nonlinearity directly

Sample Entropy is a regularity/complexity measure — and *deterministic chaos is more
regular than noise*. So a low SampEn alone does not prove nonlinearity: a strongly
autocorrelated **linear** signal (e.g. a narrowband oscillation) is also regular.

What makes the test valid is the **null**: MIAAFT preserves the power spectrum (hence
all *linear* regularity) while destroying phase/temporal determinism. A SampEn
**below its own spectrum-matched surrogates** is therefore excess regularity *not
explained by the linear spectrum* — i.e. nonlinear determinism. The decisive guard is
**G2**: a spectrum-matched **AR (linear)** null must NOT survive (FPR ≤ alpha). If G2
fails, the G1 "detection" is a regularity confound, not nonlinearity, and the bright
line does not pass.

This is also why the residual **Set A** survival (~25% at n=20) matters: healthy EEG
carries weak genuine structure plus finite-N MIAAFT bias, so the negative-sanity
threshold (≥ 0.80 not-survived) is the honest gate, fixed before the confirmatory.
