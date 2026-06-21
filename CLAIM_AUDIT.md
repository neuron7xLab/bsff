<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# CLAIM_AUDIT

Every load-bearing claim about BSFF, with the evidence file, the command that
checks it, the value/hash, and a status. No claim without a check; anything not
provable here is marked `UNPROVEN` or `NEEDS_EXTERNAL_CHECK`.

Status legend: **VERIFIED** (reproduced here) · **UNPROVEN** (asserted, not
established at the stated scope) · **NEEDS_EXTERNAL_CHECK** (requires a resource
not available in this environment) · **FALSE** (checked and wrong).

| # | Claim | Evidence | Command | Value / hash | Status |
|---|-------|----------|---------|--------------|--------|
| 1 | 22 PRs #21–#42 merged | GitHub | `gh pr list --repo neuron7xLab/bsff --state merged --json number --jq '[.[].number]\|map(select(.>=21 and .<=42))\|length'` | 22 | **VERIFIED** |
| 2 | Release v0.4.0 exists | GitHub release | `gh release view v0.4.0 --repo neuron7xLab/bsff --json tagName` | `v0.4.0` · https://github.com/neuron7xLab/bsff/releases/tag/v0.4.0 | **VERIFIED** |
| 3 | SLSA provenance asset attached | release asset | `gh release download v0.4.0 --pattern '*.intoto.jsonl' && sha256sum bsff-v0.4.0.intoto.jsonl` | `94b5187d11d0defefea17529c5e6f01a7f6b2732d6aa7e2936ebd4c85905f387` | **VERIFIED** |
| 4 | Provenance attests the exact built wheel/sdist digests | intoto DSSE payload | decode base64 payload, compare subject digests to release artifacts | release carries only the `.intoto.jsonl`; subject cross-check not done here | **NEEDS_EXTERNAL_CHECK** |
| 5 | Test count = 310 | `tools/update_status.py` | `python -m pytest tests/ --collect-only -p no:cacheprovider \| grep collected` | `310 tests collected` (= 310 passed) | **VERIFIED** |
| 5b | STATUS.md previously said 306 | `STATUS.md` history | see `TEST_COUNT_RECONCILIATION.md` | stale: 306 = pre-#42 (PR #42 added 4 tests); regenerated to 310 | **VERIFIED (was stale)** |
| 6 | 7 machine-checked invariants | `tests/test_invariants.py` | `grep -oE 'INV-[0-9]+' tests/test_invariants.py \| sort -u` | INV-1…INV-7 | **VERIFIED** |
| 7 | Real LOSO result (within-subject does not generalize) | `research/bci_generalization/result_bnci2014_001_sub1-2.json` | `cat research/bci_generalization/result_bnci2014_001_sub1-2.json` | within 0.807 → cross-subject 0.603, gap +0.204, sub2 0.518 ≈ chance | **VERIFIED** |
| 7b | "BCI within-subject accuracy does not generalize" as a *general* claim | one dataset, n=2 subjects | — | true only as the measured BNCI2014_001 n=2 result; not a population claim | **UNPROVEN (n=2, 1 dataset)** |
| 8 | MOABB adapter exists, fail-closed, raw-guarded | `src/bsff/moabb_adapter.py`, `tests/test_moabb_adapter.py` | `python -m pytest tests/test_moabb_adapter.py -q` | 6 tests pass (FakeRaw, no moabb dep) | **VERIFIED** |
| 9 | Seed-stability certification (INV-7) | `src/bsff/stability.py`, `tests/test_stability.py` | `python -m pytest tests/test_stability.py -q` | 8 tests pass; flipping verdict → `UNSTABLE` | **VERIFIED** |
| 10 | Canonical manuscript | `docs/MANUSCRIPT.md` | `test -f docs/MANUSCRIPT.md` | present (v0.4.0) | **VERIFIED** |
| 11 | Surrogate fidelity (real IAAFT) | `tools/validate_surrogate_fidelity.py`, `artifacts/surrogate_fidelity.json` | `python tools/validate_surrogate_fidelity.py` | marginal 0 (exact), spectrum ≤1.1%, covariance ≤0.09% | **VERIFIED** |
| 12 | Externally validated against TISEAN | — | TISEAN reference binary not available in sandbox | not done; intrinsic-property validation only | **NEEDS_EXTERNAL_CHECK** |
| 13 | A real published EEG dataset is shipped in the repo | — | — | no human EEG data committed; only synthetic + downloaded-at-runtime | **FALSE (not shipped) — intentional** |
| 14 | Second-dataset confirmation of the LOSO gap | — | Zenodo/physionet downloads time out in sandbox | Zhou2016 / PhysionetMI / AlexMI all read-timeout | **NEEDS_EXTERNAL_CHECK** |

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
