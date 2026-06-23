# Bonn bright line — BSFF real operating characteristic (G1 + G2)

Measure BSFF's **real** operating characteristic on real neural data *before* any
scientific claim. Two controls, one bright line:

- **G1 (power / positive control):** Bonn **Set E** (ictal iEEG, real nonlinearity)
  should mostly return **SURVIVED**; **Sets A/B** (healthy) should not.
- **G2 (specificity / negative control):** a spectrum-matched **AR** null built from
  the real Bonn spectra must yield **FPR ≤ alpha = 0.05** under the BSFF instrument.

`BRIGHT_LINE_PASSED = G1_PASS ∧ G1_NEGATIVE_SANITY ∧ G2_PASS`. No scientific success
is claimed unless **both** evidence bundles pass, produced by executed code.

## Data — canonical Andrzejak 2001 Bonn EEG (do NOT use the UCI 178-feature variant)

- Source: **UPF NTSA** `https://www.upf.edu/web/ntsa/downloads`
  (`epileptologie-bonn.de` is offline since 2024). DOI `10.1103/PhysRevE.64.061907`.
- The UPF document endpoint is **Cloudflare-gated**, so `curl`/`wget` receive an HTML
  challenge, not the zip. The canonical zips (`Z.zip`=A, `O.zip`=B, `S.zip`=E) were
  fetched once via an authenticated **browser** session and staged as
  `bonn_data/{E,A,B}/*.txt` (100 segments each, **4097** samples/segment — the UPF
  canonical export; 4096 is also documented in the literature).
- `bash download_bonn.sh ./bonn_data` verifies the staged data, or writes
  `FAIL_DOWNLOAD.json` and exits non-zero if it is absent (it never fabricates a
  download). Provenance + every file SHA256 are in
  `artifacts/bonn_bright_line/DATASET_MANIFEST.json`.

## Real-bug fixes applied to the candidate scripts

1. **Per-set glob** (`*.txt`): the candidate globbed only `Z*.txt`, so Set E
   (`S*.txt`) matched **zero** files.
2. **Accept 4096 or 4097** samples/segment.
3. **Verdict via the BSFF instrument** `evaluate_claim_pipeline` (with the policy's
   Bayesian corroboration), **not** the raw `rank_order_surrogate_test` intermediate.
   The raw test is anti-conservative on colored real spectra; the raw rejection is
   kept in the evidence for transparency but is not BSFF's verdict.

Note: `--policy strict` forces `surrogate_count = 999` (policy `max()` override), so
`--n-surrogates` is a lower bound under strict.

## Commands

```bash
# verify staged canonical data
bash download_bonn.sh ./bonn_data

# G1 exploratory / confirmatory
python run_bonn_bright_line.py --data-dir ./bonn_data --n-segments 10  --n-surrogates 99  --policy standard --output ../../artifacts/bonn_bright_line/bonn_bright_line_EXPLORATORY.json
python run_bonn_bright_line.py --data-dir ./bonn_data --n-segments 100 --n-surrogates 999 --policy strict   --output ../../artifacts/bonn_bright_line/bonn_bright_line_VERDICT.json

# G2 AR negative control (Set A and Set B separately)
python spectrum_matched_ar_control.py --input-dir ./bonn_data/A --n-segments 100 --ar-order 10 --n-surrogates 999 --policy strict --output ../../artifacts/controls/ar_negative_control_A_VERDICT.json
python spectrum_matched_ar_control.py --input-dir ./bonn_data/B --n-segments 100 --ar-order 10 --n-surrogates 999 --policy strict --output ../../artifacts/controls/ar_negative_control_B_VERDICT.json

# aggregate honest verdict
python aggregate_verdict.py   # -> BRIGHT_LINE_SUMMARY.json + BRIGHT_LINE_VERDICT.md
```

## Result (executed)

The exploratory run (committed, `standard`, n=10/20) returned:

- **G2 PASS** — instrument FPR = 0.050 ≤ 0.05 on the real-spectrum AR null (raw
  rank-order FPR = 0.10 is anti-conservative; the corroboration gate restores it).
- **G1 NOT met** — Set E (ictal) SURVIVED ≈ **20%** (≪ 80%); the `lagged_quadratic`
  statistic does **not** robustly detect Bonn ictal nonlinearity under the instrument.

The confirmatory verdict (n=100, strict) is in
`artifacts/bonn_bright_line/BRIGHT_LINE_VERDICT.md` / `BRIGHT_LINE_SUMMARY.json`.

**Interpretation:** specificity on real spectra is established (G2); **power on real
ictal nonlinearity is not** (G1), with this single-channel statistic. The bright line
is **not** crossed → the chain to BNCI2014-001 remains **blocked** until a stronger
nonlinearity statistic (e.g. nonlinear prediction error, time-reversal asymmetry,
correlation dimension) is added and re-validated against this same benchmark.

## Limitations

Not clinical. Not regulatory. Not final scientific proof. One benchmark (Bonn), one
statistic (`lagged_quadratic`), single-channel. A negative G1 is itself a valid,
publishable operating-characteristic result — it prevents a false scientific claim.
