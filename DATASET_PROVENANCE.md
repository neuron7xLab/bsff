<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Dataset Provenance

This document defines the R6/R7 data lineage contract for BSFF.

A dataset is not valid evidence until its origin, license, preprocessing, split logic,
leakage audit, artifact outputs, and reproduction command are explicit.

The machine-readable companion file is [`data_registry.json`](data_registry.json).

## Dataset status levels

| Status | Meaning |
|---|---|
| `available` | Dataset or generator is committed or reproducibly generated. |
| `committed_evidence` | Dataset evidence is represented by committed artifacts and hash manifests. |
| `preregistered` | Dataset slot is reserved for R6/R7 but not yet executed. |
| `external_required` | External reviewer selection or execution is required. |

## Minimum R6 evidence shape

BSFF must not claim R6 until at least three evidence classes exist:

1. synthetic controlled dataset;
2. public EEG/BCI dataset;
3. adversarial or null-heavy dataset.

## Leakage audit requirements

Every dataset must declare:

- subject/session split model;
- preprocessing determinism;
- exclusion criteria;
- whether labels or subject identity can leak into metrics;
- whether repeated segments create clustered observations;
- which uncertainty method compensates for that design.

## Failure semantics

A dataset invalidates the claim if:

- origin is unclear;
- license is missing;
- preprocessing is not reproducible;
- hash or artifact reference cannot be verified;
- subject/session leakage is possible;
- the aggregate result hides dataset-level failure.
