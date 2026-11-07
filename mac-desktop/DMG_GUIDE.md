# Build SuiteCRM for Mac as a DMG

This is a **standalone WebKit desktop CRM prototype**, not the original SuiteCRM PHP/MySQL server. The application still fetches Tailwind CSS, Chart.js and fonts from CDNs. **Do not use it for sensitive production CRM data.**

## Build locally on a Mac (macOS 13+)

From a cloned checkout of this repository:

```bash
git switch mac-version
git pull --ff-only origin mac-version
cd mac-desktop
bash build_dmg.sh
open dist
```

Output:
- `dist/SuiteCRM for Mac.app` is the native application bundle.
- `dist/SuiteCRM-for-Mac-1.0.0.dmg` contains the app and an Applications shortcut.

Double-click the DMG and drag the app to Applications. The default build is a **universal** Apple Silicon + Intel binary and an **ad-hoc signed** developer build. Users who download it from the internet may receive macOS Gatekeeper warnings because it is not Developer ID signed and notarized.

## Build in GitHub Actions

1. Visit https://github.com/NerdNinjaAliaz/SuiteCRM-Mac/actions
2. Select **Build macOS DMG Installer**.
3. Click **Run workflow**, select branch **mac-version**, and start it. If Actions are disabled on your fork, enable them first in repository settings.
4. Once green, open the run, go to **Artifacts**, and download **SuiteCRM-for-Mac-1.0.0-DMG**.
5. Unzip the GitHub artifact to obtain the actual `.dmg`.

The DMG is kept as a workflow artifact for up to 30 days, subject to repository policy. To publish an ordinary direct-download link, create a GitHub Release and attach the DMG as an asset.

## Optional Developer ID signing and notarization

On a local Mac where your Apple Developer ID Application certificate is installed, use:

```bash
SIGN_IDENTITY='Developer ID Application: Your Name (TEAMID)' bash build_dmg.sh
```

For notarization first store a profile via Apple's `xcrun notarytool store-credentials` and then set `NOTARY_PROFILE` as well. Never put Apple passwords or signing certificates in this public repository.

By default the GitHub Actions build is *not notarized*. For a professional public release use Developer ID signing, the hardened runtime and Apple's notary service.

References:
- https://developer.apple.com/documentation/xcode/packaging-mac-software-for-distribution
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution

## Fix: Finder says the application may be damaged or incomplete

The earlier script created the public `dist/SuiteCRM for Mac.app` directory *before* Swift compilation completed. Finder could try to open that unfinished bundle. The current build uses a hidden staging directory, validates the executable, `Info.plist`, resources, code signature and DMG, then publishes only the finished files.

After getting the latest code, run:

```bash
rm -rf 'mac-desktop/dist/SuiteCRM for Mac.app'
rm -f 'mac-desktop/dist/SuiteCRM-for-Mac-1.0.0.dmg'
ARCHES=native bash mac-desktop/build_dmg.sh
```

**Wait for `SUCCESS` before opening Finder.** Use `ARCHES=universal` when you want an Intel + Apple Silicon installer. If compilation fails, the script now prints compiler diagnostics; share the `error:` line rather than the module-map paths above it. Do not disable Gatekeeper as a workaround for an unfinished app.

If HTTPS `git pull` fails, download the current branch ZIP in a browser: https://github.com/NerdNinjaAliaz/SuiteCRM-Mac/archive/refs/heads/mac-version.zip
