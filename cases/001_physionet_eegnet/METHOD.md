# BSFF-CASE-001 — Method

The harness (`run_case.py`) runs one decoder through a battery of split protocols and a
within-subject label-permutation null, then applies a fail-closed verdict rule.
Controls dominate; `SURVIVED` requires genuine cross-subject generalization; `REFUTED`
requires positive evidence of a generalization gap.

## Data

| mode | source | provenance |
|---|---|---|
| `synthetic` | labelled ground-truth generator (`synthetic_eeg.py`) | cohort sha256; ground truth fixed by construction |
| `physionet` | EEGMMI runs 4/8/12 (imagined L/R fist) via `mne.datasets.eegbci` | per-EDF byte sha256, portable relative keys |

Both modes emit `(n_trials, n_channels, n_times)` + per-trial subject id (and, for real
EEG, a `block` = run id), so the split code is identical. Trials are epoched to a 2.0 s
window (320 samples @ 160 Hz).

## Decoders

- `logvar_lda` (**primary**): 8–30 Hz band-pass → per-channel log-variance → LDA. The
  band-pass is computed **once** up front and the feature matrix is reused across every
  fold and permutation, so the permutation battery is fast and fully deterministic.
- `eegnet`: EEGNet (Lawhern et al. 2018) in PyTorch, CPU, seeded + deterministic. The
  *named* architecture; a secondary, exploratory corroboration.

The falsification is decoder-agnostic; the generalization gap is a property of the
evaluation protocol, not of one model.

## Probes & controls (pre-registered expectations)

1. **Within-subject CV** — K-fold *inside each subject*, pooled. On real EEG it is
   **leave-one-run-out** (GroupKFold over `block`), so run-level temporal
   autocorrelation does not leak into the baseline; synthetic falls back to stratified
   K-fold. *Expected: high.*
2. **Leave-one-subject-out (LOSO)** — train on N−1 subjects, test on the held-out
   subject. *Expected: collapses to chance iff the within-subject signal is
   subject-specific.*
3. **Generalization gap** = within − LOSO, **tested directly** (probe 4).
4. **Within-subject label-permutation null** (`permutation_battery`) — the inferential
   core. Each permutation shuffles labels *within subject* (respecting clustering) and
   recomputes within, LOSO and the gap, giving empirical p-values for all three. The
   gap is tested as one paired quantity, not two marginal tests joined by AND.
5. **Leak control** — the null-within mean must sit at chance. If labels-permuted
   within-CV still decodes above chance + margin, the evaluation leaks → verdict
   withheld.
6. **Monte-Carlo resolution** — the gap p-value must be > 2 Monte-Carlo SE from alpha,
   else the verdict is withheld pending more permutations.
7. **Seed-stability** (`--stability-seeds N`) — re-run across seeds; a verdict that
   flips with the RNG is downgraded fail-closed.
8. **Global-normalization leakage probe** — fit the scaler on train+test pooled vs
   train-only; report the LOSO inflation.

## Verdict rule (fail-closed)

```
if labels-permuted within-CV decodes above chance:    UNSUPPORTED  (evaluation leaks)
elif LOSO significantly above chance:                 SURVIVED     (generalizes)
elif within significant AND gap significant+resolved: REFUTED      (does not generalize)
elif within significant AND gap not significant:      UNSUPPORTED  (underpowered; cannot refute)
else:                                                 UNSUPPORTED  (no admissible signal)
```

No path emits `TRUE`. A non-significant LOSO is **never** sufficient for `REFUTED`. A
control failure can only demote toward `UNSUPPORTED`, never promote to `SURVIVED`.

## Ground-truth validation of the harness (synthetic presets)

| preset | construction | expected verdict |
|---|---|---|
| `headline` | subject-specific discriminability only | **REFUTED** |
| `shared` | a genuinely subject-shared pattern | **SURVIVED** |
| `null` | no structure | **UNSUPPORTED** |

These fix the ground truth so the harness is shown to be two-sided: it kills the
inflated claim, confirms a real signal when one exists, and stays silent on noise.

## Provenance

`artifact_sha256` is computed over **rounded** metrics so the digest is reproducible
across BLAS / library builds; per-EDF byte hashes bind the verdict to the exact data;
the dossier records a faithful, minimal reproduction command and a `--verify` recompute
command for independent digest checking.
