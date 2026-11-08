#!/usr/bin/env bash
# Run from WSL2. No dependencies beyond bash, python3, wslpath.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PY_WIN="$ROOT/.venv/Scripts/python.exe"
LAUNCHER="$ROOT/wsl/launch_mcp.sh"
if [[ ! -f "$PY_WIN" || ! -f "$LAUNCHER" ]]; then
  echo 'Missing Windows venv or bridge. Run Windows install.ps1 first.' >&2
  exit 2
fi
if ! command -v wslpath >/dev/null 2>&1; then
  echo 'wslpath not found. Run this from WSL2, not native Linux.' >&2
  exit 2
fi
SNIPPET="$(python3 - "$LAUNCHER" <<'PY'
import json,sys
launcher=sys.argv[1]
print('[mcp_servers.autocad2019]')
print('command = ' + json.dumps('/bin/bash'))
print('args = ' + json.dumps([launcher]))
print('startup_timeout_sec = 60')
print('tool_timeout_sec = 120')
print('supports_parallel_tool_calls = false')
PY
)"
OUT="$ROOT/codex_autocad2019_snippet.toml"
printf '%s\n' "$SNIPPET" > "$OUT"
echo "Generated: $OUT"
echo "$SNIPPET"
if [[ "${1:-}" != '--apply' ]]; then
  echo 'Review the snippet. To append to ~/.codex/config.toml: bash wsl/configure_codex.sh --apply'
  exit 0
fi
CONFIG="$HOME/.codex/config.toml"
mkdir -p "$(dirname "$CONFIG")"
if [[ -f "$CONFIG" ]] && grep -Eq '^\[mcp_servers\.autocad2019\]' "$CONFIG"; then
  echo "Entry already exists in $CONFIG; no change made. Remove/update it manually if necessary." >&2
  exit 3
fi
HAD_CONFIG=0
BACKUP="$CONFIG.backup.$(date +%Y%m%d%H%M%S)"
if [[ -f "$CONFIG" ]]; then
  HAD_CONFIG=1
  cp -- "$CONFIG" "$BACKUP"
fi
# Validate generated snippet before touching config.
python3 - "$OUT" <<'PY'
import sys
raw=open(sys.argv[1],encoding='utf-8').read()
assert raw.startswith('[mcp_servers.autocad2019]\n') and 'command = ' in raw and 'args = ' in raw
try:
    import tomllib
except ImportError:
    print('Info: Python <3.11; snippet checked structurally. Codex CLI will validate full TOML.')
else:
    with open(sys.argv[1], 'rb') as f:
        conf=tomllib.load(f)
    assert 'autocad2019' in conf['mcp_servers']
PY
if [[ -f "$CONFIG" && -s "$CONFIG" ]]; then printf '\n' >> "$CONFIG"; fi
printf '%s\n' "$SNIPPET" >> "$CONFIG"
# Validate merged TOML where Python 3.11+ is available; restore on failure.
if ! python3 - "$CONFIG" <<'PY'
import sys
try:
    import tomllib
except ImportError:
    print('Info: WSL Python <3.11; verify merged config with codex mcp list.')
    sys.exit(0)
with open(sys.argv[1], 'rb') as f:
    tomllib.load(f)
PY
then
  if [[ "$HAD_CONFIG" == 1 ]]; then
    cp -- "$BACKUP" "$CONFIG"
  else
    rm -f -- "$CONFIG"
  fi
  echo 'Invalid merged TOML; original config restored.' >&2
  exit 4
fi
echo "Added autocad2019 MCP entry to: $CONFIG"
echo 'Restart Codex, then use: codex mcp list'
