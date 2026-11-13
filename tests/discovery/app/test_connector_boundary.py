"""Isolated adapter tests. These do NOT verify Odoo ORM or JSON-2 security."""
import importlib
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))


class AccessError(Exception):
    pass


class MissingError(Exception):
    pass


class ValidationError(Exception):
    pass


odoo = types.ModuleType("odoo")
odoo.api = types.SimpleNamespace(model=lambda method: method)
odoo.models = types.SimpleNamespace(AbstractModel=object)
exceptions = types.ModuleType("odoo.exceptions")
exceptions.AccessError = AccessError
exceptions.MissingError = MissingError
exceptions.ValidationError = ValidationError
with patch.dict(sys.modules, {"odoo": odoo, "odoo.exceptions": exceptions}):
    Connector = importlib.import_module(
        "businesstogo_connector.discovery.app.connector"
    ).BusinessToGoConnector


class ConnectorBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.api = Connector()
        self.env = MagicMock()
        self.api.env = self.env
        self.env._.side_effect = lambda value: value
        self.env.user.share = False
        self.env.user.has_group.return_value = True
        self.env.user._get_group_ids.return_value = {1, 2}
        self.env.__contains__.side_effect = lambda model: model == "res.partner"
        self.menu_model = MagicMock()
        self.action_model = MagicMock()
        self.business_model = MagicMock()
        self.env.__getitem__.side_effect = {
            "ir.ui.menu": self.menu_model,
            "ir.actions.act_window": self.action_model,
            "res.partner": self.business_model,
        }.__getitem__
        self.action = MagicMock()
        self.action.sudo.return_value = self.action
        self.action.exists.return_value = True
        self.action.group_ids = []
        self.action.res_model = "res.partner"
        self.action_model.browse.return_value = self.action
        self.values = {
            "id": 7, "name": "Contacts", "res_model": "res.partner",
            "res_id": False, "views": [(False, "list"), (False, "form")],
            "domain": False, "context": "{}", "search_view_id": False,
            "target": "current", "limit": 80,
        }
        self.action.read.return_value = [self.values]
        self.tree = {
            "root": {"children": [1]},
            1: {"id": 1, "name": "App", "children": [2],
                "action_model": False, "action_id": False},
            2: {"id": 2, "name": "Contacts", "children": [],
                "action_model": "ir.actions.act_window", "action_id": 7},
            99: {"id": 99, "name": "Unreachable", "children": [],
                 "action_model": "ir.actions.act_window", "action_id": 100},
        }
        for key, node in self.tree.items():
            if key != "root":
                node.update(xmlid=f"example.menu_{key}", web_icon_data=False)
        self.menu_model.load_menus.return_value = self.tree
        self.menu_model._visible_menu_ids.return_value = {1, 2}

    def test_denies_every_public_method_before_metadata_access(self):
        self.env.user.has_group.return_value = False
        for method, args in ((self.api.capabilities, ()), (self.api.list_menus, ()),
                             (self.api.resolve_action, (2,))):
            with self.assertRaises(AccessError):
                method(*args)
        self.menu_model.load_menus.assert_not_called()
        self.action_model.browse.assert_not_called()

    def test_portal_is_denied_even_if_group_membership_is_present(self):
        self.env.user.share = True
        with self.assertRaises(AccessError):
            self.api.capabilities()

    def test_capabilities_are_explicit_and_do_not_read_metadata(self):
        self.assertEqual(self.api.capabilities()["api_version"], 2)
        self.action_model.browse.assert_not_called()

    def test_discovery_uses_non_debug_visible_tree_and_checks_model_without_sudo(self):
        result = self.api.list_menus()
        self.assertEqual([m["id"] for m in result], [1, 2])
        self.menu_model.load_menus.assert_called_once_with(False)
        self.business_model.check_access.assert_called_with("read")
        self.business_model.sudo.assert_not_called()
        self.action_model.browse.assert_called_once_with(7)

    def test_debug_session_cannot_expose_non_debug_hidden_ancestry(self):
        self.menu_model._visible_menu_ids.return_value = {2}
        self.assertEqual(self.api.list_menus(), [])
        with self.assertRaises(AccessError):
            self.api.resolve_action(2)
        self.menu_model._visible_menu_ids.assert_called_with(debug=False)
        self.action_model.browse.assert_not_called()

    def test_group_restricted_action_is_hidden_and_direct_open_is_denied(self):
        self.action.group_ids = types.SimpleNamespace(ids=[9])
        self.assertEqual(self.api.list_menus(), [])
        with self.assertRaises(AccessError):
            self.api.resolve_action(2)
        self.action.read.assert_not_called()

    def test_model_access_denial_hides_action_and_rejects_direct_open(self):
        self.business_model.check_access.side_effect = AccessError()
        self.assertEqual(self.api.list_menus(), [])
        with self.assertRaises(AccessError):
            self.api.resolve_action(2)
        self.action.read.assert_not_called()

    def test_missing_action_is_denied(self):
        self.action.exists.return_value = False
        with self.assertRaises(AccessError):
            self.api.resolve_action(2)

    def test_unknown_target_model_is_denied(self):
        self.action.res_model = "unknown.model"
        self.assertEqual(self.api.list_menus(), [])

    def test_unreachable_menu_and_folder_are_denied(self):
        for value in (99, 1, 999):
            with self.assertRaises(AccessError):
                self.api.resolve_action(value)
        self.action.read.assert_not_called()

    def test_invalid_identifier_is_rejected_before_discovery(self):
        for value in (True, 0, -1, "2", None):
            with self.assertRaises(ValidationError):
                self.api.resolve_action(value)
        self.menu_model.load_menus.assert_not_called()

    def test_supported_action_descriptor_uses_allowlisted_metadata(self):
        result = self.api.resolve_action(2)
        self.assertEqual(result["id"], 7)
        self.assertEqual(result["views"], [[False, "list"], [False, "form"]])
        requested = self.action.read.call_args.args[0]
        self.assertNotIn("help", requested)
        self.assertNotIn("group_ids", requested)

    def test_target_record_is_checked_without_elevating_business_model(self):
        self.values["res_id"] = 15
        record = self.business_model.browse.return_value
        record.exists.return_value = True
        record.check_access.side_effect = AccessError()
        with self.assertRaises(AccessError):
            self.api.resolve_action(2)
        self.business_model.browse.assert_called_once_with(15)
        record.check_access.assert_called_once_with("read")
        self.business_model.sudo.assert_not_called()
        record.sudo.assert_not_called()

    def test_missing_target_record_is_denied(self):
        self.values["res_id"] = 15
        self.business_model.browse.return_value.exists.return_value = False
        with self.assertRaises(AccessError):
            self.api.resolve_action(2)

    def test_unsupported_action_is_hidden(self):
        self.tree[2]["action_model"] = "ir.actions.server"
        self.assertEqual(self.api.list_menus(), [])
        with self.assertRaises(AccessError):
            self.api.resolve_action(2)
        self.action_model.browse.assert_not_called()
