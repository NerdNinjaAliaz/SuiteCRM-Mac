#!/usr/bin/env bash
# Launch the CRM HTML prototype in a default desktop browser.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
HTML="$HERE/suitecrm_mac.html"
[[ -f "$HTML" ]] || { echo "Missing $HTML" >&2; exit 1; }
case "$(uname -s)" in
  Darwin) open "$HTML" ;;
  Linux)
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$HTML"
    else
      echo "No xdg-open command found. Open $HTML in your browser." >&2
      exit 1
    fi ;;
  *) echo "Open $HTML manually in a browser." >&2; exit 1 ;;
esac
echo "Opened local CRM preview. Full appearance requires CDN connectivity."
