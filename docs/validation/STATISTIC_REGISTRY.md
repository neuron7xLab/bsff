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

### Confirmatory (n=100, 199 surrogates) — VERDICT

- **G1 PASS:** Set E SURVIVED **0.96** (≥0.80), Set A not-SURVIVED **0.86**, Set B **0.91**.
  SampEn solves the power gap that sank `lagged_quadratic` (20% → 96%).
- **G2 FAIL:** real-spectrum AR null FPR — Set **A = 0.08** (> 0.05), Set B = 0.05,
  combined = 0.065. The instrument is **anti-conservative on Set-A-like linear spectra**.
- **BRIGHT_LINE_NOT_PASSED** — power is sufficient, **specificity is not**. This is the
  regularity-confound the ⊛ caveat predicted: on some linear spectra the AR null is more
  regular than its own MIAAFT surrogates, so the lower-tail test fires. G2 caught it.
- status: **S1 power-validated, specificity-refuted.** Chain to BNCI2014-001 stays BLOCKED.

### Next statistic contract (S2, proposed — not yet run)

To pass G2 without losing G1 power, the lower-tail SampEn test needs calibrated
specificity. Candidate fixes, to be pre-registered before running:
1. **Two-sided / FDR-controlled** rank-order p with finite-N AAFT bias correction
   (Kugiumtzis 1999) — removes the lower-tail finite-N inflation that drives Set-A FPR.
2. **Corroboration gate** (JZS Bayes factor, as in the BSFF pipeline) on top of SampEn —
   demote uncorroborated rejections to UNSUPPORTED.
3. **Statistic ensemble** (SampEn ∧ time-reversal asymmetry) requiring agreement.
Acceptance: G1 E-SURVIVED ≥ 0.80 AND G2 combined FPR ≤ 0.05, same predeclared protocol.

## S2 candidate registry (specificity)

After S1 (`sampen_lower_tail_m2_r015_v1`) passed G1 but failed G2 (combined AR-null
FPR 0.065 > 0.05), the S2 phase registers candidates that target specificity without
losing G1 power. Frozen protocol: `S2_SPECIFICITY_PROTOCOL.md`. Implementations +
hypotheses + expected failure modes: `examples/bonn_bright_line/s2_candidate_registry.py`.

| id | statistic + rule | implemented |
|----|------------------|-------------|
| S2-C1-sampen-finiteN | SampEn + conservative α/2 threshold | yes |
| S2-C2-sampen-corroboration | SampEn + effect-size (z≥2) gate | yes |
| S2-C3-sampen-fdr | SampEn + Benjamini-Hochberg FDR | yes |
| S2-C4-sampen-strictconv | SampEn + strict MIAAFT convergence | yes |
| S2-C7-permen | Permutation entropy lower-tail | yes |
| S2-C5-rqa-det | Recurrence-quantification %DET | deferred |
| S2-C6-nlpe | Nonlinear prediction error | deferred |

Exploratory: `artifacts/bonn_bright_line/s2_EXPLORATORY_RESULTS.json`. Selection lock +
confirmatory verdict follow the same fail-closed pattern as S1.

### S2 confirmatory — VERDICT (executed)

- Frozen candidate **S2-C1-sampen-finiteN** (SampEn lower-tail with conservative p ≤ α/2 = 0.025).
- Confirmatory (n=100, 199 surrogates): G1 E=0.96, A_not=0.92, B_not=0.92 (all ≥0.80);
  G2 FPR_A=0.020, FPR_B=0.020, **combined=0.020 ≤ 0.05**.
- **S2_BRIGHT_LINE_PASSED = True** → chain to BNCI2014-001 **UNLOCKED**.
- Mechanism: the α/2 threshold corrects SampEn's finite-N anti-conservative bias (S1 nominal
  0.05 gave real FPR 0.08); strong ictal rejections (p≈0.005) survive the stricter threshold,
  so G1 power is preserved. A conservative-threshold variant, not a new statistic.
- Evidence: `s2_CONFIRMATORY_VERDICT.json`, `S2_BRIGHT_LINE_SUMMARY.json`, `docs/validation/S2_VERDICT.md`.
