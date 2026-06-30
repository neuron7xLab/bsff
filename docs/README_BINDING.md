<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# README Binding

The root `README.md` is intentionally left as the existing public entrypoint.

The R6/R7 scaffold binds to it indirectly through:

- `docs/R6_R7_ASCENSION_PROTOCOL.md`;
- `docs/PUBLIC_RESEARCH_POSITION.md`;
- `CLAIMS.md`;
- `claims.yaml`;
- `data_registry.json`;
- `tools/validate_r6_contracts.py`.

This keeps the PR review surface clean: the scaffold adds new research-software gates
without rewriting the existing public README narrative.

Rank boundary:

- BSFF is not yet R6/R7.
- A local PASS is not R6 by itself.
- R6 requires an external reviewer and external hostile reproduction.
