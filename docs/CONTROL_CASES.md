<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Control cases — self-falsification before authority

Before BSFF may judge any external claim, it must show on ground truth that it
can be wrong in **both** directions (Axiom 7). Two controls, run through the same
engine as any case:

| control | signal | asserted claim | required verdict |
|---------|--------|----------------|------------------|
| `000a` negative | white noise (no structure) | "has nonlinear structure" | **not SURVIVED** |
| `000b` positive | Hénon map (genuine nonlinearity) | "has nonlinear structure" | **SURVIVED** |

```bash
python tools/verify_controls.py     # exits non-zero unless both controls pass
```

## A real defect this surfaced (and the fix)

The negative control **failed on first run**: white noise returned `SURVIVED`.
This was not a flake — it is the documented anti-conservativeness of the bare
rank-order surrogate test for finite-N linear-Gaussian data. Measured across 10
seeds:

| decision rule | white noise → SURVIVED | Hénon → SURVIVED |
|---------------|------------------------|------------------|
| rank-order only (bayes off) | **2 / 10** (false) | 10 / 10 |
| **conjunction gate** (p≤α AND BF10≥3) | **0 / 10** ✓ | 10 / 10 ✓ |

The controls therefore run the **conjunction gate**, and a strict verdict
requires it. This is exactly what a self-falsification control is for: it caught
that the data-driven path (`adjudicate_dataset` with the gate off) is
anti-conservative on noise, and forced the calibrated rule. The finding is
recorded here rather than hidden; the bare-rank-order path remains available for
fast smoke use but must not be used for a strict `SURVIVED`.

## Registries that make a verdict defensible

- `null_hypotheses.yaml` — every H0 is explicit (statement, test, reject rule,
  failure status). No p-value without a registered null. Validate:
  `python tools/validate_null_registry.py`.
- `thresholds.yaml` — every threshold carries provenance (value, reason,
  source). No magic numbers. Validate:
  `python tools/validate_threshold_registry.py`.

## Honest scope (what is NOT in this change)

The full v4.0 program (PhysioNet/EEGNet baseline, TISEAN reference binary,
surrogate-on-EEGNet, FAIR/RO-Crate packaging) is **network- and GPU-bound** and
out of this change. What is delivered here is the part that needs neither and
that hardens the instrument: working self-falsification controls, explicit
nulls, and threshold provenance.
