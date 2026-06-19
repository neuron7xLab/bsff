<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# BSFF Quality Gates

## Required local gate

```bash
python -m pytest
python tools/validate_architecture_contract.py
python tools/validate_truth_contract.py
python tools/validate_open_source_readiness.py
python tools/check_github_actions_policy.py
python tools/scan_secrets.py
python tools/validate_ip_provenance.py
python tools/validate_markdown.py
python tools/validate_validation_corpus.py
python -m build
```

## Gate semantics

| Gate | Purpose | Failure meaning |
|---|---|---|
| pytest | code contract | implementation drift |
| architecture contract | pipeline topology | architecture mutation without review |
| truth contract | README honesty | overclaiming or marketing contamination |
| OSS readiness | public repo hygiene | missing community/security metadata |
| actions policy | CI hardening | unsafe token permissions or unpinned patterns |
| secret scan | credential hygiene | accidental sensitive content |
| IP provenance | attribution chain | unclear authorship or license state |
| validation corpus | data reproducibility | synthetic oracle corrupted or stale |
| build | packaging | install/release breakage |

## Release rule

A release cannot claim `READY` unless every gate passes on a clean checkout.
Partial pass means `DEVELOPMENT_ONLY`. This is brutal and useful, unlike most
status labels invented by humans under deadline pressure.
