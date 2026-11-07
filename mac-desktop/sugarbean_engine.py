#!/usr/bin/env python3
"""SuiteCRM-inspired, standalone SQLite CRM engine (Python standard library).

This is NOT SuiteCRM's PHP SugarBean ORM. It is a small independent engine
with analogous field names, relationships and example automation hooks.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import sqlite3
import uuid
from typing import Any, Iterator

MODULES = ("Accounts", "Contacts", "Leads", "Opportunities", "Quotes", "Cases", "Activities")
STAGE_PROBABILITY_MAP = {
    "Prospecting": 10,
    "Qualification": 25,
    "Proposal/Price Quote": 65,
    "Negotiation/Review": 80,
    "Closed Won": 100,
    "Closed Lost": 0,
}
WORKFLOWS = (
    ("aow-1", "Sync Opportunity stage and probability", "Opportunities", "before_save"),
    ("aow-2", "Calculate quote totals", "Quotes", "before_save"),
    ("aow-3", "Escalate newly created critical cases", "Cases", "after_save"),
    ("aow-4", "Schedule won-deal onboarding", "Opportunities", "after_save"),
)
DEFAULT_DB = Path.home() / "Library" / "Application Support" / "SuiteCRM-for-Mac" / "crm.sqlite3"


def _date() -> str:
    return date.today().isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value if value not in (None, "") else "0")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except (ValueError, ArithmeticError) as exc:
        raise ValueError(f"Invalid money amount: {value!r}") from exc


class SugarBeanSQLiteEngine:
    """CRUD, relationship resolution, conversion, and four configurable hooks.

    A flexible JSON-per-bean schema is intentional: adding Vardef-like custom
    fields does not require SQL migrations. SQLite transactions protect the
    multi-record conversion and post-save automations.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        if self.db_path != ":memory:":
            self.conn.execute("PRAGMA journal_mode=WAL")
        self._transaction_depth = 0
        self._init_schema()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "SugarBeanSQLiteEngine":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        # Nested API calls use savepoints, so convert_lead is all-or-nothing.
        depth = self._transaction_depth
        savepoint = f"crm_sp_{depth}"
        if depth == 0:
            self.conn.execute("BEGIN IMMEDIATE")
        else:
            self.conn.execute(f"SAVEPOINT {savepoint}")
        self._transaction_depth += 1
        try:
            yield
        except BaseException:
            if depth == 0:
                self.conn.execute("ROLLBACK")
            else:
                self.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self.conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        else:
            if depth == 0:
                self.conn.execute("COMMIT")
            else:
                self.conn.execute(f"RELEASE SAVEPOINT {savepoint}")
        finally:
            self._transaction_depth -= 1

    def _init_schema(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS beans (
                module TEXT NOT NULL,
                id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (module, id)
            );
            CREATE INDEX IF NOT EXISTS idx_beans_module_date ON beans(module, updated_at);
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                module TEXT NOT NULL,
                hook TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                fired_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                hook TEXT NOT NULL,
                module TEXT NOT NULL,
                summary TEXT NOT NULL
            );
        """)
        for wid, name, module, hook in WORKFLOWS:
            self.conn.execute(
                "INSERT OR IGNORE INTO workflows(id,name,module,hook,active) VALUES(?,?,?,?,1)",
                (wid, name, module, hook),
            )

    def _check_module(self, module: str) -> None:
        if module not in MODULES:
            raise ValueError(f"Unknown CRM module {module!r}; use one of {', '.join(MODULES)}")

    def get_bean(self, module: str, bean_id: str) -> dict[str, Any] | None:
        self._check_module(module)
        row = self.conn.execute(
            "SELECT data FROM beans WHERE module=? AND id=?", (module, bean_id)
        ).fetchone()
        return json.loads(row["data"]) if row else None

    def get_beans(self, module: str) -> list[dict[str, Any]]:
        self._check_module(module)
        rows = self.conn.execute(
            "SELECT data FROM beans WHERE module=? ORDER BY updated_at DESC, id DESC", (module,)
        )
        return [json.loads(row["data"]) for row in rows]

    def _active(self, rule: str) -> bool:
        row = self.conn.execute("SELECT active FROM workflows WHERE id=?", (rule,)).fetchone()
        return bool(row and row["active"])

    def _fire(self, rule: str, module: str, hook: str, summary: str) -> None:
        self.conn.execute("UPDATE workflows SET fired_count=fired_count+1 WHERE id=?", (rule,))
        self.log_hook(hook, module, summary)

    def log_hook(self, hook: str, module: str, summary: str) -> None:
        self.conn.execute(
            "INSERT INTO audit_log(timestamp,hook,module,summary) VALUES(?,?,?,?)",
            (_timestamp(), hook, module, summary),
        )

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT timestamp,hook,module,summary FROM audit_log ORDER BY id DESC LIMIT ?",
            (max(0, limit),),
        )
        return [dict(row) for row in rows]

    def get_workflows(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM workflows ORDER BY id")]

    def set_workflow_active(self, rule: str, active: bool) -> None:
        if not any(rule == wid for wid, *_ in WORKFLOWS):
            raise ValueError(f"Unknown workflow {rule!r}")
        with self.transaction():
            self.conn.execute("UPDATE workflows SET active=? WHERE id=?", (int(active), rule))
            self.log_hook("workflow_toggle", "System", f"{rule} {'enabled' if active else 'disabled'}")

    def save_bean(self, module: str, values: dict[str, Any]) -> dict[str, Any]:
        self._check_module(module)
        if not isinstance(values, dict):
            raise TypeError("Bean values must be a dictionary")
        with self.transaction():
            requested_id = str(values["id"]) if values.get("id") else None
            previous = self.get_bean(module, requested_id) if requested_id else None
            new = previous is None
            if requested_id and new:
                # Support importing existing IDs, but do not silently overwrite other beans.
                bean_id = requested_id
            else:
                bean_id = requested_id or f"{module[:3].lower()}-{uuid.uuid4().hex[:12]}"
            bean = {**(previous or {}), **values, "id": bean_id}
            bean.setdefault("created_at", _date())
            bean["updated_at"] = _timestamp()

            if module == "Opportunities":
                bean["amount"] = float(_money(bean.get("amount", 0)))
                if self._active("aow-1") and bean.get("sales_stage") in STAGE_PROBABILITY_MAP:
                    bean["probability"] = STAGE_PROBABILITY_MAP[bean["sales_stage"]]
                    self._fire("aow-1", module, "before_save", f"Probability set to {bean['probability']}%")
                else:
                    bean["probability"] = float(bean.get("probability") or 0)
            elif module == "Quotes":
                if not bean.get("quote_number"):
                    bean["quote_number"] = f"AOS-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
                if self._active("aow-2"):
                    subtotal = _money(bean.get("subtotal_amount", 0))
                    discount_pct = min(Decimal("100"), max(Decimal("0"), Decimal(str(bean.get("discount_percent") or 0))))
                    tax_pct = max(Decimal("0"), Decimal(str(bean.get("tax_percent") or 0)))
                    discount = _money(subtotal * discount_pct / 100)
                    taxable = subtotal - discount
                    tax = _money(taxable * tax_pct / 100)
                    bean.update(
                        subtotal_amount=float(subtotal),
                        discount_percent=float(discount_pct),
                        tax_percent=float(tax_pct),
                        discount_amount=float(discount),
                        tax_amount=float(tax),
                        total_amount=float(taxable + tax),
                    )
                    self._fire("aow-2", module, "before_save", f"Quote total = {bean['total_amount']:.2f}")
            elif module == "Cases":
                bean.setdefault("case_number", f"CASE-{uuid.uuid4().hex[:8].upper()}")
            elif module == "Accounts":
                bean["annual_revenue"] = float(_money(bean.get("annual_revenue", 0)))
            elif module == "Leads":
                bean["estimated_value"] = float(_money(bean.get("estimated_value", 0)))

            self.conn.execute(
                """INSERT INTO beans(module,id,data,created_at,updated_at)
                   VALUES(?,?,?,?,?) ON CONFLICT(module,id) DO UPDATE SET
                   data=excluded.data, updated_at=excluded.updated_at""",
                (module, bean_id, json.dumps(bean, ensure_ascii=False), bean["created_at"], bean["updated_at"]),
            )
            self.log_hook("after_save", module, f"{'Created' if new else 'Updated'} {bean_id}")

            if module == "Cases" and new and bean.get("priority") == "P1 - Critical" and self._active("aow-3"):
                self.save_bean("Activities", {
                    "name": f"[Auto-Escalation] Resolve P1 Case: {bean.get('name','')}",
                    "activity_type": "Task", "status": "Planned",
                    "parent_type": "Cases", "parent_id": bean_id,
                    "assigned_user_name": "Incident Response Team", "date_due": _date(),
                })
                self._fire("aow-3", module, "after_save", f"Created escalation task for {bean_id}")

            became_won = module == "Opportunities" and bean.get("sales_stage") == "Closed Won" and (
                new or not previous or previous.get("sales_stage") != "Closed Won"
            )
            if became_won and self._active("aow-4") and bean.get("account_id"):
                existing = any(
                    act.get("origin_opportunity_id") == bean_id
                    for act in self.get_beans("Activities")
                )
                if not existing:
                    self.save_bean("Activities", {
                        "name": f"Customer Onboarding Kickoff: {bean.get('name','')}",
                        "activity_type": "Meeting", "status": "Planned",
                        "parent_type": "Accounts", "parent_id": bean["account_id"],
                        "origin_opportunity_id": bean_id,
                        "assigned_user_name": bean.get("assigned_user_name", ""), "date_due": _date(),
                    })
                    self._fire("aow-4", module, "after_save", f"Scheduled onboarding for {bean_id}")
            return bean

    def delete_bean(self, module: str, bean_id: str) -> bool:
        self._check_module(module)
        with self.transaction():
            cur = self.conn.execute("DELETE FROM beans WHERE module=? AND id=?", (module, bean_id))
            if cur.rowcount:
                self.log_hook("after_delete", module, f"Deleted {bean_id}")
            return cur.rowcount > 0

    def get_related_beans(self, parent_module: str, parent_id: str, target_module: str) -> list[dict[str, Any]]:
        self._check_module(parent_module)
        self._check_module(target_module)
        if target_module == "Activities":
            if parent_module == "Accounts":
                return [a for a in self.get_beans("Activities") if a.get("parent_type") == "Accounts" and a.get("parent_id") == parent_id]
            if parent_module == "Contacts":
                c = self.get_bean("Contacts", parent_id)
                return [a for a in self.get_beans("Activities") if (a.get("parent_type"), a.get("parent_id")) in (("Contacts", parent_id), ("Accounts", (c or {}).get("account_id")))]
            return [a for a in self.get_beans("Activities") if a.get("parent_type") == parent_module and a.get("parent_id") == parent_id]
        if parent_module == "Accounts" and target_module in ("Contacts", "Opportunities", "Quotes", "Cases"):
            return [b for b in self.get_beans(target_module) if b.get("account_id") == parent_id]
        if parent_module == "Opportunities" and target_module == "Quotes":
            return [b for b in self.get_beans("Quotes") if b.get("opportunity_id") == parent_id]
        if parent_module == "Contacts" and target_module in ("Cases", "Opportunities"):
            contact = self.get_bean("Contacts", parent_id)
            return [b for b in self.get_beans(target_module) if contact and contact.get("account_id") and b.get("account_id") == contact["account_id"]]
        return []

    # Compatibility alias resembling SuiteCRM's bean relationship convention.
    load_relationship = get_related_beans

    def convert_lead(self, lead_id: str) -> dict[str, dict[str, Any]]:
        with self.transaction():
            lead = self.get_bean("Leads", lead_id)
            if not lead:
                raise ValueError(f"Lead {lead_id!r} does not exist")
            if lead.get("status") == "Converted" or lead.get("converted"):
                raise ValueError("Lead was already converted; refusing duplicate conversion")
            company = str(lead.get("account_name") or f"{lead.get('first_name','')} {lead.get('last_name','')}").strip()
            account = next((a for a in self.get_beans("Accounts") if a.get("name", "").casefold() == company.casefold()), None)
            if not account:
                account = self.save_bean("Accounts", {
                    "name": company, "account_type": "Prospect", "phone_office": lead.get("phone_work", "")
                })
            contact = self.save_bean("Contacts", {
                "first_name": lead.get("first_name", ""), "last_name": lead.get("last_name", ""),
                "account_id": account["id"], "title": lead.get("title", ""),
                "email1": lead.get("email1", ""), "phone_work": lead.get("phone_work", ""),
                "lead_source": lead.get("lead_source", ""),
            })
            opportunity = self.save_bean("Opportunities", {
                "name": f"{company} — New Opportunity", "account_id": account["id"],
                "sales_stage": "Qualification", "amount": lead.get("estimated_value", 0),
                "probability": 25,
            })
            converted = self.save_bean("Leads", {
                **lead, "status": "Converted", "converted": True,
                "converted_account_id": account["id"],
                "converted_contact_id": contact["id"],
                "converted_opportunity_id": opportunity["id"],
            })
            self.log_hook("after_relationship_add", "Leads", f"Converted {lead_id} into {account['id']} / {contact['id']} / {opportunity['id']}")
            return {"lead": converted, "account": account, "contact": contact, "opportunity": opportunity}

    def summary(self) -> dict[str, Any]:
        opps = self.get_beans("Opportunities")
        open_opps = [o for o in opps if o.get("sales_stage") not in ("Closed Won", "Closed Lost")]
        return {
            "counts": {m: len(self.get_beans(m)) for m in MODULES},
            "active_pipeline": round(sum(float(o.get("amount") or 0) for o in open_opps), 2),
            "weighted_forecast": round(sum(float(o.get("amount") or 0) * float(o.get("probability") or 0) / 100 for o in open_opps), 2),
            "closed_won_revenue": round(sum(float(o.get("amount") or 0) for o in opps if o.get("sales_stage") == "Closed Won"), 2),
            "open_cases": sum(c.get("status") not in ("Resolved", "Closed") for c in self.get_beans("Cases")),
        }

    def export_json(self, path: str | Path) -> None:
        data = {module: self.get_beans(module) for module in MODULES}
        data["Workflows"] = self.get_workflows()
        data["AuditLog"] = self.get_audit_log(limit=10000)
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def import_json(self, path: str | Path) -> dict[str, int]:
        """Import JSON exported by the HTML app, preserving record IDs.

        This is a one-time import, NOT a live synchronized database. Import
        uses saved values rather than firing automations that might duplicate
        tasks/onboarding when migrating existing records.
        """
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Expected a JSON object indexed by module")
        counts: dict[str, int] = {}
        with self.transaction():
            for module in MODULES:
                records = raw.get(module, [])
                if not isinstance(records, list):
                    raise ValueError(f"{module} must be an array")
                counts[module] = 0
                for b in records:
                    if not isinstance(b, dict) or not b.get("id"):
                        raise ValueError(f"{module} contains record without ID")
                    v = dict(b)
                    v.setdefault("created_at", _date())
                    v.setdefault("updated_at", _timestamp())
                    self.conn.execute(
                        """INSERT INTO beans(module,id,data,created_at,updated_at)
                           VALUES(?,?,?,?,?) ON CONFLICT(module,id) DO UPDATE SET
                           data=excluded.data, updated_at=excluded.updated_at""",
                        (module, str(v["id"]), json.dumps(v, ensure_ascii=False), v["created_at"], v["updated_at"]),
                    )
                    counts[module] += 1
            self.log_hook("import", "System", f"Imported {sum(counts.values())} CRM records from {path}")
        return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="SuiteCRM-inspired local SQLite CRM engine")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")
    actions = parser.add_subparsers(dest="command", required=True)
    actions.add_parser("init", help="Create database and workflow tables")
    actions.add_parser("summary", help="Print executive KPIs")
    actions.add_parser("workflows", help="Print workflow settings")
    actions.add_parser("audit", help="Print recent audit events")
    ls = actions.add_parser("list", help="List module records"); ls.add_argument("module", choices=MODULES)
    create = actions.add_parser("create", help="Create a bean using a JSON object"); create.add_argument("module", choices=MODULES); create.add_argument("json", help='e.g. \'{"name":"Acme"}\'')
    conv = actions.add_parser("convert-lead", help="Convert lead into Account, Contact, Opportunity"); conv.add_argument("lead_id")
    export = actions.add_parser("export-json", help="Export database JSON"); export.add_argument("path")
    imp = actions.add_parser("import-json", help="Import HTML app JSON export"); imp.add_argument("path")
    workflow = actions.add_parser("set-workflow", help="Enable or disable AOW rule"); workflow.add_argument("rule", choices=[w[0] for w in WORKFLOWS]); workflow.add_argument("state", choices=["on", "off"])
    args = parser.parse_args()
    with SugarBeanSQLiteEngine(args.db) as engine:
        if args.command == "init":
            output: Any = {"database": engine.db_path, "status": "ready"}
        elif args.command == "summary": output = engine.summary()
        elif args.command == "workflows": output = engine.get_workflows()
        elif args.command == "audit": output = engine.get_audit_log()
        elif args.command == "list": output = engine.get_beans(args.module)
        elif args.command == "create": output = engine.save_bean(args.module, json.loads(args.json))
        elif args.command == "convert-lead": output = engine.convert_lead(args.lead_id)
        elif args.command == "export-json":
            engine.export_json(args.path); output = {"written": args.path}
        elif args.command == "import-json": output = engine.import_json(args.path)
        else:
            engine.set_workflow_active(args.rule, args.state == "on"); output = engine.get_workflows()
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
