# SuiteCRM for Mac — Architecture, Developer & User Documentation

**SuiteCRM for Mac** is a native-inspired macOS desktop and WebKit CRM application modeled on the core architecture of the open-source [SuiteCRM Repository](https://github.com/SuiteCRM/SuiteCRM). It brings SuiteCRM's enterprise data model—[SugarBean ORM](https://docs.suitecrm.com/developer/core-framework/working-with-beans/), declarative [Metadata (Vardefs)](https://docs.suitecrm.com/developer/core-framework/metadata/), relationship subpanels, [Leads](https://docs.suitecrm.com/user/sales-relationships/leads/) conversion, [AOS Quotes](https://docs.suitecrm.com/user/sales-relationships/quotes-invoices-contracts/), and [Logic Hooks](https://docs.suitecrm.com/developer/core-framework/logic-hooks/)—into a fast, zero-dependency macOS experience.

## 1. Architectural Overview

SuiteCRM for Mac mirrors the three foundational layers of [SuiteCRM](https://github.com/SuiteCRM/SuiteCRM):

| Architectural Layer | SuiteCRM (PHP / MySQL) | SuiteCRM for Mac (`suitecrm_mac.html` + `sugarbean_engine.py`) |
| :--- | :--- | :--- |
| **Data Model (ORM)** | [SugarBean](https://docs.suitecrm.com/developer/core-framework/working-with-beans/) & `BeanFactory` | `BeanStoreEngine` (JS LocalStorage/Memory) & `SugarBeanSQLiteEngine` (Python SQLite) |
| **Declarative Metadata** | `vardefs.php`, `detailviewdefs.php`, `listviewdefs.php` ([Metadata](https://docs.suitecrm.com/developer/core-framework/metadata/)) | `SUITECRM_VARDEFS` schema registry driving tables, forms, filters, and inspectors dynamically |
| **Relationship Engine** | `load_relationship()` & Subpanel definitions | `getRelatedBeans()` / `load_relationship()` resolving 1-to-many subpanels inside the macOS Inspector Drawer |
| **Automation & Hooks** | [Logic Hooks](https://docs.suitecrm.com/developer/core-framework/logic-hooks/) (`before_save`, `after_save`) & AOW Workflows | Built-in AOW Rules 1–4 executing automatically on Bean creation, stage updates, and case escalations |
| **Desktop Shell** | Apache / IIS Web Browser UI | Native macOS `NSWindow` + `WKWebView` wrapper (`MacApp.swift`) with traffic-light controls & `⌘K` Spotlight search |

## 2. Core Modules & Functional Specifications

Every stock module is defined in `SUITECRM_VARDEFS` and supports full CRUD operations, enum filtering, Spotlight search (`⌘K`), and relationship subpanel inspection:

1. **Executive Dashboard (`Home::Dashlets`)**
   - Displays real-time KPI dashlets for Active Pipeline (`$`), Probability-Weighted Forecast (`$`), Closed Won Revenue, Active Inbound Leads, and Open Support Cases.
   - Renders interactive Chart.js visualizations for **Pipeline by Sales Stage ($)** and **Leads & Contacts by Acquisition Source**.
   - Lists top open deals and upcoming planned activities with one-click Bean inspection.

2. **[Accounts](https://docs.suitecrm.com/user/sales-relationships/accounts/) (`modules/Accounts` — `Account` Bean)**
   - Serves as the central company hub linking related records across the organization.
   - **Fields**: `name`, `account_type` (`Customer`, `Prospect`, `Partner`, `Reseller`, `Investor`), `industry`, `annual_revenue`, `phone_office`, `website`, `billing_address_city`, `assigned_user_name`.
   - **Subpanels**: `Contacts`, `Opportunities`, `Quotes`, `Cases`, and `Activities`.

3. **[Contacts](https://docs.suitecrm.com/user/sales-relationships/contacts/) (`modules/Contacts` — `Contact` Bean)**
   - Tracks qualified individuals associated with an Account.
   - **Fields**: `first_name`, `last_name`, `title`, `account_id` (relational link to `Accounts`), `email1`, `phone_work`, `lead_source`.
   - **Subpanels**: `Opportunities`, `Activities`, and `Cases`.

4. **[Leads](https://docs.suitecrm.com/user/sales-relationships/leads/) (`modules/Leads` — `Lead` Bean)**
   - Captures unqualified inbound prospects from web forms, conferences, or referrals.
   - **1-Click Lead Conversion (`convertLead` / `convert_lead`)**: Atomically converts a Lead into a linked **Account**, **Contact**, and **Opportunity** (initialized at `Qualification` / `25%` probability) and marks the Lead status as `Converted`.

5. **[Opportunities](https://docs.suitecrm.com/user/sales-relationships/opportunities/) (`modules/Opportunities` — `Opportunity` Bean)**
   - Manages revenue deals across six standard sales stages: `Prospecting` (10%), `Qualification` (25%), `Proposal/Price Quote` (65%), `Negotiation/Review` (80%), `Closed Won` (100%), and `Closed Lost` (0%).
   - Includes both a **Kanban Pipeline Board** (with one-click `Advance Stage →` buttons) and a **List View**.

6. **[Quotes (AOS)](https://docs.suitecrm.com/user/sales-relationships/quotes-invoices-contracts/) (`modules/AOS_Quotes` — `AOS_Quotes` Bean)**
   - Models SuiteCRM's Advanced OpenSales quoting module.
   - Automatically calculates `discount_amount`, `tax_amount`, and `total_amount` from `subtotal_amount`, `discount_percent`, and `tax_percent` during the `before_save` hook.

7. **Support Cases (`modules/Cases` — `aCase` Bean) & Activities (`modules/Activities` — `Task` Bean)**
   - Tracks customer issues by priority (`P1 - Critical` through `P4 - Low`), status, and resolution notes.
   - Connects unified `Call`, `Meeting`, and `Task` activities to any parent SugarBean record (`parent_type` + `parent_id`).

## 3. Advanced OpenWorkflow (AOW) & Logic Hooks

SuiteCRM for Mac implements four automated [Logic Hooks](https://docs.suitecrm.com/developer/core-framework/logic-hooks/) that can be toggled live in the **AOW Workflows & Hooks** view:

| Rule ID | Trigger Hook | Target Module | Automated Behavior |
| :--- | :--- | :--- | :--- |
| **AOW Rule 1** | `before_save` | `Opportunities` | Synchronizes `probability` (%) automatically whenever `sales_stage` is set or updated. |
| **AOW Rule 2** | `before_save` | `Quotes` | Computes `discount_amount`, `tax_amount`, and `total_amount` from subtotal, discount %, and tax %. |
| **AOW Rule 3** | `after_save` | `Cases` | Automatically creates an urgent escalation `Task` in `Activities` when a new `P1 - Critical` Case is saved. |
| **AOW Rule 4** | `after_save` | `Opportunities` | Schedules a `Customer Onboarding Kickoff` meeting under the parent Account when a deal reaches `Closed Won`. |

## 4. Repository Structure & macOS Build Instructions

The `suitecrm_mac_desktop.zip` package contains the complete source tree ready for macOS compilation and GitHub hosting:

- `suitecrm_mac.html` — Self-contained interactive macOS CRM application (HTML5, Tailwind CSS, Chart.js, SugarBean JS ORM, and 8 built-in self-tests).
- `MacApp.swift` — Native macOS AppKit & `WKWebView` wrapper with transparent vibrancy titlebar and standard window controls.
- `sugarbean_engine.py` — Python 3 + SQLite3 implementation of the SugarBean ORM, `load_relationship` resolver, Lead conversion, and AOW hooks.
- `test_suitecrm_mac.py` — Automated `unittest` suite verifying all 7 backend SQLite CRM workflows.
- `SUITECRM_MAC_DOCUMENTATION.md` & `README.md` — Full technical and user documentation.
- `publish_to_github.sh` — Helper shell script to initialize, commit, and push the repository to GitHub (`https://github.com/NerdNinjaAliaz/suitecrm-mac`).

### Compiling the Native macOS App (`SuiteCRM-Mac`)

Run the following command in Terminal on macOS (requires Xcode Command Line Tools):

```bash
unzip suitecrm_mac_desktop.zip
cd suitecrm_mac_desktop
swiftc MacApp.swift -framework Cocoa -framework WebKit -o SuiteCRM-Mac
./SuiteCRM-Mac
```

### Running the Automated Verification Suites

1. **Python SQLite SugarBean Test Suite** (7 unit & integration tests):
   ```bash
   python3 test_suitecrm_mac.py
   ```
2. **In-App JavaScript Self-Test Suite** (8 end-to-end assertions):
   Click **Run Tests** in the top-right toolbar of the app (or open **Test Suite & Audit Log** in the left sidebar) to run all 8 assertions and inspect the real-time LogicHook execution log.

## 5. Keyboard Shortcuts & Quick Actions

- **Spotlight Search (`⌘K` or `Ctrl+K`)**: Focuses the global search bar to filter across all SugarBeans (`Accounts`, `Contacts`, `Leads`, `Opportunities`, `Quotes`, `Cases`, `Activities`).
- **Close Active Modal (`Esc`)**: Dismisses the Create/Edit SugarBean modal or clears active search.
- **Export Database (`↓` Toolbar Icon)**: Exports the entire in-memory SugarBean database to `suitecrm_mac_beans_export.json`.
- **Reset Seed Data (`↻` Toolbar Icon)**: Restores the factory enterprise seed dataset.
