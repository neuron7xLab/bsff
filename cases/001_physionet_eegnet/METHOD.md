# BSFF-CASE-001 — Method

The harness (`run_case.py`) runs one decoder through a battery of split protocols and
controls, each a pre-registered probe with an expected outcome. The verdict rule is
fail-closed: controls dominate, and `SURVIVED` requires genuine cross-subject
generalization.

## Data

| mode | source | provenance |
|---|---|---|
| `synthetic` | labelled ground-truth generator (`synthetic_eeg.py`) | cohort sha256; ground truth fixed by construction |
| `physionet` | EEGMMI runs 4/8/12 (imagined L/R fist) via `mne.datasets.eegbci` | per-EDF byte sha256 |

Both modes emit `(n_trials, n_channels, n_times)` + per-trial subject id, so the split
code is identical. Trials are epoched to a 2.0 s window (320 samples @ 160 Hz).

## Decoders

- `logvar_lda` (default): 8–30 Hz band-pass → per-channel log-variance → LDA. Fully
  deterministic, the canonical motor-imagery (ERD/ERS) feature. Workhorse engine.
- `eegnet`: EEGNet (Lawhern et al. 2018) in PyTorch, CPU, seeded + deterministic. The
  *named* architecture, so the loop closes on the real model, not a stand-in.

The falsification is decoder-agnostic; the generalization gap is a property of the
evaluation protocol, not of one model.

## Probes (pre-registered expectations)

1. **Within-subject CV** — stratified 5-fold *inside each subject*, pooled. The
   "global / within-validation" number. *Expected: high.*
2. **Leave-one-subject-out (LOSO)** — train on N−1 subjects, test on the held-out
   subject. The honest generalization test. *Expected: collapses to chance iff the
   within-subject signal is subject-specific.*
3. **Generalization gap** = within − LOSO. The headline falsification statistic.
4. **Label-shuffle control** — permute labels within subject, re-run within-subject CV.
   *Expected: chance.* If it stays high, the evaluation leaks → verdict withheld.
5. **LOSO permutation null** — shuffle labels within subject and recompute LOSO many
   times; `p = (#{null ≥ observed} + 1)/(n+1)`. The actual test for "does it
   generalize", not a raw threshold.
6. **Global-normalization leakage probe** — fit the feature scaler on train+test
   pooled vs train-only; report the LOSO inflation. A concrete leak made visible.

## Verdict rule (fail-closed)

```
if shuffled labels decode above chance within subject:   UNSUPPORTED  (evaluation leaks)
elif within significant AND LOSO not significant:         REFUTED      (no generalization)
elif LOSO significant:                                    SURVIVED     (generalizes)
else:                                                     UNSUPPORTED  (no admissible signal)
```

No path emits `TRUE`. A control failure can only demote toward `UNSUPPORTED`, never
promote to `SURVIVED`.

## Ground-truth validation of the harness (synthetic presets)

| preset | construction | expected verdict |
|---|---|---|
| `headline` | subject-specific discriminability only | **REFUTED** |
| `shared` | a genuinely subject-shared pattern | **SURVIVED** |
| `null` | no structure | **UNSUPPORTED** |

These three fix the ground truth so the harness is shown to be two-sided: it kills the
inflated claim, confirms a real signal when one exists, and stays silent on noise.
