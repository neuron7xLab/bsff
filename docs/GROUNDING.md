<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Grounding — prose numbers bound to artifacts

> Ground: bind an abstract output to a verified external artifact — a number, a
> file, a command, a hash — after which the statement stops being text and
> becomes a checkable fact.

A number typed into a document is text: it can drift from reality or simply be
wrong, and nothing catches it. `tools/verify_grounding.py` binds every registered
load-bearing number to its generating artifact and fails closed if they differ.

```bash
python tools/verify_grounding.py
```

## What is grounded

| statement (in prose) | bound to artifact |
|----------------------|-------------------|
| MANUSCRIPT LOSO within-subject (0.807) | `research/bci_generalization/result_…json::within_mean` |
| MANUSCRIPT LOSO cross-subject (0.603) | `…::cross_subject_loso_mean` |
| MANUSCRIPT LOSO gap (0.204) | `…::loso_gap` |
| README test count | grounded **by reference** to `STATUS.md` (no hardcoded badge allowed) |

The gate re-derives each value from its artifact and asserts it appears in the
doc. A hand-typed number that no longer matches its source is rejected — the same
floor the claim audit and STATUS sync already enforce, extended to prose.

It is wired into `tools/verify_honesty.py`, so it runs in CI and is folded into
the release certificate chain. After it passes, those statements are facts, not
text. Adding a new grounded fact is one entry in `GROUNDED_FACTS`.
