#!/usr/bin/env bash
# Build and start standalone native macOS window.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "The native launcher requires macOS. Try run_browser.sh instead." >&2
  exit 1
fi
bash "$HERE/build_mac.sh"
cd "$HERE"
exec "$HERE/SuiteCRM-Mac"
