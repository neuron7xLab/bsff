<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Statistical Validity Contract

This document defines the minimum scientific-statistical contract required for BSFF
claims to approach R6/R7 status.

The machine-enforceable starter implementation lives in
[`src/bsff/statistics/contracts.py`](src/bsff/statistics/contracts.py).

## Mandatory result fields

Every scientific result must declare:

- effect size or operational effect measure;
- confidence interval or equivalent uncertainty estimate;
- null-model result;
- seed sensitivity;
- dataset-specific result;
- aggregate result;
- failure threshold;
- interpretation boundary.

## Required null-model classes

At minimum, BSFF evidence should be able to express:

- shuffled-label null;
- phase-randomized surrogate;
- colored-noise / AR null;
- block bootstrap;
- adversarial synthetic signal;
- dataset-specific negative control.

## Failure conditions

A scientific claim fails if:

- a positive claim lacks null comparison;
- uncertainty is absent;
- one lucky seed drives the result;
- aggregate result hides dataset-level failure;
- exploratory evidence is presented as validation;
- provenance or artifact hashes drift;
- the claim scope exceeds the evidence boundary.

## Interpretation boundary

The strongest valid positive language in BSFF is:

> survived falsification under stated conditions

Forbidden language includes:

- proved;
- confirmed universal validity;
- clinical-grade;
- regulatory-grade;
- diagnostic;
- therapeutic.

## CI starter gate

The current gate validates registry shape and contract semantics:

```bash
pytest tests/test_statistical_contract.py
```

Future hardening should parse generated result artifacts and fail when any scientific
result lacks null comparison, uncertainty, seed sensitivity, or failure semantics.
