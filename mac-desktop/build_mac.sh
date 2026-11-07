#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This native launcher must be built on macOS (AppKit + WebKit)." >&2
  exit 1
fi
xcrun --find swiftc >/dev/null || { echo "Install Xcode Command Line Tools: xcode-select --install"; exit 1; }
TMP_BIN="$(mktemp "${PWD}/.SuiteCRM-Mac-build.XXXXXX")"
trap 'rm -f "$TMP_BIN"' EXIT
xcrun swiftc -Onone MacApp.swift -framework Cocoa -framework WebKit -o "$TMP_BIN"
[[ -s "$TMP_BIN" ]] || { echo "ERROR: No executable was built." >&2; exit 1; }
chmod 755 "$TMP_BIN"
mv -f "$TMP_BIN" SuiteCRM-Mac
echo "Built $(pwd)/SuiteCRM-Mac"
echo "Run: ./SuiteCRM-Mac"
