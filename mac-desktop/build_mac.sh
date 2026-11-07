#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This native launcher must be built on macOS (AppKit + WebKit)." >&2
  exit 1
fi
xcrun --find swiftc >/dev/null || { echo "Install Xcode Command Line Tools: xcode-select --install"; exit 1; }
swiftc MacApp.swift -framework Cocoa -framework WebKit -o SuiteCRM-Mac
echo "Built $(pwd)/SuiteCRM-Mac"
echo "Run: ./SuiteCRM-Mac"
