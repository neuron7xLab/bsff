<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Reproduce the Bonn bright-line verdict

An external reviewer can clone the repo, acquire the canonical data, run the controls,
and obtain the same G1/G2 verdict. Nothing here is clinical, diagnostic, or final
scientific proof.

## 1. Environment

```bash
python -m venv .venv && . .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,stats]"   # scipy KDTree is used by SampEn
bsff selftest
```

## 2. Acquire canonical Bonn data (do NOT use the UCI 178 variant)

Source: **UPF NTSA** `https://www.upf.edu/web/ntsa/downloads` (DOI 10.1103/PhysRevE.64.061907).
The document endpoint is Cloudflare-gated, so fetch the zips once via a browser and
stage them; then verify:

```bash
# stage Z.zip->A, O.zip->B, S.zip->E as examples/bonn_bright_line/bonn_data/{A,B,E}/*.txt
bash examples/bonn_bright_line/download_bonn.sh examples/bonn_bright_line/bonn_data
# -> verifies 100 segments/set, 4096|4097 samples, or writes FAIL_DOWNLOAD.json
```

Provenance + per-file SHA256: `artifacts/bonn_bright_line/DATASET_MANIFEST.json`.

## 3a. Reproduce the S1 negative artifact (historical: NOT_PASSED)

```bash
cd examples/bonn_bright_line
# G1 — Bonn positive control (Sample-Entropy lower-tail, nominal alpha=0.05)
python run.py --data-dir ./bonn_data --sets A B E --n-segments 100 --n-surrogates 199 \
  --output ../../artifacts/bonn_bright_line/bonn_CONFIRMATORY_VERDICT.json
# G2 — real-spectrum AR negative control (same instrument), per set
python run_ar_negative.py --input-dir ./bonn_data/A --n-segments 100 --n-surrogates 199 \
  --output ../../artifacts/controls/ar_negative_CONFIRMATORY_A.json
python run_ar_negative.py --input-dir ./bonn_data/B --n-segments 100 --n-surrogates 199 \
  --output ../../artifacts/controls/ar_negative_CONFIRMATORY_B.json
python aggregate_verdict.py
python check_consistency.py --output ../../artifacts/release/CONSISTENCY_CHECK.json
python release_check.py --root ../.. --output artifacts/release/RELEASE_CHECK.json
```

Expected S1 final state: `BRIGHT_LINE_NOT_PASSED` (G1 pass, G2 fail — combined AR-null FPR 0.065).
Preserved as the historical negative result.

## 3b. Reproduce the S2 PASS artifact (current canonical: PASSED)

```bash
cd examples/bonn_bright_line
python s2_evaluate_candidates.py --data-dir ./bonn_data --n-segments 30 --n-surrogates 199 \
  --output ../../artifacts/bonn_bright_line/s2_EXPLORATORY_RESULTS.json
python s2_select_candidate.py          # freezes ONE candidate before confirmatory
python s2_confirmatory.py --data-dir ./bonn_data --n-segments 100 --n-surrogates 199 \
  --output ../../artifacts/bonn_bright_line/s2_CONFIRMATORY_VERDICT.json
python s2_aggregate.py                 # -> S2_BRIGHT_LINE_SUMMARY.json + docs/validation/S2_VERDICT.md
cd ../.. && python tools/generate_current_truth.py
```

**Expected current canonical final state: `S2_BRIGHT_LINE_PASSED`** (G1 pass, G2 pass —
combined AR-null FPR 0.02). Runtime: each confirmatory ≈ 30–100 min (199 surrogates).

Verify hashes + truth coherence:

```bash
cd "$(git rev-parse --show-toplevel)"
sha256sum -c artifacts/release/bonn_bright_line/HASHES.sha256
python tools/validate_current_truth.py     # docs must agree with CURRENT_TRUTH.json
```

Canonical truth: `artifacts/release/CURRENT_TRUTH.json`
(`latest_validation_state = BONN_S2_BRIGHT_LINE_PASSED`). A non-zero exit on any gate means
the state is unmet — read the summaries, do not assume PASS.

## 4. Tests

```bash
python -m pytest -q tests/bonn_bright_line
```

## Notes
- Deterministic seeds (`SEED_BASE=20260623` G1, `20260624` G2); no Python hash() randomization.
- Pre-declared thresholds (E SURVIVED ≥ 0.80, A/B not-SURVIVED ≥ 0.80, G2 FPR ≤ 0.05,
  alpha = 0.05) are fixed in `docs/validation/BONN_BRIGHT_LINE_PROTOCOL.md` and not changed
  after the confirmatory.
- `n_surrogates=199` (not 999): MIAAFT on 4097-sample segments costs ~60 ms/surrogate, so
  999 × 500 segments is hours-infeasible; 199 gives p-resolution 0.005, adequate for alpha=0.05.
- The failed `lagged_quadratic` statistic (~20% Set-E power) is preserved in
  `docs/validation/STATISTIC_REGISTRY.md` as a negative result.
