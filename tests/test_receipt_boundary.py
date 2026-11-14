import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1] / "businesstogo_inventory/receipts"


class Rejected(Exception):
    pass


def load_adapter():
    odoo = types.ModuleType("odoo")
    odoo.api = types.SimpleNamespace(model=lambda fn: fn)
    odoo.models = types.SimpleNamespace(AbstractModel=object)
    errors = types.ModuleType("odoo.exceptions")
    errors.AccessError = errors.UserError = errors.ValidationError = Rejected
    domain = types.ModuleType("receipt_test.domain")
    spec = importlib.util.spec_from_file_location("receipt_test.domain.contract", ROOT / "domain/contract.py")
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    with patch.dict(sys.modules, {"odoo": odoo, "odoo.exceptions": errors,
                                 "receipt_test.domain": domain, "receipt_test.domain.contract": contract}):
        spec = importlib.util.spec_from_file_location("receipt_test.app.receipts", ROOT / "app/receipts.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module.BusinessToGoReceipts


Adapter = load_adapter()


class ReceiptBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.api = Adapter()
        self.writes = []
        self.validations = []
        self.snapshot = {"revision": "r1", "lines": [{"id": 1, "expected": 3, "quantity": 2}]}
        self.move = types.SimpleNamespace(id=1, write=self.writes.append)
        self.picking = types.SimpleNamespace(id=42, ids=[42], state="assigned")
        self.picking.move_ids = types.SimpleNamespace(filtered=lambda fn: [self.move])
        self.picking.with_context = lambda **context: self.picking
        self.picking.button_validate = self.validate
        self.api.env = types.SimpleNamespace(flush_all=lambda: None, invalidate_all=lambda: None)
        self.api._safe_context = lambda: self.api
        self.api._locked = lambda receipt_id: self.picking
        self.api._snapshot = lambda picking: self.snapshot

    def validate(self):
        self.validations.append(True)
        self.picking.state = "done"
        return True

    def test_save_updates_quantity_and_picked_without_validating_or_changing_demand(self):
        result = self.api.save(42, "r1", [{"id": 1, "quantity": 2}])
        self.assertEqual(self.writes, [{"quantity": 2, "picked": True}])
        self.assertEqual(self.validations, [])
        self.assertEqual(result, self.snapshot)

    def test_stale_revision_prevents_all_mutations(self):
        with self.assertRaises(Rejected):
            self.api.save(42, "old", [{"id": 1, "quantity": 2}])
        self.assertEqual(self.writes, [])

    def test_partial_validation_never_calls_odoo_validation(self):
        with self.assertRaises(Rejected):
            self.api.validate(42, "r1")
        self.assertEqual(self.validations, [])

    def test_full_saved_receipt_validates_without_rewriting_quantities(self):
        self.snapshot["lines"][0]["quantity"] = 3
        self.assertEqual(self.api.validate(42, "r1"), {"id": 42, "state": "done"})
        self.assertEqual(self.writes, [])
        self.assertEqual(self.validations, [True])

    def test_wizard_is_rejected_so_odoo_transaction_can_roll_back(self):
        self.snapshot["lines"][0]["quantity"] = 3
        self.picking.button_validate = lambda: {"res_model": "stock.backorder.confirmation"}
        with self.assertRaises(Rejected):
            self.api.validate(42, "r1")
