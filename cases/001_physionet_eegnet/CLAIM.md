# BSFF-CASE-001 — Claim

## Target

**Dataset:** PhysioNet EEG Motor Movement/Imagery Database (EEGMMI, `eegmmidb` 1.0.0),
Schalk et al., 2004 — 109 subjects, 64-channel EEG at 160 Hz.

**Model family:** EEGNet (Lawhern et al., 2018) and CSP-style log-variance decoders —
the architectures the popular "EEG motor-imagery decoding works" framing is built on.

## Claim under test

> Motor-imagery EEG decoders robustly decode left-vs-right-fist intention on PhysioNet
> EEGMMI; the reported within-subject / global-validation accuracy reflects
> **generalizable** decoding of the neural intention.

This is the operative, repeatedly-cited form: many tutorials, benchmark tables and
blog reproductions report high accuracy from a within-subject or pooled random split
and present it as evidence that the *signal* — the decodable motor-imagery intention —
is being captured.

## Falsifiable reduction

The claim is empirical-statistical and operationalizable, so BSFF can attack it
directly. We reduce it to a measurable statement:

> If the high within-subject accuracy reflects generalizable neural decoding, then a
> decoder trained on a set of subjects must decode a **held-out** subject above chance
> (leave-one-subject-out, LOSO).

**Pre-registered falsification criterion:**

- The claim is **REFUTED** if within-subject accuracy is significantly above chance
  while LOSO accuracy is **not** significantly above chance (permutation null).
- The claim **SURVIVES** only if LOSO accuracy is significantly above chance.
- The verdict is **UNSUPPORTED** if the credibility controls fail (e.g. shuffled
  labels remain decodable within subject → the evaluation itself leaks) or if no
  signal is admissible.

Chance = 0.5 (balanced binary). α = 0.05.

## What this case is NOT

- It is **not** a claim that EEG motor imagery is undecodable. Within-subject decoding
  of EEGMMI is real and reproducible. The case attacks the *generalization* inference
  drawn from within-subject numbers, not the within-subject number itself.
- It is **not** regulatory or clinical validation.
- The synthetic-mode result is a ground-truth demonstration that the harness is
  two-sided; it is **not** real EEG. The real verdict is the `physionet`-source run,
  bound to per-EDF byte hashes.
