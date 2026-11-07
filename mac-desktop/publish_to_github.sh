#!/usr/bin/env bash
set -euo pipefail
# Run from an existing clone of NerdNinjaAliaz/SuiteCRM, mac-version branch.
# Nothing is pushed until user explicitly executes this script.
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" != "mac-version" ]]; then
  echo "Refusing to publish: switch to 'mac-version' branch first (current: $BRANCH)." >&2
  exit 1
fi
ORIGIN="$(git remote get-url origin)"
if [[ "$ORIGIN" != *"NerdNinjaAliaz/SuiteCRM"* ]]; then
  echo "Refusing to publish: unexpected origin '$ORIGIN'" >&2
  exit 1
fi
if [[ ! -f mac-desktop/suitecrm_mac.html ]]; then
  echo "Missing mac-desktop/suitecrm_mac.html" >&2
  exit 1
fi
git add mac-desktop README_MAC_DESKTOP.md .github/workflows/mac-desktop-tests.yml
if git diff --cached --quiet; then
  echo "No Mac-desktop changes to commit."
  exit 0
fi
git commit -m "Add standalone SuiteCRM for Mac desktop companion"
git push origin mac-version
