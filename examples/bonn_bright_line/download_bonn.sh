#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# BONN EEG DATASET — acquire + verify (Andrzejak et al. 2001, Phys. Rev. E 64, 061907)
# DOI: 10.1103/PhysRevE.64.061907
#
# CANONICAL SOURCE: UPF NTSA (https://www.upf.edu/web/ntsa/downloads).
#   epileptologie-bonn.de is OFFLINE since 2024. Do NOT use the UCI 178-feature variant.
#
# IMPORTANT — the UPF document endpoint is behind a Cloudflare JS challenge, so
# curl/wget CANNOT fetch the zips directly (they receive an HTML challenge page).
# The canonical zips must be fetched once via a real browser session, e.g.:
#   Sets:  Z.zip=A(healthy open)  O.zip=B(healthy closed)  N.zip=C  F.zip=D  S.zip=E(ictal)
#   Base:  https://www.upf.edu/documents/229517819/234490509/<NAME>.zip/<uuid>
# Staged layout expected by the bright-line scripts:
#   bonn_data/E/*.txt  bonn_data/A/*.txt  bonn_data/B/*.txt   (100 segments each)
#
# This script (a) tries the documented URLs, (b) DETECTS the Cloudflare wall, (c) if
# data is already staged, verifies it, and (d) otherwise writes a FAIL_DOWNLOAD
# marker and exits non-zero. It never fabricates a successful download.
#
# Usage: bash download_bonn.sh [TARGET_DIR=./bonn_data]

set -euo pipefail
TARGET_DIR="${1:-./bonn_data}"
FAIL_MARKER="../../artifacts/bonn_bright_line/FAIL_DOWNLOAD.json"

declare -A URL=(
  [A]="https://www.upf.edu/documents/229517819/234490509/Z.zip/9c4a0084-c0d6-3cf6-fe48-8a8767713e67"
  [B]="https://www.upf.edu/documents/229517819/234490509/O.zip/f324f98f-1ade-e912-b89d-e313ac362b6a"
  [E]="https://www.upf.edu/documents/229517819/234490509/S.zip/7647d3f7-c6bb-6d72-57f7-8f12972896a6"
)

echo "========================================================"
echo "Bonn EEG — acquire/verify | target=${TARGET_DIR}"
echo "  source: UPF NTSA (canonical, Cloudflare-gated)"
echo "========================================================"
mkdir -p "${TARGET_DIR}"

verify_staged() {
  local ok=1
  for S in E A B; do
    local n; n=$(ls "${TARGET_DIR}/${S}"/*.txt 2>/dev/null | wc -l)
    local lines="n/a"
    if [[ "${n}" -gt 0 ]]; then lines=$(wc -l < "$(ls "${TARGET_DIR}/${S}"/*.txt | head -1)"); fi
    echo "  Set ${S}: ${n} segments | samples/segment=${lines}"
    if [[ "${n}" -lt 1 ]]; then ok=0; fi
    if [[ "${lines}" != "4096" && "${lines}" != "4097" && "${lines}" != "n/a" ]]; then ok=0; fi
  done
  return $((1 - ok))
}

# If already staged (e.g. browser-fetched), verify and finish.
if verify_staged; then
  echo "Data already staged and format-verified (4096|4097 samples)."
  for S in E A B; do echo "  Set ${S} first-file sha256: $(sha256sum "$(ls "${TARGET_DIR}/${S}"/*.txt | head -1)" | cut -c1-16)…"; done
  echo "OK"
  exit 0
fi

# Otherwise try curl and detect the Cloudflare wall.
echo "Data not staged — attempting direct download (expected to be Cloudflare-blocked)…"
TMP=$(mktemp -d)
blocked=0
for S in E A B; do
  out="${TMP}/${S}.zip"
  curl -sL -A "Mozilla/5.0" "${URL[$S]}" -o "${out}" || true
  if head -c2 "${out}" 2>/dev/null | grep -q 'PK'; then
    echo "  Set ${S}: got a ZIP — unzipping"; mkdir -p "${TARGET_DIR}/${S}"; unzip -o -q "${out}" -d "${TARGET_DIR}/${S}"
  else
    echo "  Set ${S}: NOT a ZIP (Cloudflare challenge HTML) — direct download blocked"; blocked=1
  fi
done
rm -rf "${TMP}"

if [[ "${blocked}" -eq 1 ]] && ! verify_staged; then
  mkdir -p "$(dirname "${FAIL_MARKER}")"
  cat > "${FAIL_MARKER}" <<JSON
{
  "status": "FAIL_DOWNLOAD",
  "reason": "UPF NTSA document endpoint is Cloudflare-gated; curl/wget receive an HTML challenge, not the ZIP.",
  "remedy": "Fetch the canonical zips once via a real browser session (URLs in this script) and stage as bonn_data/{E,A,B}/*.txt, then re-run.",
  "source_urls": {"A": "${URL[A]}", "B": "${URL[B]}", "E": "${URL[E]}"},
  "do_not_substitute": "Do NOT use the UCI 178-feature variant or any non-canonical mirror."
}
JSON
  echo "WROTE ${FAIL_MARKER} — STOP. Stage the canonical data via browser, then re-run." >&2
  exit 1
fi

verify_staged
echo "OK"
