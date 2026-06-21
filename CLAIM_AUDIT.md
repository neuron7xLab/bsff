<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# CLAIM_AUDIT

Every load-bearing claim about BSFF, with the evidence file, the command that
checks it, the value/hash, and a status. No claim without a check; anything not
provable here is marked `UNPROVEN` or `NEEDS_EXTERNAL_CHECK`.

Status legend: **VERIFIED** (reproduced here) · **UNPROVEN** (asserted, not
established at the stated scope) · **NEEDS_EXTERNAL_CHECK** (requires a resource
not available in this environment) · **FALSE** (checked and wrong).

## Governing rule (status coupling)

**A claim's status is bounded by the weakest status it depends on.** A row may
not be `VERIFIED` if it rests on a `NEEDS_EXTERNAL_CHECK` or `UNPROVEN` premise.
A hash of a file proves the file's *identity*, never the *validity* of what the
file asserts. This rule was added after an external reviewer correctly found
three coupling defects in the first version of this audit:

1. **SLSA "VERIFIED" rested on a file-hash** (identity) while signature + digest
   cross-check are `NEEDS_EXTERNAL_CHECK` — split into 3a/3b/3c/4/4b/4c below.
2. **Surrogate fidelity "VERIFIED" omitted that the thresholds are smoke/
   engineering-grade** (`docs/REPRODUCIBILITY.md`) and external (TISEAN)
   validation is open — split into 11a/11b/11c.
3. **The n=2 LOSO result was shown as a "result" in `PUBLIC_SHOWCASE.md`** while
   the general claim is `UNPROVEN` here — showcase now carries the n=2 caveat.

