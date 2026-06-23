<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Reviewer packet — BSFF Bonn bright line

This packet lets an external reviewer verify, in minutes, exactly what is proven and
what is not. It is independent research software, not a clinical or regulatory artifact.

## What this is
A **fail-closed scientific validation** of whether BSFF's surrogate-test instrument has
a usable operating characteristic on real neural data, gated by two controls:

- **G1 (power):** Bonn Set E (ictal iEEG) must mostly **SURVIVED**, and healthy Sets
  A/B must mostly **not** survive.
- **G2 (specificity):** a spectrum-matched **AR (linear)** null must keep **FPR ≤ 0.05**.

`BRIGHT_LINE_PASSED = G1 ∧ G2`. The verdict is whatever the executed artifacts show —
a negative result is preserved as evidence, not hidden.

## Verify in 5 steps
1. Read the pre-declared protocol: `docs/validation/BONN_BRIGHT_LINE_PROTOCOL.md` and
   `docs/validation/STATISTIC_REGISTRY.md` (thresholds fixed BEFORE the confirmatory).
2. Read the machine verdict: `artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json`
   and `docs/validation/BRIGHT_LINE_VERDICT.md`.
3. Check data provenance + hashes: `artifacts/bonn_bright_line/DATASET_MANIFEST.json`
   (canonical Bonn from UPF NTSA; per-file SHA256; NOT the UCI 178 variant).
4. Re-run: follow `REPRODUCE.md` (one command per gate, deterministic seeds).
5. Run tests: `pytest -q tests/bonn_bright_line` (16 deterministic tests, no network).

## Method honesty (⊛)
SampEn measures **regularity**, and deterministic chaos is more regular than noise — so
low SampEn alone is not nonlinearity. The MIAAFT null preserves the linear spectrum, so
SampEn **below its own spectrum-matched surrogates** is nonlinear determinism; **G2** is
the decisive guard that this is not a linear-regularity confound. See STATISTIC_REGISTRY.md.

## Trust boundaries (forbidden claims)
Not clinical diagnosis · not medical use · not regulatory validation · not final proof of
brain nonlinear dynamics · not a universal BCI benchmark authority. This is a **seed for
BNCI preregistration / replication**, nothing more.

## Reviewer decision table

| Reviewer question | Answer |
|-------------------|--------|
| Can BSFF now proceed to BNCI2014-001? | **No.** G2 failed (combined AR-null FPR 0.065 > 0.05). |
| Did BSFF detect Bonn Set E? | **Yes.** G1 passed (Set E SURVIVED 0.96). |
| Is the statistic specific enough? | **No.** Combined AR-null FPR = 0.065 > alpha 0.05. |
| Is this a failed project? | **No.** It is a successful fail-closed negative validation result. |

**Inspect first:** `artifacts/bonn_bright_line/BRIGHT_LINE_SUMMARY.json`.
**Run first:** `python examples/bonn_bright_line/check_consistency.py`.
**What would change the verdict:** an S2 statistic (see `docs/validation/NEXT_METHOD_CONTRACT_S2.md`)
that holds G1 power **and** drives combined AR-null FPR ≤ 0.05 under the same pre-declared protocol.
**Must not be claimed:** clinical/medical/regulatory status, final brain-dynamics proof, universal BCI authority.
