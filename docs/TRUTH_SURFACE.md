<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab -->

# Truth surface

Every place BSFF makes a public claim is a *surface*. The truth contract
(`tools/validate_truth_contract.py`) scans all of them so no overclaim can drift
in through a doc, a badge, package metadata, or release notes.

## Scanned surfaces

| surface | how |
|---------|-----|
| `README.md`, `VERDICT.md` | phrase scan + required disclosures |
| `STATUS.md`, `DEMONSTRATION.md`, `CORE.md`, `DECISION.md`, `CLAIM_AUDIT.md` | phrase scan |
| `docs/*.md` (except contract-defining files) | phrase scan |
| `pyproject.toml` (PyPI metadata: description, keywords) | phrase scan |
| `CHANGELOG.md` / release notes | `tools/validate_release_notes.py` |
| CLI help text | sourced from `src/bsff/cli.py`, scanned with docs |

Contract-defining files (`TRUTH_SURFACE.md`, `VALIDATION_TIERS.md`, the tier
protocols) necessarily quote the forbidden vocabulary in order to forbid it; they
are checked for existence rather than phrase-scanned.

## Blocked claims (affirmative use fails CI)

```text
clinically validated
regulatory ready / regulatory grade
proves BCI claims
proves EEG claims
real EEG validated
TISEAN validated
external replication complete
external validation complete
scientifically proven
medical validation
production clinical use
```

## Allowed framing

```text
falsification-first
survived falsification under stated assumptions
synthetic ground truth
independent numpy reference (NOT external validation)
partial real EEG case (n=9, single dataset)
not clinical / not regulatory
TISEAN not met unless external binary evidence exists
independent replication not met unless an external artifact exists
```

The rule is constant: **widen enforcement, never raise claim strength.** This
document adds no capability claim; it only makes more places unable to lie.
