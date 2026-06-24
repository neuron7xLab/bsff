<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# BNCI2014-001 preregistration — protocol

**Status:** preregistration scaffold. Unlocked by the S2 Bonn bright-line pass
(`docs/validation/S2_VERDICT.md`). **No BNCI data acquired or analysed yet** — this file
freezes the plan *before* any BNCI run, exactly as the Bonn protocol did.

## Why unlocked
The Bonn bright line is crossed (S1 G1 + S2 G2) with the finite-N-corrected SampEn
detector: power on real ictal EEG (E SURVIVED 0.96) and specificity on real-spectrum AR
nulls (combined FPR 0.020 ≤ 0.05). The instrument has a demonstrated operating
characteristic on a real neural benchmark — the precondition for adjudicating BNCI claims.

## Dataset
- **BNCI2014-001** (BCI Competition IV-2a): 9 subjects, 4 motor-imagery classes, 22 EEG +
  3 EOG channels, 250 Hz. Source: `bnci-horizon-2020.eu` (canonical). DOI to be cited in
  the manifest. Not the only mirror; a hash manifest is mandatory before use.
- Acquisition: documented download + per-file SHA256 → `artifacts/bnci2014_001/DATASET_MANIFEST.json`
  (to be created at execution time). Raw data gitignored.

## Instrument (frozen)
`sampen_lower_tail_m2_r015_v1` with the S2 finite-N rule (p ≤ α/2 = 0.025), MIAAFT null,
convergence-gated. Same code path as the Bonn confirmatory; no per-dataset retuning.

## Hypotheses (to be frozen with thresholds before any run)
- Positive control: epochs with known motor-imagery structure should exceed chance under a
  task-decoding metric (analysis plan).
- Specificity control: real-spectrum AR nulls per subject must keep FPR ≤ 0.05.

This protocol is intentionally incomplete on numeric thresholds until the analysis plan and
stop rules are frozen (see sibling files). No claim is made here.

## Preregistration lock
The confirmatory plan is frozen in [`BNCI2014_001_LOCK.json`](BNCI2014_001_LOCK.json)
(`status: PREREGISTRATION_LOCKED_NOT_EXECUTED`). No BNCI run has occurred; no BNCI claim exists
until the locked `artifact_paths` are produced under explicit authorization.
