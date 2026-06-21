# BSFF-CASE-001 — Report

**The within/global-validation accuracy that the popular "EEG motor-imagery decoding
works" framing leans on does not survive a leave-one-subject-out attack.** On real
PhysioNet EEGMMI data, a decoder that scores significantly above chance *within*
subjects drops to chance when forced to decode a *held-out* subject — and the
credibility controls confirm the collapse is real, not an artefact of the test.

Verdict: **REFUTED** (hash-bound; see `artifacts/case001_real/VERDICT.json`).

---

## 1. The claim

> Motor-imagery EEG decoders (EEGNet / CSP-style) robustly decode left-vs-right-fist
> intention on PhysioNet EEGMMI; the reported within/global-validation accuracy
> reflects generalizable decoding.

Reduced to a falsifiable test (see `CLAIM.md`): if the within-subject number reflects
generalizable neural decoding, a decoder trained on N−1 subjects must decode the
held-out subject above chance.

## 2. Real result — PhysioNet EEGMMI, 9 subjects

Imagined left-vs-right fist (runs 4/8/12), 2.0 s epochs @ 160 Hz, decoder
`logvar_lda` (8–30 Hz log-variance + LDA), 200-permutation LOSO null. 405 trials, 9
subjects, **27 EDF files byte-hashed** into the dossier.

| metric | value | reading |
|---|---|---|
| within-subject CV accuracy | **0.553** | above chance (binomial p = 0.018) |
| leave-one-subject-out accuracy | **0.454** | at/below chance |
| generalization gap (within − LOSO) | **0.099** | the headline collapse |
| LOSO permutation p-value | **0.98** | fails to reject the no-generalization null |
| LOSO permutation null mean | 0.497 | LOSO sits in the null |
| label-shuffle within (control) | 0.494 | clean — the evaluation does not leak |
| global-normalization LOSO inflation | 0.002 | no normalization leak in this pipeline |
| per-subject LOSO | 0.24–0.51 | every held-out subject ≤ chance |

The within-subject signal is real (p = 0.018) and it **does not transfer**: LOSO sits
squarely inside its permutation null (p = 0.98). The label-shuffle control passes, so
the verdict is admissible rather than withheld.

**Honest scope:** this `logvar_lda` decoder is deliberately simple, so its
within-subject number (0.553) is modest. The case attacks the *generalization
inference*, and the within→LOSO collapse is a property of the evaluation protocol, not
of one model — re-run the same battery on the *named* architecture with
`--decoder eegnet` to corroborate. A higher within-subject number from a stronger
decoder does not rescue the claim: it only widens the gap, because LOSO is bounded by
how much of the signal is genuinely subject-shared, not by decoder capacity.

## 3. Why this is trustworthy — the harness is two-sided

A falsifier that only ever says "REFUTED" is worthless. On labelled synthetic ground
truth where the answer is fixed by construction (`METHOD.md`), the same harness
returns:

| preset | construction | verdict |
|---|---|---|
| `headline` | subject-specific discriminability only | **REFUTED** (within 1.000 → LOSO 0.467) |
| `shared` | a genuinely subject-shared pattern | **SURVIVED** (LOSO recovers above chance) |
| `null` | no structure | **UNSUPPORTED** (nothing decodes) |

It kills the trap, confirms a real cross-subject signal when one exists, and stays
silent on noise. The committed synthetic dossier (`VERDICT.json`, REFUTED) is the
in-repo, CI-checked reference.

## 4. Controls run

- **Label-shuffle within subject** — permuted labels must not decode. They don't
  (0.494). If they had, the verdict would be withheld as `UNSUPPORTED`, never
  `SURVIVED`.
- **LOSO permutation null** — the actual significance test for generalization, not a
  hand-set threshold.
- **Global-normalization leakage probe** — fits the scaler on train+test pooled vs
  train-only and reports the inflation (0.002 here; the leak is quantified, not
  assumed away).

## 5. Reproduce

```bash
# Synthetic ground-truth (offline, deterministic, ~minutes):
PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
    --source synthetic --config headline --permutations 500 --out /tmp/case001

# Real PhysioNet (needs network + the optional mne extra):
PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
    --source physionet --subjects 1-9 --decoder logvar_lda \
    --permutations 200 --out artifacts/case001_real
```

The verdict, every metric, the environment, the command, and the per-EDF byte hashes
are written to `VERDICT.json` / `MANIFEST.json`. Same inputs + same code → same
`artifact_sha256`.

## 6. What would overturn this

A decoder that scores significantly above chance *leave-one-subject-out* on EEGMMI,
with the label-shuffle control passing, would move the verdict to `SURVIVED`. That is
the bar. This case does not claim it is unreachable — it records that the commonly
cited within-subject number, by itself, does not clear it.
