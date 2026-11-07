#!/usr/bin/env bash
# Read-only preflight for macOS Swift/DMG tools.
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "DMG builds require macOS. Use run_browser.sh for browser preview." >&2
  exit 1
fi
echo "macOS $(sw_vers -productVersion)"
if ! xcrun --find swiftc >/dev/null 2>&1; then
  echo "Missing Swift compiler. Install Xcode Command Line Tools: xcode-select --install" >&2
  exit 1
fi
for command in hdiutil codesign sips plutil ditto; do
  command -v "$command" >/dev/null || { echo "Missing required $command" >&2; exit 1; }
done
echo "Swift compiler: $(xcrun --find swiftc)"
if command -v python3 >/dev/null 2>&1; then
  python3 --version
else
  echo "Python is optional for desktop/DMG; Python 3.10+ is used for SQLite CLI."
fi
echo "Ready: bash mac-desktop/build_dmg.sh"
