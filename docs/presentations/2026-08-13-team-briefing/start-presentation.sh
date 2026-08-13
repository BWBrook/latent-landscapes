#!/usr/bin/env bash
set -euo pipefail

port="${1:-8765}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
url="http://localhost:${port}/"

cd "$here"
python3 -m http.server "$port" --bind 127.0.0.1 >/tmp/latent-landscapes-presentation.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT INT TERM

sleep 0.6
if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -Command "Start-Process '${url}'" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$url"
fi

printf 'Latent Landscapes briefing: %s\n' "$url"
printf 'Press Ctrl+C here after the presentation.\n'
wait "$server_pid"
