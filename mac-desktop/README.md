# SuiteCRM for Mac — Desktop Companion (Source)

A **standalone SuiteCRM-inspired desktop CRM**, designed for macOS and web browsers. It is **not** the upstream SuiteCRM PHP application, and **does not connect to the PHP/MySQL SuiteCRM server**. Its models deliberately borrow SuiteCRM terminology (Accounts, Contacts, Leads, Opportunities, AOS Quotes, Cases, Activities, Vardefs and Logic Hooks).

## Quick start

### Easiest: browser version

Open `suitecrm_mac.html` in Chrome or Safari. The app comes with **clearly fictitious demo customer records** and uses browser `localStorage` for persistence. It loads Tailwind CSS, Chart.js and Google Fonts from CDNs, so an internet connection is required for full styling and charts.

### Native window on macOS

Requires macOS with Apple Xcode Command Line Tools installed. In **Terminal**:

```bash
xcode-select --install  # if not already installed
cd mac-desktop
./build_mac.sh
./SuiteCRM-Mac
```

Or compile directly:

```bash
swiftc MacApp.swift -framework Cocoa -framework WebKit -o SuiteCRM-Mac
./SuiteCRM-Mac
```

Keep `suitecrm_mac.html` in the same directory as the compiled executable. `WKWebView` uses native macOS window controls. The native application saves its browser-form CRM dataset to:

`~/Library/Application Support/SuiteCRM-for-Mac/beans.json`

**Backup this file** before upgrading, resetting demo data, or importing anything. `Export Database` opens a macOS save dialog for JSON.

> Apple code signing/notarization is not configured. This builds an unsigned local executable, **not** a ready-to-distribute `.app` package. The Swift shell needs an actual macOS compile test; it cannot be compiled on Linux.

### Python SQLite engine

Python 3.10 or newer, **no pip dependencies**. The Python engine has an **independent** SQLite datastore and a small command-line API:

```bash
python3 sugarbean_engine.py init
python3 sugarbean_engine.py summary
python3 sugarbean_engine.py create Accounts '{"name":"Acme Supplies","account_type":"Customer"}'
python3 sugarbean_engine.py list Accounts
python3 sugarbean_engine.py workflows
python3 -m unittest -v test_suitecrm_mac.py
```

Database file: `~/Library/Application Support/SuiteCRM-for-Mac/crm.sqlite3` by default; use `--db /path/to/file.sqlite3` to change it. **SQLite is not connected live to the HTML/WebKit app**; these are two implementations for experimentation and eventual integration. JSON import/export is the supported interchange path:

```bash
python3 sugarbean_engine.py import-json path/to/suitecrm_mac_beans_export.json
python3 sugarbean_engine.py export-json path/to/sqlite-backup.json
```

Importing preserves record IDs and does **not** replay business hooks, to avoid duplicating automation side effects.

## Modules

| Module | Meaning |
|---|---|
| Dashboard | Pipeline KPIs, weighted forecast, won deals, leads and open cases |
| Accounts | Companies and relationships |
| Contacts | Individual stakeholders linked to accounts |
| Leads | Unqualified prospects, eligible for one-click conversion |
| Opportunities | Six sales stages, Kanban and probability syncing |
| Quotes | AOS-style subtotal, discount, tax and quote total |
| Cases | Customer support tickets and P1 escalation |
| Activities | Calls, meetings and tasks linked to parents |
| AOW Workflows | Four configurable demonstration logic hooks |
| Studio & Vardefs | Inspect declarative field metadata in the browser UI |

**Search:** `⌘K` on macOS, `Ctrl+K` elsewhere. **Escape:** closes a modal.

## Important limitations

- The frontend JavaScript `BeanStoreEngine` and backend Python `SugarBeanSQLiteEngine` are **independent**. There is currently no native-to-Python IPC or bidirectional synchronization.
- This is an **offline-capable data model**, but its web UI depends on online CDN assets for full appearance. It is not a bundled, fully offline distribution.
- The browser app offers JSON export; **XLSX, DOCX and PDF exports are not implemented** in this release.
- Demo-data resets overwrite the current browser/native data store. Export backups first.
- This demonstration does not implement authentication, roles, field-level permissions, audit security, PII encryption, cloud sync, conflict resolution or hardened input validation. **Do not use it for sensitive production customer data.**
- Source code is provided for customization and learning, not a drop-in replacement for SuiteCRM 7/8.

## Source layout

```text
mac-desktop/
├── suitecrm_mac.html           # UI, JavaScript store, charts and Vardefs
├── MacApp.swift                # AppKit/WKWebView wrapper & native JSON persistence
├── build_mac.sh                # macOS build helper
├── sugarbean_engine.py        # SQLite CRM model & business hooks
├── test_suitecrm_mac.py       # 13 Python unit/integration tests
├── SUITECRM_MAC_DOCUMENTATION.md
├── README.md
└── publish_to_github.sh       # Optional explicit-push helper
```

For original SuiteCRM, go to https://github.com/SuiteCRM/SuiteCRM. For the user's fork, go to https://github.com/NerdNinjaAliaz/SuiteCRM. Read `FORK_GUIDE.md` in this zip before copying code into the fork.

## License / origin

The upstream SuiteCRM/SuiteCRM repository is licensed under **AGPL-3.0** (see the original `LICENSE.txt`). Preserve its copyright notices, license, Git history, and attribution. The included standalone Mac companion has been authored around the supplied HTML and added Python/Swift code; it is **inspired by** SuiteCRM but is not an official SuiteCRM distribution. Review the licensing implications if you integrate it with upstream code or redistribute a modified combined application.
