<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Fail-closed decision table

| condition | decision state | claim allowed |
|-----------|----------------|---------------|
| G1 power ≥ 0.80 AND G2 CI-upper ≤ 0.05 | `BONN_S2_BRIGHT_LINE_ROBUSTLY_PASSED` | robust bright-line pass |
| G1 ≥ 0.80, predeclared-seed FPR ≤ 0.05, G2 CI-upper > 0.05 | `BONN_NOMINAL_S2_PASS_BUT_G2_NOT_ROBUST` | nominal single-seed pass only |
| G1 < 0.80 OR seed-avg FPR clearly > 0.05 | `BRIGHT_LINE_NOT_PASSED` | none |
| data absent | `BLOCKED_DATA` | none |
| method invalid for regime | `BLOCKED_METHOD` | none |
| runtime/repo surface absent | `BLOCKED_RUNTIME` | none |

No other state. Non-PASS always carries a non-zero exit. Current: row 2 (nominal, not robust).
