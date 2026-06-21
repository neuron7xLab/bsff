<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Self-conformance — the system verifies itself through its own output

A declared contract (`contracts/bsff_contract.yaml`) lists what BSFF claims to
provide. `tools/run_contract_conformance.py` checks each item against the
repository's **actual** output and emits a machine verdict
(`artifacts/conformance/CONFORMANCE_VERDICT.json`).

```bash
python tools/run_contract_conformance.py
```

## Item states

| state | meaning |
|-------|---------|
| `CONFORMANT` | the file exists / the command exits 0 |
| `NONCONFORMANT` | declared and feasible, but missing or failed — a real defect |
| `UNVERIFIABLE` | declared `blocked` (network / GPU / external binary) — honestly not checkable here, **never faked CONFORMANT** |

Overall: `NONCONFORMANT` if any feasible item fails (fail-closed); `PARTIAL` if
all feasible pass but some are blocked; `CONFORMANT` only if every item passes.

## Current verdict (this repository)

**`PARTIAL`** — 10 CONFORMANT, 0 NONCONFORMANT, 4 UNVERIFIABLE.

- **CONFORMANT (10):** self-falsification controls, null registry, threshold
  registry, surrogate fidelity, STATUS sync, invariants suite, manuscript, claim
  audit, real LOSO result, validation corpus.
- **UNVERIFIABLE (4):** release-signature chain (network), case-001 EEGNet
  baseline (network+GPU), case-001 split/leakage/surrogate attacks (depend on the
  baseline), TISEAN external validation (external C binary).

`PARTIAL` is the honest verdict: everything the environment can check is
conformant, and everything it cannot is named as blocked — not quietly claimed.
A green `PARTIAL` here means *no feasible promise is broken*. It does not mean the
blocked work is done.
