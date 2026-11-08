#!/usr/bin/env bash
# Sole Codex stdio launch entry. Keeps Windows process CWD on C: NTFS.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WIN_PY="$ROOT/.venv/Scripts/python.exe"
if [[ ! -f "$WIN_PY" ]]; then
  echo "[cad2019] Windows Python missing: $WIN_PY; run install.ps1" >&2
  exit 2
fi
if ! command -v wslpath >/dev/null 2>&1; then
  echo '[cad2019] wslpath missing: this launcher is for WSL2 only' >&2
  exit 2
fi
cd "$ROOT"
exec "$WIN_PY" -X utf8 "$(wslpath -w "$ROOT/windows/bridge.py")"
