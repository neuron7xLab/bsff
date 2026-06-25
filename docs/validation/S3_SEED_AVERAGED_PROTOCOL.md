<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# S3 seed-averaged bright-line protocol (frozen before run)

The S2 falsification showed G2 specificity is seed-sensitive (seed-avg FPR 0.035, Wilson 95% CI
[0.022, 0.056] crossing 0.05). S3 re-runs the bright line with a **robust, seed-averaged** gate.

## Frozen gate (no tuning after results)
- **G1 (power):** seed-averaged Set-E SURVIVED fraction ≥ 0.80.
- **G2 (specificity):** pooled AR-null FPR (Sets A+B) over all seeds, with a Wilson 95% CI.
  PASS requires the **CI upper bound ≤ 0.05** (stricter than a point estimate — the failure mode
  the falsification exposed).
- Statistic: `sampen_lower_tail_m2_r015_v1`, p ≤ α/2 = 0.025, MIAAFT null, **unchanged**.
- K = 10 seeds (fixed list), N = 50 segments/set, n_surrogates = 199. α = 0.05 fixed.

## Allowed terminal states
`S3_BRIGHT_LINE_ROBUSTLY_PASSED` · `S3_BRIGHT_LINE_NOT_ROBUSTLY_PASSED`.

## Forbidden
Changing α/thresholds/statistic after results; dropping seeds; selecting a favorable seed.
Runner: `examples/bonn_bright_line/s3_seed_averaged_confirmatory.py`. Lock:
`artifacts/bonn_bright_line/S3_PROTOCOL_LOCK.json`.
