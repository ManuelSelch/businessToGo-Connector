import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "action_contract", ROOT / "businesstogo_connector/discovery/domain/action_contract.py"
)
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class ActionContractTests(unittest.TestCase):
    def test_accepts_only_positive_integer_menu_ids(self):
        self.assertEqual(contract.menu_id(12), 12)
        for value in (True, False, 0, -1, "12", 1.2, None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                contract.menu_id(value)

    def test_projects_only_supported_action_fields(self):
        action = {
            "id": 7, "name": "Contacts", "res_model": "res.partner",
            "views": [(False, "list"), (42, "form")],
            "domain": "[('active', '=', True)]",
            "context": "{'default_is_company': True}",
            "res_id": 0, "search_view_id": (9, "Search"), "limit": 80,
            "target": "current", "help": "<p>private</p>",
            "group_ids": [1], "unexpected_secret": "hidden",
        }
        result = contract.action_descriptor(action)
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["views"], [[False, "list"], [42, "form"]])
        self.assertEqual(result["domain"], action["domain"])
        self.assertEqual(result["context"], action["context"])
        self.assertEqual(result["search_view_id"], 9)
        self.assertEqual(result["res_id"], False)
        self.assertNotIn("help", result)
        self.assertNotIn("group_ids", result)
        self.assertNotIn("unexpected_secret", result)

    def test_preserves_false_search_view_and_record_identity(self):
        result = contract.action_descriptor({
            "id": 7, "name": "Record", "res_model": "res.partner",
            "views": [(False, "form")], "res_id": 15,
            "domain": False, "context": "{}", "search_view_id": False,
            "target": "new", "limit": 80,
        })
        self.assertEqual(result["res_id"], 15)
        self.assertIs(result["search_view_id"], False)
        self.assertIs(result["domain"], False)
        self.assertEqual(result["target"], "new")

    def test_keeps_only_supported_branches_in_original_order(self):
        tree = {
            1: {"id": 1, "name": "App", "children": [3, 2]},
            2: {"id": 2, "name": "Allowed", "children": []},
            3: {"id": 3, "name": "Denied", "children": []},
            4: {"id": 4, "name": "Orphan", "children": []},
            "root": {"children": [1]},
        }
        menus = contract.menu_descriptors(tree, {2})
        self.assertEqual([m["id"] for m in menus], [1, 2])
        self.assertEqual(menus[0]["children"], [2])
        self.assertEqual(menus[1]["parent_id"], 1)
        self.assertTrue(menus[1]["has_action"])
        self.assertFalse(menus[0]["has_action"])

    def test_empty_or_unreachable_actions_do_not_leak(self):
        tree = {"root": {"children": []}, 2: {"id": 2, "name": "Hidden", "children": []}}
        self.assertEqual(contract.menu_descriptors(tree, {2}), [])
        self.assertEqual(contract.menu_descriptors({"root": {"children": []}}, set()), [])

    def test_does_not_mutate_odoo_cached_menu_tree(self):
        tree = {"root": {"children": [1]}, 1: {"id": 1, "name": "App", "children": [2]},
                2: {"id": 2, "name": "Contacts", "children": []}}
        result = contract.menu_descriptors(tree, {2})
        result[0]["children"].clear()
        self.assertEqual(tree[1]["children"], [2])


if __name__ == "__main__":
    unittest.main()
