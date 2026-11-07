#!/usr/bin/env bash
# Creates a universal macOS app and a drag-to-Applications DMG.
set -euo pipefail
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="SuiteCRM for Mac"
EXECUTABLE="SuiteCRM-Mac"
BUNDLE_ID="io.github.nerdninjaaliaz.suitecrm-mac"
VERSION="${VERSION:-1.0.0}"
MIN_MACOS="13.0"
ARCHES="${ARCHES:-universal}"  # universal | native | arm64 | x86_64
OUT_DIR="${SOURCE_DIR}/dist"
FINAL_APP="${OUT_DIR}/${APP_NAME}.app"
FINAL_DMG="${OUT_DIR}/SuiteCRM-for-Mac-${VERSION}.dmg"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo 'ERROR: Run this script on macOS (AppKit and hdiutil are required).' >&2
  exit 1
fi
if ! [[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo 'ERROR: VERSION must look like 1.0.0' >&2
  exit 1
fi
for command in xcrun ditto hdiutil codesign sips plutil; do
  command -v "$command" >/dev/null || { echo "Missing $command. Install Xcode Command Line Tools." >&2; exit 1; }
done
[[ -f "${SOURCE_DIR}/suitecrm_mac.html" && -f "${SOURCE_DIR}/MacApp.swift" ]] || {
  echo 'ERROR: Missing MacApp.swift or suitecrm_mac.html.' >&2; exit 1;
}

mkdir -p "${OUT_DIR}"
# Work in hidden staging; do not expose an unfinished .app in Finder.
TMP_DIR="$(mktemp -d "${OUT_DIR}/.suitecrm-building.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
APP_PATH="${TMP_DIR}/${APP_NAME}.app"
DMG_PATH="${TMP_DIR}/SuiteCRM-for-Mac-${VERSION}.dmg"
mkdir -p "${APP_PATH}/Contents/MacOS" "${APP_PATH}/Contents/Resources"
SDK="$(xcrun --sdk macosx --show-sdk-path)"
case "$ARCHES" in
  universal) TARGETS=(arm64 x86_64) ;;
  native) TARGETS=("$(uname -m)") ;;
  arm64|x86_64) TARGETS=("$ARCHES") ;;
  *) echo 'ERROR: ARCHES must be universal, native, arm64, or x86_64' >&2; exit 1 ;;
esac
echo "Building ${APP_NAME} ${VERSION} for ${TARGETS[*]} ..."
BINS=()
for arch in "${TARGETS[@]}"; do
  BIN="${TMP_DIR}/${EXECUTABLE}-${arch}"
  echo "Compiling ${arch} (do not open the app before SUCCESS) ..."
  if ! xcrun swiftc -Onone -sdk "$SDK" -target "${arch}-apple-macos${MIN_MACOS}" \
    -framework Cocoa -framework WebKit "${SOURCE_DIR}/MacApp.swift" -o "$BIN" >"${TMP_DIR}/compile-${arch}.log" 2>&1; then
    echo "ERROR: Swift compilation failed for ${arch}; details:" >&2
    tail -n 100 "${TMP_DIR}/compile-${arch}.log" >&2
    exit 1
  fi
  [[ -s "$BIN" ]] || { echo "ERROR: No executable produced for ${arch}" >&2; exit 1; }
  BINS+=("$BIN")
