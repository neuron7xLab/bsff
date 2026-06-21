# BSFF-CASE-001 — Report

**The within/global-validation accuracy that the popular "EEG motor-imagery decoding
works" framing leans on does not survive a leave-one-subject-out attack.** On real
PhysioNet EEGMMI data, a decoder that scores significantly above chance *within*
subjects shows a **statistically significant generalization gap** — it drops to chance
on a held-out subject — and the controls confirm the collapse is real, not an artefact
of the test.

Verdict: **REFUTED** (hash-bound; `artifacts/case001_real/VERDICT.json`).

This verdict rests on **positive evidence**: a paired within-subject permutation test
of the gap `within − LOSO`, not on the weaker "LOSO happens to be non-significant".

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
`logvar_lda` (8–30 Hz log-variance + LDA), **block-aware (leave-one-run-out)**
within-subject CV, 500-permutation within-subject label-permutation null. 405 trials,
9 subjects, **27 EDF files byte-hashed** into the dossier.

| metric | value | reading |
|---|---|---|
| within-subject CV accuracy | **0.605** | above chance (permutation p = 0.002) |
| leave-one-subject-out accuracy | **0.454** | sits in its null (mean 0.499) |
| **generalization gap (within − LOSO)** | **0.151** | **paired-permutation p = 0.002 (resolved)** |
| LOSO permutation p | 0.99 | fails to reject the no-generalization null |
| null-within mean (leak control) | 0.495 | clean — the evaluation does not leak |
| global-normalization LOSO inflation | ~0 | no normalization leak in this pipeline |

The within-subject signal is real (p = 0.002), and the **gap is itself significant**
(p = 0.002): the within accuracy does not transfer leave-one-subject-out. LOSO sits in
its permutation null. The leak control passes, so the verdict is admissible.

**Honest scope:** this falsifies the *generalization inference*, not the within-subject
result, and is not a claim that motor imagery is undecodable. The `logvar_lda` decoder
is the pre-registered primary; the collapse is a property of the evaluation protocol,
corroborable on the named architecture via `--decoder eegnet`. A stronger decoder with
a higher within-subject number only widens the gap, because LOSO is bounded by how much
of the signal is genuinely subject-shared, not by decoder capacity.

## 3. Why this is trustworthy — the harness is two-sided

A falsifier that only ever says "REFUTED" is worthless. On labelled synthetic ground
truth where the answer is fixed by construction (`METHOD.md`), the same harness returns:

| preset | construction | verdict |
|---|---|---|
| `headline` | subject-specific discriminability only | **REFUTED** (within 1.000, gap p ≈ 0.002) |
| `shared` | a genuinely subject-shared pattern | **SURVIVED** (LOSO above chance, p ≈ 0.005) |
| `null` | no structure | **UNSUPPORTED** (nothing decodes) |

It kills the trap, confirms a real cross-subject signal when one exists, and stays
silent on noise. The committed synthetic dossier (`VERDICT.json`, REFUTED) is the
in-repo, CI-checked reference; its digest is verifiable with `--verify`.

## 4. Inferential discipline (what makes this honest)

- **The gap is tested directly.** REFUTED requires a *significantly positive*
  `within − LOSO` under a within-subject label-permutation null — not the fallacy
  "LOSO is not significant, therefore it does not generalize" (absence of evidence is
  not evidence of absence). A within-significant but gap-non-significant result returns
  `UNSUPPORTED` (likely underpowered), never `REFUTED`.
- **The null respects clustering.** Permuting labels *within subject* (not a pooled
  binomial over non-independent trials) keeps the test from being anti-conservative —
  the exact statistical sin the case exists to expose.
- **Block-aware within-subject split.** On real EEG, within-subject CV is
  leave-one-run-out, so run-level temporal autocorrelation does not inflate the
  baseline the gap is measured against.
- **Monte-Carlo resolution.** If the gap p-value is within 2 Monte-Carlo SE of alpha,
  the verdict is withheld until more permutations resolve it — no verdict is decided by
  permutation noise.
- **Leak control.** If labels-permuted within-CV still decodes above chance, the
  evaluation leaks and the verdict is withheld (`UNSUPPORTED`), never `SURVIVED`.
- **Seed-stability.** `--stability-seeds N` re-runs the verdict across seeds; a verdict
  that flips with the RNG is downgraded fail-closed.

## 5. Reproduce & verify

```bash
# Synthetic ground-truth (offline, deterministic):
PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
    --source synthetic --config headline --permutations 500 --out /tmp/case001

# Real PhysioNet (needs network + the optional mne extra):
PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
    --source physionet --subjects 1-9 --decoder logvar_lda \
    --permutations 500 --out artifacts/case001_real

# Verify a committed dossier's digest (no science recompute):
PYTHONPATH=src python cases/001_physionet_eegnet/run_case.py \
    --verify cases/001_physionet_eegnet/VERDICT.json
```

`artifact_sha256` is computed over rounded metrics so it is reproducible across BLAS /
library builds; per-EDF byte hashes bind the verdict to the exact data.

## 6. What would overturn this

A decoder that scores significantly above chance *leave-one-subject-out* on EEGMMI,
with the leak control passing, would move the verdict to `SURVIVED`. That is the bar.
This case does not claim it is unreachable — it records that the commonly cited
within-subject number, by itself, does not clear it, and that the gap is significant.
