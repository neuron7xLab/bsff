<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Known failures (preserved, not hidden)

1. **G2 specificity not robust** — seed-averaged AR-null FPR 0.0354, Wilson 95% CI [0.022, 0.056]
   crosses the 0.05 gate. The Bonn S2 bright line is a nominal single-seed pass, NOT robustly crossed.
2. **S1 lagged_quadratic** — ~20% Set-E power (insufficient). Preserved as the first negative result.
3. **BNCI method transfer** — S2-C1 anti-conservative on narrowband 501-sample epochs (probe FPR 0.375);
   BNCI is `BNCI_BLOCKED_METHOD`, not executed.
4. **Replication** — Cho2017/Lee2019 not executed (scaffolds only); `multi_dataset_replication_state=NOT_DONE`.
5. **Docker `evidence verify`** — needs git in the slim image (host-only tool); selftest works in-container.

These are evidence, not embarrassment: a falsifier must publish where it fails.
