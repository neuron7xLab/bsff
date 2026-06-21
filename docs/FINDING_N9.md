<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Finding: the n=2 number was not representative

The earlier generalization measurement used **n=2** subjects and reported a
within-subject accuracy of **0.807**. Run on **n=9** real PhysioNet EEGMMI
subjects (same paradigm, CSP+LDA, left-vs-right fist), the picture is soberer:

| metric | n=2 (earlier) | n=9 (this finding) |
|--------|---------------|--------------------|
| within-subject mean | 0.807 | **0.612** |
| cross-subject (LOSO) mean | 0.603 | **0.531** |
| generalization gap | 0.204 | **0.082** |
| subjects at chance (≤0.55) within-subject | — | **4 / 9** |

Two readings, both honest:

1. **The 0.807 was two lucky subjects.** At n=9 the within-subject accuracy is
   0.612, with 4 of 9 subjects at or near chance *even within subject*. A demo or
   paper that reports ~0.80 on a hand-picked pair is not describing the dataset;
   it is describing its pair.
2. **The gap shrank because the ceiling fell, not because generalization
   improved.** Cross-subject is 0.531 — essentially chance. The model does not
   transfer across people; it barely works within one.

This is the framework turned on its own prior output: more data made the number
*worse and more honest*. The reproducible script is
`research/bci_generalization/run_loso_eegbci.py`; the artifact is
`result_eegbci_loso_n9.json`. It is network/CPU-bound and does not run in CI — it
is exactly the kind of external evidence the decision gate tracks as the open V6
leg, now partially addressed (n>2 on one real dataset; still single-dataset, no
TISEAN).
