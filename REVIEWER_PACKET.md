<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# REVIEWER_PACKET

One document for an external reviewer. No rhetoric.

## Install
```bash
git clone https://github.com/neuron7xLab/bsff && cd bsff
pip install -e '.[dev]'            # core + test tooling
pip install -e '.[moabb]'         # optional: real MOABB EEG (heavy, network)
```

## Run
```bash
python -m pytest -q                       # full suite — expect 310 passed
python -m bsff.cli --help                 # CLI surface
python tools/update_status.py --check     # STATUS.md is generated + in sync
```

## Reproduce the headline result
```bash
pip install -e '.[moabb]'
python research/bci_generalization/run_experiment.py \
  --dataset BNCI2014_001 --subjects 1 2 --out result.json
# within-session ~0.81, cross-subject (LOSO) ~0.60, gap ~+0.20; result.json carries sha256
```

## Validate the engine itself
```bash
python tools/validate_surrogate_fidelity.py            # surrogates are real IAAFT
python -m pytest tests/test_invariants.py -q           # the 7 axioms (INV-1..7)
python -m pytest tests/test_validation_corpus_v020_contract.py -q   # ground truth
```

## Verify the release provenance
```bash
gh release download v0.4.0 --repo neuron7xLab/bsff --pattern '*.intoto.jsonl'
sha256sum bsff-v0.4.0.intoto.jsonl
# expect 94b5187d11d0defefea17529c5e6f01a7f6b2732d6aa7e2936ebd4c85905f387
```

## Limitations
See `LIMITATIONS_HARD.md`. Summary: not TISEAN-validated externally; no shipped
human EEG; linear/spectral scope; LOSO result is n=2 minimal; not clinical/regulatory.

## Known blockers
- Second-dataset confirmation blocked by external download time-outs (Zenodo,
  physionet.org) in our environment — runs in a network with normal throughput.
- Full multi-subject LOSO and any deep-net (EEGNet) baseline need GPU/time and
  are out of the current repository's scope.

## What would falsify BSFF itself
A reviewer should reject BSFF's verdicts if any of these holds:
1. **Non-determinism:** the same `(input, seed)` yields different verdicts
   (`tests/test_invariants.py::test_inv1_*` would fail).
2. **A surrogate is not a real IAAFT surrogate:** marginal not preserved, or
   spectrum residual large (`validate_surrogate_fidelity.py` would fail).
3. **A null survives:** an IID/linear-Gaussian null returns `SURVIVED`
   (operating-characteristic false-positive rate exceeds α).
4. **Provenance break:** a report's `artifact_sha256` does not recompute, or a
   ledger fails `bsff ledger-verify`.
5. **A claim absent from its source is adjudicated** instead of quarantined.
6. **A verdict flips across seeds** but is still certified (not `UNSTABLE`).

If none of these holds, the verdicts are reproducible and fail-closed by
construction. If any holds, BSFF is broken and should not be trusted until fixed.
