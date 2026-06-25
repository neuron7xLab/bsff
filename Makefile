# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
.PHONY: lab-99 regen lock verify verify-offline build-proof openai-2026 mission-check hostile-review

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
	python tools/validate_artifact_schema.py
	python tools/regenerate.py --check
	bsff release-check --strict --output artifacts/release
	python -m build
	python tools/generate_evidence_bundle.py

# Regenerate every generated artifact in dependency order (STATUS -> MANIFEST -> pages).
regen:
	python tools/regenerate.py

# --- OpenAI-2026 research-grade validation grid -----------------------------

# Regenerate the hash-pinned dependency locks from pyproject.
lock:
	python -m pip install pip-tools
	pip-compile pyproject.toml --extra dev --extra leakage --extra stats --extra yaml --generate-hashes -o requirements/ci.lock
	pip-compile pyproject.toml --extra dev --generate-hashes -o requirements/dev.lock
	pip-compile pyproject.toml --extra dev --extra fuzz --generate-hashes -o requirements/fuzz.lock
	pip-compile pyproject.toml --extra dev --extra security --generate-hashes -o requirements/security.lock
	python tools/validate_lockfiles.py

# Full research-grade verification, ending on the machine-derived verdict.
verify:
	python -m ruff check src tests tools benchmarks fuzz
	python -m ruff format --check src tests tools benchmarks fuzz
	python -m pytest tests/ -m "not slow" --tb=short
	python -m pytest tests/property tests/adversarial --tb=short
	python -m pytest tests/redteam tests/meta_validation --tb=short
	python -m pytest tests/test_openai_2026_verdict_schema.py tests/test_openai_2026_claims.py --tb=short
	python tools/mutation_kill_gate.py --strict
	python tools/validate_mutation_report.py artifacts/adversarial/mutation_kill_report.json
	python tools/statistical_power_profile.py --output artifacts/statistics/power_profile.json
	python tools/validate_power_profile.py artifacts/statistics/power_profile.json
	python tools/record_offline_evidence.py
	python tools/run_replayability_gate.py
	python tools/generate_redteam_matrix.py
	python tools/validate_redteam_matrix.py
	python tools/validate_openai_2026_claims.py
	python tools/final_validation_verdict.py

# Same correctness surface, with external network denied.
verify-offline:
	python -m pytest tests/ -m "not slow" --tb=short --disable-network
	python -m pytest tests/property tests/adversarial --tb=short --disable-network
	python -m pytest tests/redteam tests/meta_validation --tb=short --disable-network

# Build proof: wheel runs offline, SBOM + manifest are reproducible.
build-proof:
	python -m build
	python tools/validate_wheel_runtime.py --offline
	python tools/generate_sbom.py --outdir artifacts/sbom
	python tools/validate_provenance.py
	python tools/generate_manifest.py --check

# The whole grid, locally.
openai-2026: lock verify-offline build-proof verify
	@echo "OpenAI-2026 validation grid complete."

# Mission-critical gate: no silent success, no ambiguous PASS, no stale truth, no unbounded claim.
mission-check:
	python -m compileall -q src tests examples research tools
	python -m pytest -q tests/ -m "not slow"
	bsff selftest
	bsff evidence verify
	python tools/validate_current_truth.py
	python tools/generate_current_truth.py --check
	python tools/validate_forbidden_claims.py
	python tools/validate_statistical_claims.py
	python tools/validate_truth_contract.py
	python tools/regenerate.py --check

# Reviewer-facing hostile-review surface.
hostile-review:
	@echo "See docs/reviewer_packet/HOSTILE_REVIEW_CHECKLIST.md and docs/ADVERSARIAL_REVIEW.md"
	bsff evidence verify
	python tools/validate_statistical_claims.py
	python tools/validate_forbidden_claims.py
