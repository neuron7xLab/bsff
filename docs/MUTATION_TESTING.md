<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Mutation probe — do the tests have teeth?

A high test count measures volume, not value. This probe mutates
decision-critical logic in `src/bsff/verdict_engine.py` and checks whether the
suite **notices**. A killed mutant means a test caught the break; a survivor is a
real gap. It is baseline-guarded: if the suite is not green first, it aborts.

```bash
python tools/mutation_probe.py     # artifacts/mutation_probe.json
```

## What it found, and what was done

First run: **4 / 5** — and the survivor was real.

| mutation (single-point flip) | result |
|------------------------------|--------|
| invert verdict assignment (`SURVIVED`/`REFUTED`) | KILLED |
| flip BF01 null-evidence comparison | KILLED |
| flip conjunction-gate comparison (`BF10 <` → `>`) | KILLED |
| invert leakage fail-closed gate | KILLED |
| flip low-surrogate caveat threshold (`< 99` → `> 99`) | **SURVIVED → gap** |

The four verdict-determining mutations were all caught — the logic that decides
SURVIVED/REFUTED/UNSUPPORTED is genuinely tested. But the low-surrogate **caveat**
(a warning appended when `surrogate_count < 99`) was asserted by no test: flipping
its comparison changed behaviour and nothing failed.

`tests/test_low_surrogate_caveat.py` closes it — it passes on clean code and fails
under the mutant. Re-running the probe now scores **5 / 5**.

## Honest scope

This is a **curated sample of 5 semantic mutations on one module**, not an
exhaustive mutation-testing sweep (no `mutmut`/`cosmic-ray` full run over the
codebase). It demonstrates that the *decision-critical* path has teeth and it
found one genuine caveat-coverage gap; it does **not** certify the whole codebase.
A full sweep is future work and would itself be CPU-bound external evidence, like
the n=9 LOSO and the operating-characteristic calibration.