| # | Claim | Evidence | Command | Value / hash | Status |
|---|-------|----------|---------|--------------|--------|
| 1 | 22 PRs #21–#42 merged | GitHub | `gh pr list --repo neuron7xLab/bsff --state merged --json number --jq '[.[].number]\|map(select(.>=21 and .<=42))\|length'` | 22 | **VERIFIED** |
| 2 | Release v0.4.0 exists | GitHub release | `gh release view v0.4.0 --repo neuron7xLab/bsff --json tagName` | `v0.4.0` · https://github.com/neuron7xLab/bsff/releases/tag/v0.4.0 | **VERIFIED** |
| 3a | An asset `bsff-v0.4.0.intoto.jsonl` is attached to the release | release | `gh release view v0.4.0 --json assets` | present | **VERIFIED** |
| 3b | The asset's bytes have sha256 `94b5187d…` | downloaded file | `sha256sum bsff-v0.4.0.intoto.jsonl` | `94b5187d11d0defefea17529c5e6f01a7f6b2732d6aa7e2936ebd4c85905f387` | **VERIFIED — file identity only, NOT proof of provenance validity** |
| 3c | Asset is a structurally-valid SLSA-v0.2 in-toto statement attesting the v0.4.0 wheel+sdist | decoded DSSE | `python -c "import json,base64;b=json.load(open('bsff-v0.4.0.intoto.jsonl'));print(base64.b64decode(b['dsseEnvelope']['payload']))"` | subjects `bsff-0.4.0-*.whl` sha256 `2e355d18…`, `bsff-0.4.0.tar.gz` sha256 `0700a6ff…` | **VERIFIED** |
| 4 | Provenance **signature** chain-of-trust valid (Fulcio/Rekor) | sigstore bundle | `cosign verify-blob-attestation …` | 1 signature; not verifiable offline | **NEEDS_EXTERNAL_CHECK** |
| 4b | Attested digests match the **distributed** artifacts | — | compare subjects vs released/installed whl+sdist | release carries ONLY the `.intoto.jsonl` — wheel/sdist not attached, nothing to cross-check | **NEEDS_EXTERNAL_CHECK / GAP** |
| 4c | "SLSA provenance is valid" (the load-bearing claim) | depends on 4 ∧ 4b | — | bounded by weakest leg | **NOT VERIFIED — corrected; earlier flat "VERIFIED" was an overclaim (file-hash ≠ validity)** |
| 5 | Test count = 310 | `tools/update_status.py` | `python -m pytest tests/ --collect-only -p no:cacheprovider \| grep collected` | `310 tests collected` (= 310 passed) | **VERIFIED** |
| 5b | STATUS.md previously said 306 | `STATUS.md` history | see `TEST_COUNT_RECONCILIATION.md` | stale: 306 = pre-#42 (PR #42 added 4 tests); regenerated to 310 | **VERIFIED (was stale)** |
| 6 | 7 machine-checked invariants | `tests/test_invariants.py` | `grep -oE 'INV-[0-9]+' tests/test_invariants.py \| sort -u` | INV-1…INV-7 | **VERIFIED** |
| 7 | Real LOSO result (within-subject does not generalize) | `research/bci_generalization/result_bnci2014_001_sub1-2.json` | `cat research/bci_generalization/result_bnci2014_001_sub1-2.json` | within 0.807 → cross-subject 0.603, gap +0.204, sub2 0.518 ≈ chance | **VERIFIED** |
| 7b | "BCI within-subject accuracy does not generalize" as a *general* claim | now n=9 on a second dataset, but still single-dataset | — | direction holds (cross ≈ chance); magnitude is dataset-specific; not yet a population claim | **UNPROVEN (single dataset)** |
| 7c | n=9 PhysioNet EEGMMI LOSO measurement (supersedes the n=2 anecdote) | `research/bci_generalization/result_eegbci_loso_n9.json` | `python research/bci_generalization/run_loso_eegbci.py --subjects 1-9` | within 0.612 → cross 0.531 (≈chance), gap 0.082; 4/9 subjects at chance even within-subject | **VERIFIED (measurement; the 0.807 n=2 was not representative — see `docs/FINDING_N9.md`)** |
| 8 | MOABB adapter exists, fail-closed, raw-guarded | `src/bsff/moabb_adapter.py`, `tests/test_moabb_adapter.py` | `python -m pytest tests/test_moabb_adapter.py -q` | 6 tests pass (FakeRaw, no moabb dep) | **VERIFIED** |
| 9 | Seed-stability certification (INV-7) | `src/bsff/stability.py`, `tests/test_stability.py` | `python -m pytest tests/test_stability.py -q` | 8 tests pass; flipping verdict → `UNSTABLE` | **VERIFIED** |
| 10 | Canonical manuscript | `docs/MANUSCRIPT.md` | `test -f docs/MANUSCRIPT.md` | present (v0.4.0) | **VERIFIED** |
| 11a | Surrogate **marginal** preserved exactly (a mathematical invariant) | `tools/validate_surrogate_fidelity.py` | `python tools/validate_surrogate_fidelity.py` | marginal max-diff = 0 | **VERIFIED** |
| 11b | Surrogate **spectrum/covariance** within tolerance | `artifacts/surrogate_fidelity.json` | `python tools/validate_surrogate_fidelity.py` | spectrum ≤1.1%, covariance ≤0.09% vs **engineering** thresholds (<5%) | **VERIFIED (engineering/smoke-grade per `docs/REPRODUCIBILITY.md`; NOT external/regulatory)** |
| 11c | Surrogate math is **externally** validated (TISEAN reference) | — | — | not run | **NEEDS_EXTERNAL_CHECK** — and any verdict from `bsff adjudicate-data` (incl. CASE-001 Stage 7) inherits this open leg |
| 12 | Externally validated against TISEAN | — | TISEAN reference binary not available in sandbox | not done; intrinsic-property validation only | **NEEDS_EXTERNAL_CHECK** |
| 13 | A real published EEG dataset is shipped in the repo | — | — | no human EEG data committed; only synthetic + downloaded-at-runtime | **FALSE (not shipped) — intentional** |
| 14 | Second-dataset confirmation that cross-subject decoding ≈ chance | `research/bci_generalization/result_eegbci_loso_n9.json` | `python research/bci_generalization/run_loso_eegbci.py --subjects 1-9` | PhysioNet EEGMMI n=9: cross-subject LOSO = 0.531 ≈ chance, confirming no cross-subject transfer (a *second* dataset beyond BNCI2014_001) | **VERIFIED (direction only; ≥3rd dataset + n>9 still open)** |

## How to re-run the whole audit

```bash
git clone https://github.com/neuron7xLab/bsff && cd bsff
pip install -e '.[dev]'
python -m pytest tests/ --collect-only -p no:cacheprovider | grep collected   # 310
python -m pytest -q                                                            # 310 passed
python tools/update_status.py --check                                          # STATUS in sync
gh release download v0.4.0 --pattern '*.intoto.jsonl' && sha256sum bsff-v0.4.0.intoto.jsonl
cat research/bci_generalization/result_bnci2014_001_sub1-2.json
```
