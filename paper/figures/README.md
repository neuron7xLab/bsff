<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Paper figures

Figures for the JOSS paper (`paper/paper.md`) are produced deterministically
from committed artifacts. No statistics are recomputed at render time; the
generator only visualises pinned numbers.

## Regenerate

```bash
python paper/figures/generate_figures.py
```

This reads `artifacts/operating_characteristic.json` (produced by
`tools/calibrate_operating_characteristic.py`) and writes
`paper/figures/operating_characteristic.png`.

If `matplotlib` is not installed the script degrades gracefully: it prints the
underlying survival-rate table and exits 0 without writing a PNG.

## Figures

- `operating_characteristic.png` — per-class survival rate under the
  frequentist rule and the shipped conjunction rule, with the nominal level
  `alpha` marked. The `henon` and `logistic` classes are power targets (should
  survive); the `ar1_phi*` and `white` classes are false-positive-rate targets
  (should not survive). Conjunction bars carry the 95% confidence interval from
  the artifact.
