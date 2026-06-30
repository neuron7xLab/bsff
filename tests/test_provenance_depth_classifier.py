from pathlib import Path

from tools.ci.classify_provenance_depth import classify


def test_skipped_attestation_becomes_policy_gap(tmp_path: Path) -> None:
    wf = tmp_path / "w.yml"
    wf.write_text(
        "\n".join(
            [
                "name: P",
                "jobs:",
                "  p:",
                "    steps:",
                "      - name: Sign build provenance (keyless Sigstore)",
                "        if: github.event_name != 'pull_request'",
                "        uses: actions/attest-build-provenance@v4",
                "      - run: python tools/generate_sbom.py --outdir artifacts/sbom",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    doc = classify(tmp_path)
    assert doc["verdict"] == "PASS_WITH_POLICY_GAPS"
    assert "ATTESTATION_SKIPPED_POLICY_GAP" in doc["classes"]
