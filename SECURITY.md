<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.2.x | Yes, research kernel only |

## Reporting a vulnerability

Report privately through GitHub Security Advisories:
<https://github.com/neuron7xLab/bsff/security/advisories/new>
or by email to <neuron7x@ukr.net>.

We aim to acknowledge a report within **3 business days** and to publish a fix or
coordinated-disclosure timeline within **30 days**. Please do **not** open a
public issue for a vulnerability, and do **not** paste private EEG/BCI data,
credentials, medical records, access tokens, or subject identifiers into public
issues. Humans keep doing that and then call it “collaboration”. It is not.

Report:

1. affected version or commit,
2. exact command or workflow,
3. minimal reproduction,
4. whether the issue affects falsification validity, data leakage, supply chain, or artifact integrity.

## Security boundaries

BSFF is not a clinical, diagnostic, regulatory, or subject-identification system. It is a falsification-first research kernel. A security issue is any defect that lets a false claim pass as `SURVIVED`, hides caveats, corrupts evidence artifacts, or weakens CI gates.

## Dependency/security automation

The repository includes Dependabot, CodeQL, dependency review, local secret-pattern scanning, pip-audit, OpenSSF Scorecard, and release artifact provenance gates. GitHub repository-level secret scanning and push protection must still be enabled in the GitHub UI after publication.
