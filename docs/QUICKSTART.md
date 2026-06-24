<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Quickstart

BSFF is a falsification-first instrument: it tries to **refute** a signal claim and reports
SURVIVED / REFUTED / UNSUPPORTED / BLOCKED — never a bare "significant". This page gets an
external user from clone to a verified verdict in minutes. Not clinical, not regulatory.

## 1. Install
```bash
git clone https://github.com/neuron7xLab/bsff && cd bsff
python -m venv .venv && . .venv/bin/activate
python -m pip install -U pip && python -m pip install -e ".[dev,stats]"
bsff selftest          # operational-kernel self-validation
```

## 2. Verify the committed evidence (no data download needed)
```bash
bsff evidence verify   # coherence + hashes + release gate + raw-data hygiene
```
Exit 0 + `"state": "PASS"` means the repository's evidence is internally consistent and the
canonical state is `BONN_S2_BRIGHT_LINE_PASSED` (see `artifacts/release/CURRENT_TRUTH.json`).

## 3. Reproduce the Bonn S2 bright-line
```bash
bsff reproduce bonn-s2             # dry-run: verify committed S2 artifacts + hashes
bsff reproduce bonn-s2 --execute   # re-run the confirmatory (needs staged data; ~30-100 min)
```
Data staging (Bonn is license-gated, not shipped): see [`DATA_POLICY.md`](DATA_POLICY.md).

## 4. Run the benchmark yourself
```bash
bsff benchmark bonn-bright-line --mode exploratory     # candidate sweep (fast-ish)
bsff benchmark bonn-bright-line --mode confirmatory     # frozen S2 candidate (long)
```
Emits `state: PASS|FAIL|BLOCKED_DATA|BLOCKED_RUNTIME`; never prints PASS without artifacts.

## 5. Use BSFF on your own claim
```bash
bsff falsify --claim my_claim.json --signal my_signal.npy --out verdict.json
```

## Interpreting a verdict
See [`VERDICT_SEMANTICS`](validation/) and [`REPRODUCE.md`](../REPRODUCE.md). Forbidden uses
(clinical / diagnostic / regulatory / "final proof of brain dynamics" / universal BCI
authority) are enumerated in `artifacts/release/CURRENT_TRUTH.json` and never claimed.

## Common failures
- `BLOCKED_RUNTIME`: not run from a repo clone (needs `examples/` + `tools/`).
- `BLOCKED_DATA`: Bonn data not staged — see `DATA_POLICY.md`.
- `evidence verify` FAIL: a doc/artifact drifted from `CURRENT_TRUTH.json`; regenerate with
  `python tools/generate_current_truth.py` and re-check.
