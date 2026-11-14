import ast
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "businesstogo_inventory/receipts/domain/contract.py"
spec = importlib.util.spec_from_file_location("receipt_contract", PATH)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class ReceiptContractTests(unittest.TestCase):
    def setUp(self):
        self.lines = [{"id": 1, "expected": 3}, {"id": 2, "expected": 2}]

    def test_partial_and_zero_counts_can_be_saved(self):
        self.assertEqual(contract.counts(self.lines, [{"id": 1, "quantity": 2}, {"id": 2, "quantity": 0}]), {1: 2, 2: 0})

    def test_incomplete_duplicate_unknown_and_invalid_counts_fail(self):
        for values in [[], [{"id": 1, "quantity": 2}] * 2,
                       [{"id": 9, "quantity": 1}, {"id": 2, "quantity": 0}]]:
            with self.assertRaises(ValueError):
                contract.counts(self.lines, values)
        for count in [True, -1, 4, 1.5, "2", None]:
            with self.assertRaises(ValueError):
                contract.counts(self.lines, [{"id": 1, "quantity": count}, {"id": 2, "quantity": 0}])

    def test_revision_changes_for_detail_and_quantity_changes(self):
        baseline = contract.revision([42, [1, 0, False]])
        self.assertEqual(baseline, contract.revision([42, [1, 0, False]]))
        self.assertNotEqual(baseline, contract.revision([42, [1, 1, True]]))

    def test_optional_package_depends_on_stock_without_changing_base(self):
        addon = PATH.parents[2]
        manifest = ast.literal_eval((addon / "__manifest__.py").read_text())
        self.assertEqual(manifest["depends"], ["businesstogo_connector", "stock"])
        self.assertFalse(manifest["auto_install"])
        self.assertIn("test_receipts", (addon / "tests/__init__.py").read_text())

    def test_ids_reject_boolean_and_nonpositive(self):
        for value in [True, 0, -1, "42"]:
            with self.assertRaises(ValueError):
                contract.positive_id(value)
