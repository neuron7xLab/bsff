# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
.PHONY: lab-99 regen

# Full local lab run — mirrors the CI test + slow-tests + build surface.
lab-99:
	python -m pip install --upgrade pip
	python -m pip install -e '.[dev,stats,leakage,yaml]'
	python -m ruff check src tests tools
	python -m ruff format --check src tests tools
	python -m pytest tests/ -m "not slow" -v --tb=short --cov=bsff --cov-report=term-missing
	python -m pytest tests/ -m slow -v --tb=short
	bsff doctor --require-strict
	python tools/validate_architecture_contract.py
	python tools/validate_truth_contract.py
	python tools/validate_open_source_readiness.py
	python tools/check_github_actions_policy.py
	python tools/scan_secrets.py
	python tools/generate_provenance_manifest.py
	python tools/validate_ip_provenance.py
	python tools/validate_markdown.py
	python tools/validate_tisean_reference.py
	python tools/validate_real_eeg_case.py
	python tools/update_status.py --check
	python tools/generate_manifest.py --check
	python tools/regenerate.py --check
	bsff release-check --strict --output artifacts/release
	python -m build
	python tools/generate_evidence_bundle.py

# Regenerate every generated artifact in dependency order (STATUS -> MANIFEST -> pages).
regen:
	python tools/regenerate.py
