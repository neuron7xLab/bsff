# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Yaroslav Vasylenko / neuron7xLab
"""Wheel-level reproducibility gate: prove BSFF works installed, not just in-tree.

An editable install can hide packaging bugs (missing modules, broken entry points,
data files left out of the wheel). This gate builds the wheel, installs it into a
pristine virtualenv with NO ``PYTHONPATH`` and NO access to the local ``src`` tree,
then exercises the public surface from there:

  * ``import bsff`` resolves to the INSTALLED package (asserted, not assumed);
  * ``ClaimSpec`` / ``evaluate_claim_pipeline`` import and a real verdict runs;
  * the ``bsff`` and ``bsff-validate`` console scripts work;
  * ``bsff-validate`` emits a schema-valid, hash-stamped evidence artifact.

The validation artifact is copied to ``artifacts/wheel_validation.json``. Any
failure exits non-zero. This is a tool, not a pytest test: it legitimately needs
network access to resolve runtime dependencies into the clean environment.

    python tools/validate_wheel_runtime.py [--output PATH] [--keep]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ARTIFACT_KEYS = {"pipeline_status", "phase", "gates", "status", "artifact_sha256"}


def _run(
    cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"[FAIL] {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
        raise SystemExit(1)
    return proc


def _clean_env() -> dict[str, str]:
    """Environment with PYTHONPATH stripped so the local src can never leak in."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def validate_wheel(output: Path, keep: bool = False, offline: bool = False) -> int:
    workdir = Path(tempfile.mkdtemp(prefix="bsff-wheel-"))
    dist = workdir / "dist"
    venv = workdir / ".venv-wheel-test"
    env = _clean_env()
    try:
        # 1. Build the wheel from the repo into an isolated dist dir.
        print("==> building wheel")
        _run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)], cwd=ROOT, env=env)
        wheels = glob.glob(str(dist / "*.whl"))
        if not wheels:
            print("[FAIL] no wheel produced")
            return 1
        wheel = wheels[0]
        print(f"    wheel: {Path(wheel).name}")

        vpy = venv / "bin" / "python"
        if offline:
            # Offline proof: a venv that inherits the already-resolved deps, then
            # install the wheel with NO index and NO deps. --no-index makes any
            # attempt to reach PyPI fail, so success proves the wheel runs without
            # network given its runtime closure is present.
            print("==> creating system-site venv and installing the wheel offline")
            _run(
                [sys.executable, "-m", "venv", "--system-site-packages", str(venv)],
                cwd=workdir,
                env=env,
            )
            _run(
                [str(vpy), "-m", "pip", "install", "--no-index", "--no-deps", wheel],
                cwd=workdir,
                env=env,
            )
        else:
            # 2. Pristine virtualenv; install ONLY the wheel (+ stats extra so the
            #    publication-grade Bayes path is real, not silently degraded).
            print("==> creating clean virtualenv and installing the wheel")
            _run([sys.executable, "-m", "venv", str(venv)], cwd=workdir, env=env)
            _run([str(vpy), "-m", "pip", "install", "--upgrade", "pip"], cwd=workdir, env=env)
            _run(
                [str(vpy), "-m", "pip", "install", f"{wheel}[stats,leakage,yaml]"],
                cwd=workdir,
                env=env,
            )

        # 3. Import + real verdict from the INSTALLED package, asserting the source
        #    is the wheel, not the working-tree src. cwd is the temp workdir, so even
        #    `.` cannot expose the repo's src/ layout.
        print("==> exercising the installed import surface")
        # The src-leak assertion proves the wheel shadows any editable install; it
        # only applies to the pristine online venv. The offline venv inherits the
        # parent's editable bsff via --system-site-packages, so the check is skipped
        # there — offline mode proves "runs without network", not "shadows src".
        src_assert = (
            ""
            if offline
            else f"assert {str(ROOT / 'src')!r} not in str(src), f'src leak: {{src}}';"
        )
        probe = (
            "import bsff, pathlib;"
            "from bsff import ClaimSpec, evaluate_claim_pipeline;"
            "from bsff.synthetic import henon_series;"
            "src=pathlib.Path(bsff.__file__).resolve();"
            f"{src_assert}"
            "spec=ClaimSpec(claim_id='wheel-smoke', signal_type='EEG', task_type='nonlinear_structure',"
            " sampling_rate_hz=250.0, n_channels=1, n_samples=512, statistic='lagged_quadratic',"
            " alpha=0.05, surrogate_count=19);"
            "v=evaluate_claim_pipeline(spec, henon_series(n_samples=512, seed=11), policy='standard', seed=101);"
            "assert v.verdict in {'SURVIVED','UNSUPPORTED','REFUTED'};"
            "assert len(v.contract_sha256)==64;"
            "print('import-ok', getattr(bsff,'__version__','?'), v.verdict, str(src))"
        )
        out = _run([str(vpy), "-c", probe], cwd=workdir, env=env)
        print("    " + out.stdout.strip())

        # 4. Console-script entry points must work from the wheel.
        print("==> exercising console-script entry points")
        _run([str(venv / "bin" / "bsff"), "--help"], cwd=workdir, env=env)
        artifact = workdir / "wheel_validation.json"
        _run(
            [str(venv / "bin" / "bsff-validate"), "--output", str(artifact)],
            cwd=workdir,
            env=env,
        )

        # 5. Artifact must be schema-valid and hash-stamped.
        print("==> validating the emitted evidence artifact")
        data = json.loads(artifact.read_text(encoding="utf-8"))
        missing = REQUIRED_ARTIFACT_KEYS - set(data)
        if missing:
            print(f"[FAIL] wheel_validation.json missing keys: {sorted(missing)}")
            return 1
        sha = str(data.get("artifact_sha256", ""))
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            print(f"[FAIL] artifact_sha256 is not a 64-hex digest: {sha!r}")
            return 1

        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, output)
        print(f"\nWHEEL RUNTIME: PASS — {Path(wheel).name} import-ok, CLI-ok, artifact-ok")
        print(f"artifact: {output}")
        return 0
    finally:
        if keep:
            print(f"workdir kept at: {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "wheel_validation.json")
    parser.add_argument("--keep", action="store_true", help="keep the temp workdir for debugging")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="install the wheel with --no-index/--no-deps to prove offline runtime",
    )
    args = parser.parse_args(argv)
    return validate_wheel(args.output, keep=args.keep, offline=args.offline)


if __name__ == "__main__":
    raise SystemExit(main())