done
if [[ ${#BINS[@]} -gt 1 ]]; then
  xcrun lipo -create "${BINS[@]}" -output "${APP_PATH}/Contents/MacOS/${EXECUTABLE}"
else
  ditto "${BINS[0]}" "${APP_PATH}/Contents/MacOS/${EXECUTABLE}"
fi
chmod 755 "${APP_PATH}/Contents/MacOS/${EXECUTABLE}"
[[ -x "${APP_PATH}/Contents/MacOS/${EXECUTABLE}" ]] || { echo "Missing executable" >&2; exit 1; }
xcrun lipo -info "${APP_PATH}/Contents/MacOS/${EXECUTABLE}"
ditto "${SOURCE_DIR}/suitecrm_mac.html" "${APP_PATH}/Contents/Resources/suitecrm_mac.html"

ICON_PNG="${TMP_DIR}/icon-1024.png"
if xcrun swift "${SOURCE_DIR}/GenerateIcon.swift" "$ICON_PNG" >"${TMP_DIR}/icon.log" 2>&1 && [[ -s "$ICON_PNG" ]]; then
  HAVE_ICON=true
else
  HAVE_ICON=false
  echo "WARNING: Icon creation failed; continuing with the system default app icon." >&2
  tail -n 8 "${TMP_DIR}/icon.log" >&2 || true
fi
ICONSET="${TMP_DIR}/AppIcon.iconset"
ICON_PLIST=""
if [[ "$HAVE_ICON" == true ]]; then
  mkdir -p "$ICONSET"
  ICON_OK=true
  for pt in 16 32 128 256 512; do
    sips -s format png -z "$pt" "$pt" "$ICON_PNG" --out "${ICONSET}/icon_${pt}x${pt}.png" >/dev/null || ICON_OK=false
    doubled=$((pt * 2))
    sips -s format png -z "$doubled" "$doubled" "$ICON_PNG" --out "${ICONSET}/icon_${pt}x${pt}@2x.png" >/dev/null || ICON_OK=false
  done
  if [[ "$ICON_OK" == true ]] && xcrun iconutil -c icns "$ICONSET" -o "${APP_PATH}/Contents/Resources/AppIcon.icns"; then
    ICON_PLIST="<key>CFBundleIconFile</key><string>AppIcon</string>"
  else
    echo "WARNING: Icon conversion failed; using default icon." >&2
  fi
fi

cat > "${APP_PATH}/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>SuiteCRM for Mac</string>
  <key>CFBundleDisplayName</key><string>SuiteCRM for Mac</string>
  <key>CFBundleExecutable</key><string>SuiteCRM-Mac</string>
  <key>CFBundleIdentifier</key><string>${BUNDLE_ID}</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>${VERSION}</string>
  <key>CFBundleVersion</key><string>1</string>
  ${ICON_PLIST}
  <key>LSMinimumSystemVersion</key><string>${MIN_MACOS}</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
</dict>
</plist>
PLIST
printf 'APPL????' > "${APP_PATH}/Contents/PkgInfo"
plutil -lint "${APP_PATH}/Contents/Info.plist"
[[ -s "${APP_PATH}/Contents/Resources/suitecrm_mac.html" ]] || { echo "HTML resource missing" >&2; exit 1; }
if [[ -n "${SIGN_IDENTITY:-}" ]]; then
  codesign --force --options runtime --timestamp --sign "$SIGN_IDENTITY" "$APP_PATH"
else
  echo 'Ad-hoc signing for local testing (not Developer ID notarized).'
  codesign --force --sign - "$APP_PATH"
fi
codesign --verify --strict --verbose=2 "$APP_PATH"

STAGING="${TMP_DIR}/dmg-root"
mkdir -p "$STAGING"
ditto "$APP_PATH" "${STAGING}/${APP_NAME}.app"
ln -s /Applications "${STAGING}/Applications"
rm -f "$DMG_PATH"
hdiutil create -volname "SuiteCRM for Mac ${VERSION}" \
  -srcfolder "$STAGING" -ov -format UDZO "$DMG_PATH"
hdiutil verify "$DMG_PATH"
if [[ -n "${SIGN_IDENTITY:-}" ]]; then
  codesign --force --timestamp --sign "$SIGN_IDENTITY" -i "${BUNDLE_ID}.dmg" "$DMG_PATH"
fi
if [[ -n "${NOTARY_PROFILE:-}" ]]; then
  [[ -n "${SIGN_IDENTITY:-}" ]] || { echo 'NOTARY_PROFILE needs SIGN_IDENTITY' >&2; exit 1; }
  xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG_PATH"
  xcrun stapler validate "$DMG_PATH"
fi
echo "Publishing only the complete, verified app and DMG..."
rm -rf "$FINAL_APP"
rm -f "$FINAL_DMG"
mv "$APP_PATH" "$FINAL_APP"
mv "$DMG_PATH" "$FINAL_DMG"
printf 'SUCCESS: %s\n' "$FINAL_DMG"
printf 'App bundle: %s\n' "$FINAL_APP"
if [[ -z "${SIGN_IDENTITY:-}" ]]; then
  echo 'Note: This is an ad-hoc-signed development DMG. Gatekeeper may warn on other Macs.'
fi
