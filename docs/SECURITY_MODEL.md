<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Security model

## Assets

- falsification verdict integrity,
- validation artifact integrity,
- dependency supply chain,
- GitHub Actions workflow integrity,
- contributor trust boundary,
- absence of private neuro/medical data in public artifacts.

## Threats

| Threat | Control |
|---|---|
| False `SURVIVED` verdict | surrogate, leakage, stationarity, calibration, truth-contract tests |
| Dependency compromise | Dependabot, dependency review, pip-audit |
| Workflow privilege escalation | explicit permissions, local Actions policy checker |
| Secret exposure | GitHub secret scanning/push protection plus local regex scan |
| Inflated README claims | `tools/validate_truth_contract.py` |
| Unreviewed main changes | CODEOWNERS + ruleset JSON |

## Trust boundary

Public issues and PRs are untrusted. Do not run contributor-provided data or code outside CI isolation unless it is minimized and reviewed. Do not upload private EEG/BCI data. Do not accept “trust me bro” as a data governance framework, despite its popularity among mammals.
