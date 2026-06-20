<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Aiming BSFF at an external claim

This directory is a worked, reproducible adversarial dossier. It shows how to
point BSFF at *someone else's* claim about a signal and get a machine-readable,
provenance-stamped verdict — not a self-test on synthetic data.

## The two files you provide

1. **A claim** (`claim.json`) — a `ClaimSpec`: what is being asserted, on what
   signal, under what null model and significance level. Unknown fields are
   rejected fail-closed, so a typo cannot silently weaken the contract.
2. **A signal** (`.npy` / `.csv` / `.tsv`) — the raw data the claim stands on.
   Its shape must match the claim exactly (`n_channels × n_samples`); a mismatch
   aborts the run rather than reshaping the data into a passing verdict.

## Run it

```bash
# A genuinely nonlinear signal survives the surrogate attack.
bsff falsify --claim claim.json --signal signal_chaotic.csv --policy strict
#  -> verdict: SURVIVED   (p ≈ 0.001)

# The same claim on a linear-stochastic null is refuted.
bsff falsify --claim claim.json --signal signal_null.csv --policy strict
#  -> verdict: REFUTED    (p ≈ 0.8)

# Persist the dossier for the record:
bsff falsify --claim claim.json --signal signal_chaotic.csv --out case.json
```

## Reading the verdict

| Verdict | Meaning |
| --- | --- |
| `SURVIVED` | Survived the surrogate attack **and** the Bayesian corroboration gate. The claim is *not refuted* — never read as "proven". |
| `REFUTED` | The statistic is indistinguishable from (or consistent with) the linear-stochastic null, or a leakage path was detected. |
| `UNSUPPORTED` | The instrument could not earn a confident verdict (e.g. non-converged surrogate null). Fail-closed: absence of evidence, not evidence of absence. |

The emitted case-file carries `signal_provenance.sha256` (byte-level hash of the
input), `contract_sha256`, and a self-verifying `artifact_sha256`, so any third
party can confirm exactly which bytes produced which verdict.

> To falsify a real published claim, replace `claim.json` with the paper's
> assertion and the `.csv` with the released dataset. BSFF does not trust it. It
> tests it.
