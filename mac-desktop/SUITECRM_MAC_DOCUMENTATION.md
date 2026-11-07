# SuiteCRM for Mac — Architecture, Developer & User Documentation

## Project status

This repository contains a complete **source package for a prototype Mac desktop companion**, consisting of a browser UI, macOS `WKWebView` shell and an **independent** SQLite implementation of CRM workflows. Upstream SuiteCRM is a larger PHP/MySQL product. This project intentionally does not claim source compatibility with SuiteCRM's actual PHP SugarBean, BeanFactory, vardef parser or SuiteCRM REST API.

### Architecture

```text
macOS: NSWindow + WKWebView
    └── suitecrm_mac.html
         ├── UI and declarative SUITECRM_VARDEFS
         ├── JS BeanStoreEngine
         ├── AOW sample hooks + Kanban + charts
         ├── Browser → localStorage
         └── Native bridge → Application Support/beans.json

Separate Python CLI
    └── sugarbean_engine.py
         ├── SQLite `beans` rows (module + id + JSON data)
         ├── Workflows flags/counters
         ├── Audit log
         ├── Transactional lead conversion
         └── JSON import/export
```

There is **no direct data sync** between the JS store and the Python SQLite engine. An architecturally correct future version would replace the JavaScript data-source methods with an IPC layer and use SQLite as the only source of truth.

### JavaScript metadata registry

`SUITECRM_VARDEFS` is a JavaScript object in `suitecrm_mac.html` containing fields, types, drop-down options, module labels and relationship subpanels. You can add fields by extending the corresponding module's `fields` array; the form renderer and inspector follow this schema. Do not confuse this with PHP `vardefs.php` consumed by real SuiteCRM.

### Modules and reference fields

- **Accounts**: name, account_type, industry, annual_revenue, phone_office, website, billing_address_city, assigned_user_name.
- **Contacts**: first_name, last_name, title, account_id, email1, phone_work, lead_source.
- **Leads**: first_name, last_name, account_name, status, lead_source, estimated_value, email1, phone_work, title.
- **Opportunities**: name, account_id, sales_stage, amount, probability, date_closed, assigned_user_name.
- **Quotes (AOS-inspired)**: name, account_id, opportunity_id, stage, subtotal_amount, discount_percent, tax_percent, expiration; calculated amounts.
- **Cases**: name, account_id, priority, status, type, resolution.
- **Activities**: name, activity_type, status, parent_type, parent_id, date_due, assigned_user_name.

### Workflows (toggleable independently in each engine)

| Rule | Phase | Trigger | Action |
|---|---|---|---|
| `aow-1` | before_save | Opportunity stage | Set probability to Prospecting 10%, Qualification 25%, Proposal 65%, Negotiation 80%, Won 100%, Lost 0% |
| `aow-2` | before_save | Quote save | Compute discount from subtotal, tax after discount, and final amount |
| `aow-3` | after_save | Newly created P1 Case | Create escalation activity/task linked to the case |
| `aow-4` | after_save | Opportunity enters Closed Won | Create an onboarding kickoff meeting linked to the owning Account |

The Python version uses integer cents-equivalent rounding through `Decimal` for accurate two-decimal quote calculation and SQLite savepoints for nested `save_bean` operations. It blocks repeat Lead conversions and avoids duplicate onboarding when the same Won opportunity is saved again. The JavaScript prototype follows the original uploaded UI implementation and may differ in some edge cases.

### Lead conversion

1. Look up a company name in Accounts (case-insensitive) or create an Account.
2. Create a Contact linked to the Account.
3. Create a Qualification-stage Opportunity initialized to 25% probability and the Lead's estimated value.
4. Mark the Lead as converted and store its new record IDs.
5. In the Python engine, wrap every step in a SQLite transaction. If any step raises, rollback everything.

### Relationships

The Python API `get_related_beans(parent_module, parent_id, target_module)` (alias `load_relationship`) supports Account → Contacts / Opportunities / Quotes / Cases / Activities, Opportunity → Quotes, and parent-linked Activities. Contacts resolve related Opportunities/Cases through their parent Account. This is a small purpose-built resolver, **not** SuiteCRM's many-to-many relation engine.

### Storage and migration

- Browser: namespaced `localStorage` key `suitecrm_mac_beanstore_v1`.
- Native macOS: `~/Library/Application Support/SuiteCRM-for-Mac/beans.json`, written atomically via the WKScriptMessageHandler.
- Python CLI: `~/Library/Application Support/SuiteCRM-for-Mac/crm.sqlite3` using SQLite WAL mode for file-backed databases.
- Export/import: use JSON backup from browser or native app, then `python3 sugarbean_engine.py import-json backup.json`. Imported records keep their original IDs and do not fire hooks. Use `export-json` to create an independent JSON backup of SQLite.

### Running on macOS

```bash
cd mac-desktop
chmod +x build_mac.sh
./build_mac.sh
./SuiteCRM-Mac
```

Requires macOS and Apple Xcode Command Line Tools. `Swiftc` compiles the window runner, not an `.app` bundle. The Swift file must be compiled and exercised on a real Mac; the source archive was created and tested in a Linux-based build environment where AppKit is unavailable.

### Automated tests

```bash
cd mac-desktop
python3 -m unittest -v test_suitecrm_mac.py
```

Python tests cover CRUD, metadata module count, stage syncing, quote math, case escalation, onboarding deduplication, lead conversion, relationships, workflow toggles, KPIs, import/export, rollback, decimal rounding. The HTML UI also contains eight JavaScript self-tests. During this packaging, those self-tests were isolated from actual persistence so they do not overwrite live browser records.

### Engineering to-do / production readiness

1. Implement a genuine WebKit-to-Python/SQLite API bridge (one datastore and one workflow implementation).
2. Bundle vetted styles/scripts/fonts locally or ship a network-capable installer with integrity verification.
3. Implement import preview, schema/version migrations, validation and robust error reporting.
4. Add user authentication/authorization, encrypted backups and per-record access controls.
5. Add XLSX/DOCX/PDF report exporters with actual integration tests.
6. Implement strict content escaping / HTML sanitization and a Content Security Policy before accepting untrusted data.
7. Create a signed, notarized `.app` via an Xcode project, with update and backup strategy.
8. Add a migration adapter for the real SuiteCRM REST API if connecting to an existing installation is desired.

### Upstream references

- Repo: https://github.com/SuiteCRM/SuiteCRM
- SugarBean: https://docs.suitecrm.com/developer/core-framework/working-with-beans/
- Metadata/Vardefs: https://docs.suitecrm.com/developer/core-framework/metadata/
- Logic Hooks: https://docs.suitecrm.com/developer/core-framework/logic-hooks/
- Forking docs: https://docs.github.com/en/pull-requests/how-tos/work-with-forks/fork-a-repo
