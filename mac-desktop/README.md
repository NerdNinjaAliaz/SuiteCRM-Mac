# SuiteCRM for Mac · Desktop Companion

**[← Main README](../README.md)** · **[Project website](../docs/index.html)** · **[DMG guide](DMG_GUIDE.md)** · **[Architecture](SUITECRM_MAC_DOCUMENTATION.md)**

> Standalone, **unofficial prototype**. It is not a PHP SuiteCRM desktop client and does not connect to or sync with SuiteCRM's backend.

## Choose how to run

| Mode | Requirements | Command (from repository root) |
|:--|:--|:--|
| Browser preview | Modern browser; internet for CDN styling/charts | `bash mac-desktop/run_browser.sh` |
| Native macOS window | macOS + Xcode Command Line Tools | `bash mac-desktop/run_mac.sh` |
| Universal `.app` + DMG | macOS 13+ + Xcode Command Line Tools | `bash mac-desktop/build_dmg.sh` |
| Python SQLite engine | Python 3.10+ standard library | `python3 mac-desktop/sugarbean_engine.py init` |

Install the Apple compiler tools if necessary using `xcode-select --install`.

The DMG is created in `mac-desktop/dist/`. For a no-local-Mac build, run the [GitHub Actions DMG workflow](https://github.com/NerdNinjaAliaz/SuiteCRM-Mac/actions/workflows/build-macos-dmg.yml) on branch `mac-version`. Its unsigned-for-distribution build may trigger Gatekeeper warnings.

## Optional CLI and tests

```bash
python3 mac-desktop/sugarbean_engine.py init
python3 mac-desktop/sugarbean_engine.py summary
python3 mac-desktop/sugarbean_engine.py create Accounts '{"name":"Example Co","account_type":"Customer"}'
python3 mac-desktop/sugarbean_engine.py list Accounts
python3 -m unittest discover -s mac-desktop -p 'test_suitecrm_mac.py' -v
```

## Files

- `suitecrm_mac.html`: JS UI, sample CRM data, views, charts and local storage.
- `MacApp.swift`: native AppKit/WebKit host, menu and JSON persistence bridge.
- `build_mac.sh`, `run_mac.sh`: compile or compile-and-launch the native executable.
- `run_browser.sh`: open local HTML in the default browser.
- `build_dmg.sh`, `GenerateIcon.swift`: create an icon, universal `.app`, and drag-to-Applications `.dmg`.
- `sugarbean_engine.py`: independent Python/SQLite API, JSON import/export and automations.
- `test_suitecrm_mac.py`: Python unit/integration tests.
- `SUITECRM_MAC_DOCUMENTATION.md` and `DMG_GUIDE.md`: full documentation.

## Data and limitations

| Browser | Native macOS | Python CLI |
|---|---|---|
| `localStorage` | `~/Library/Application Support/SuiteCRM-for-Mac/beans.json` | `~/Library/Application Support/SuiteCRM-for-Mac/crm.sqlite3` |

The data stores do **not** synchronize automatically. The browser relies on online Tailwind CSS, Chart.js and Google Fonts. No production encryption, authentication, authorization or cloud synchronization is included. **Avoid sensitive real customer data.** XLSX, DOCX and PDF export are not included.

## License & attribution

This fork preserves upstream [SuiteCRM/SuiteCRM](https://github.com/SuiteCRM/SuiteCRM), licensed AGPL-3.0 (see [LICENSE.txt](../LICENSE.txt)). This Mac component is independently authored and not officially endorsed by SuiteCRM.
