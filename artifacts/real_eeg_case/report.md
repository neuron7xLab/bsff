# BSFF real-EEG (synthetic-fixture) case report

> **HONESTY:** the shipped dataset is a SYNTHETIC, EEG-shaped fixture
> (deterministic Henon-map traces), NOT a real human recording. See
> `docs/REAL_EEG_VALIDATION.md` to substitute a real OpenNeuro/BIDS dataset.

## Primary verdict (valid-signal path)

- claim_id: `bids-sub-01-task-rest`
- verdict: **SURVIVED**
- p_value: 0.05
- data sha256: `5fc54436eb9e50a840e4ed5278f4e95449e8edf1331e9e940d116dd2337684d3`

## Four expected-verdict demonstrations

1. valid-signal path -> **SURVIVED** (real engine)
2. feature-table -> **REFUSED** by `no_feature_table_leakage` (real ingestion guard)
3. label-leakage -> **REFUTED** (real engine leakage short-circuit)
4. nonstationarity -> **REFUTED** with KPSS stationarity caveat (real gate)

## Caveats (primary verdict)

- Low surrogate count: suitable for CI smoke, not final evidence.
