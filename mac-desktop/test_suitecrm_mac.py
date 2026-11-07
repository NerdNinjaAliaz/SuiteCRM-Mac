#!/usr/bin/env python3
"""Offline integration tests for the standalone Python/SQLite engine."""
import json
import tempfile
import unittest
from pathlib import Path

from sugarbean_engine import MODULES, SugarBeanSQLiteEngine


class SuiteCRMEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = SugarBeanSQLiteEngine(":memory:")

    def tearDown(self):
        self.engine.close()

    def account(self):
        return self.engine.save_bean("Accounts", {"name": "Sonoma Robotics", "account_type": "Customer"})

    def test_modules_and_workflows(self):
        self.assertEqual(len(MODULES), 7)
        self.assertEqual(len(self.engine.get_workflows()), 4)
        self.assertTrue(all(w["active"] for w in self.engine.get_workflows()))

    def test_account_crud(self):
        account = self.account()
        self.assertEqual(self.engine.get_bean("Accounts", account["id"])["name"], "Sonoma Robotics")
        updated = self.engine.save_bean("Accounts", {"id": account["id"], "name": "New Name"})
        self.assertEqual(updated["name"], "New Name")
        self.assertEqual(len(self.engine.get_beans("Accounts")), 1)
        self.assertTrue(self.engine.delete_bean("Accounts", account["id"]))
        self.assertFalse(self.engine.delete_bean("Accounts", account["id"]))

    def test_opportunity_probability_hook(self):
        opp = self.engine.save_bean("Opportunities", {"name": "Demo", "sales_stage": "Negotiation/Review", "amount": 150000})
        self.assertEqual(opp["probability"], 80)
        self.assertEqual(opp["amount"], 150000.0)

    def test_quote_discount_tax_hook(self):
        q = self.engine.save_bean("Quotes", {
            "name": "Proposal", "subtotal_amount": 100000, "discount_percent": 10, "tax_percent": 8
        })
        self.assertEqual(q["discount_amount"], 10000)
        self.assertEqual(q["tax_amount"], 7200)
        self.assertEqual(q["total_amount"], 97200)
        self.assertIn("AOS-", q["quote_number"])

    def test_critical_case_escalation_once(self):
        case = self.engine.save_bean("Cases", {"name": "Down", "priority": "P1 - Critical"})
        acts = self.engine.get_related_beans("Cases", case["id"], "Activities")
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["activity_type"], "Task")
        self.engine.save_bean("Cases", {"id": case["id"], "name": "Still down"})
        self.assertEqual(len(self.engine.get_related_beans("Cases", case["id"], "Activities")), 1)

    def test_closed_won_onboarding_once(self):
        acc = self.account()
        opp = self.engine.save_bean("Opportunities", {
            "name": "Enterprise", "account_id": acc["id"], "sales_stage": "Proposal/Price Quote", "amount": 3000
        })
        won = self.engine.save_bean("Opportunities", {"id": opp["id"], "sales_stage": "Closed Won"})
        self.assertEqual(won["probability"], 100)
        activities = self.engine.get_related_beans("Accounts", acc["id"], "Activities")
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["origin_opportunity_id"], opp["id"])
        self.engine.save_bean("Opportunities", {"id": opp["id"], "sales_stage": "Closed Won"})
        self.assertEqual(len(self.engine.get_related_beans("Accounts", acc["id"], "Activities")), 1)

    def test_lead_conversion(self):
        lead = self.engine.save_bean("Leads", {
            "first_name": "Jane", "last_name": "Doe", "account_name": "Nimbus Co", "estimated_value": 70000,
            "email1": "jane@example.org"
        })
        data = self.engine.convert_lead(lead["id"])
        self.assertEqual(data["lead"]["status"], "Converted")
        self.assertEqual(data["opportunity"]["sales_stage"], "Qualification")
        self.assertEqual(data["opportunity"]["probability"], 25)
        self.assertEqual(data["contact"]["account_id"], data["account"]["id"])
        with self.assertRaisesRegex(ValueError, "already converted"):
            self.engine.convert_lead(lead["id"])

    def test_account_relationships(self):
        acc = self.account()
        self.engine.save_bean("Contacts", {"first_name": "Sam", "account_id": acc["id"]})
        opp = self.engine.save_bean("Opportunities", {"name": "Order", "account_id": acc["id"], "sales_stage": "Prospecting", "amount": 500})
        self.engine.save_bean("Quotes", {"name": "Quote", "account_id": acc["id"], "opportunity_id": opp["id"], "subtotal_amount": 200})
        self.assertEqual(len(self.engine.load_relationship("Accounts", acc["id"], "Contacts")), 1)
        self.assertEqual(len(self.engine.load_relationship("Accounts", acc["id"], "Opportunities")), 1)
        self.assertEqual(len(self.engine.load_relationship("Accounts", acc["id"], "Quotes")), 1)
        self.assertEqual(len(self.engine.load_relationship("Opportunities", opp["id"], "Quotes")), 1)

    def test_disable_workflow(self):
        self.engine.set_workflow_active("aow-1", False)
        opp = self.engine.save_bean("Opportunities", {
            "name": "Manual probability", "sales_stage": "Closed Won", "amount": 10, "probability": 42
        })
        self.assertEqual(opp["probability"], 42)
        self.assertEqual(next(w for w in self.engine.get_workflows() if w["id"] == "aow-1")["active"], 0)

    def test_summary(self):
        self.engine.save_bean("Opportunities", {"name": "A", "sales_stage": "Qualification", "amount": 100})
        self.engine.save_bean("Opportunities", {"name": "B", "sales_stage": "Closed Won", "amount": 250})
        self.engine.save_bean("Cases", {"name": "Help", "status": "New"})
        kpis = self.engine.summary()
        self.assertEqual(kpis["active_pipeline"], 100)
        self.assertEqual(kpis["weighted_forecast"], 25)
        self.assertEqual(kpis["closed_won_revenue"], 250)
        self.assertEqual(kpis["open_cases"], 1)

    def test_json_export_and_import(self):
        account = self.account()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "backup.json"
            self.engine.export_json(p)
            payload = json.loads(p.read_text())
            self.assertEqual(payload["Accounts"][0]["id"], account["id"])
            with SugarBeanSQLiteEngine(":memory:") as second:
                result = second.import_json(p)
                self.assertEqual(result["Accounts"], 1)
                self.assertEqual(second.get_bean("Accounts", account["id"])["name"], "Sonoma Robotics")

    def test_atomic_import_rollback_on_error(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text(json.dumps({"Accounts": [{"id": "acc-1", "name": "Good"}], "Contacts": [{"first_name": "missing ID"}]}))
            with self.assertRaisesRegex(ValueError, "without ID"):
                self.engine.import_json(p)
            self.assertEqual(self.engine.get_beans("Accounts"), [])

    def test_rounded_money(self):
        q = self.engine.save_bean("Quotes", {"name": "Tiny", "subtotal_amount": "10.01", "discount_percent": "5", "tax_percent": "8.25"})
        self.assertEqual(q["discount_amount"], 0.50)
        self.assertEqual(q["tax_amount"], 0.78)
        self.assertEqual(q["total_amount"], 10.29)


if __name__ == "__main__":
    unittest.main(verbosity=2)
