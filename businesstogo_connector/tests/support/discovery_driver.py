import ast

from odoo import Command
from odoo.exceptions import AccessError, ValidationError


class DiscoveryDriver:
    """Real ORM setup and assertions; no fake permission boundaries."""

    def __init__(self, case):
        self.case = case
        self.env = case.env
        self.group = self.env.ref("businesstogo_connector.group_connector_user")
        internal = self.env.ref("base.group_user")
        self.user = self.env["res.users"].create({
            "name": "Connector ordinary user",
            "login": "businesstogo-test-assigned",
            "group_ids": [Command.set([internal.id, self.group.id])],
        })
        self.unassigned = self.env["res.users"].create({
            "name": "Connector unassigned user",
            "login": "businesstogo-test-unassigned",
            "group_ids": [Command.set([internal.id])],
        })
        self.portal = self.env["res.users"].create({
            "name": "Connector portal user",
            "login": "businesstogo-test-portal",
            "group_ids": [Command.set([
                self.env.ref("base.group_portal").id, self.group.id,
            ])],
        })
        self.root = self.env["ir.ui.menu"].create({"name": "Connector test"})
        self.action = self.env["ir.actions.act_window"].create({
            "name": "Connector Contacts", "res_model": "res.partner",
            "view_mode": "list,form", "context": "{'default_is_company': True}",
            "domain": "[('active', '=', True)]",
        })
        self.menu = self.env["ir.ui.menu"].create({
            "name": "Contacts", "parent_id": self.root.id,
            "action": f"ir.actions.act_window,{self.action.id}",
        })
        self.partner = self.env["res.partner"].create({"name": "Connector test contact"})
        self.api = self.env["businesstogo.connector"].with_user(self.user)
        self.result = None

    def discover(self):
        self.result = self.api.list_menus()

    def openContacts(self):
        self.result = self.api.resolve_action(self.menu.id)

    def shouldDescribeCapabilities(self):
        result = self.api.capabilities()
        self.case.assertEqual(result["api_version"], 2)
        self.case.assertIn("window_action_resolution", result["capabilities"])

    def shouldBeOrdinaryUser(self):
        self.case.assertFalse(self.user.has_group("base.group_system"))
        self.case.assertFalse(self.user.has_group("base.group_erp_manager"))

    def shouldIncludeContactsAndAncestors(self):
        menus = {m["id"]: m for m in self.result}
        self.case.assertIn(self.root.id, menus)
        self.case.assertEqual(menus[self.menu.id]["parent_id"], self.root.id)
        self.case.assertTrue(menus[self.menu.id]["has_action"])

    def shouldPreserveAction(self):
        self.case.assertEqual(self.result["id"], self.action.id)
        self.case.assertEqual(self.result["res_model"], "res.partner")
        self.case.assertEqual(self.result["domain"], self.action.domain)
        self.case.assertEqual(self.result["context"], self.action.context)
        self.case.assertEqual(self.result["views"], [[False, "list"], [False, "form"]])
        self.case.assertNotIn("group_ids", self.result)

    def shouldRejectUnassignedUsers(self):
        api = self.env["businesstogo.connector"].with_user(self.unassigned)
        self._shouldRejectAllMethods(api)

    def shouldRejectPortalEvenWithConnectorGroup(self):
        api = self.env["businesstogo.connector"].with_user(self.portal)
        self._shouldRejectAllMethods(api)

    def _shouldRejectAllMethods(self, api):
        for method, args in (
            (api.capabilities, ()), (api.list_menus, ()),
            (api.resolve_action, (self.menu.id,)),
        ):
            with self.case.assertRaises(AccessError):
                method(*args)

    def restrictActionToAdministrators(self):
        self.action.group_ids = [Command.set([self.env.ref("base.group_system").id])]

    def restrictFolderToAdministrators(self):
        self.root.group_ids = [Command.set([self.env.ref("base.group_system").id])]

    def restrictFolderToTechnicalMode(self):
        self.root.group_ids = [Command.set([self.env.ref("base.group_no_one").id])]

    def removeModelReadPermission(self):
        self.action.res_model = "ir.config_parameter"

    def archiveMenu(self):
        self.menu.active = False

    def useUnsupportedAction(self):
        action = self.env["ir.actions.act_url"].create({
            "name": "Not supported", "url": "https://example.com",
        })
        self.menu.action = f"ir.actions.act_url,{action.id}"

    def shouldHideAndRejectContacts(self):
        self.case.assertNotIn(self.menu.id, [m["id"] for m in self.api.list_menus()])
        with self.case.assertRaises(AccessError):
            self.api.resolve_action(self.menu.id)

    def shouldRejectMissingMenu(self):
        with self.case.assertRaises(AccessError):
            self.api.resolve_action(2147483647)

    def shouldRejectInvalidMenuIdentifiers(self):
        for value in (True, 0, -1, "1", 1.5, None, []):
            with self.case.assertRaises(ValidationError):
                self.api.resolve_action(value)

    def shouldRejectFolderAsAction(self):
        with self.case.assertRaises(AccessError):
            self.api.resolve_action(self.root.id)

    def shouldNotGrantTechnicalModelAccess(self):
        for model, ids in (
            ("ir.actions.act_window", [self.action.id]),
            ("ir.config_parameter", []),
        ):
            with self.case.assertRaises(AccessError):
                self.env[model].with_user(self.user).browse(ids).check_access("read")

    def shouldNotChangePermissionsOnDiscovery(self):
        before = set(self.user.group_ids.ids)
        self.api.list_menus()
        self.api.resolve_action(self.menu.id)
        self.case.assertEqual(set(self.user.group_ids.ids), before)

    def targetUnreadableRecord(self):
        self.action.res_id = self.partner.id
        self.env["ir.rule"].create({
            "name": "Connector test blocked record",
            "model_id": self.env["ir.model"]._get_id("res.partner"),
            "domain_force": f"[('id', '!=', {self.partner.id})]",
        })

    def shouldRejectUnreadableTargetRecord(self):
        with self.case.assertRaises(AccessError):
            self.api.resolve_action(self.menu.id)

    def shouldLoadResolvedViewsAndRecordPage(self):
        descriptor = self.api.resolve_action(self.menu.id)
        model = self.env[descriptor["res_model"]].with_user(self.user)
        context = dict(self.env.context)
        context.update(ast.literal_eval(descriptor["context"]))
        domain = ast.literal_eval(descriptor["domain"])
        model = model.with_context(context)
        views = model.get_views(descriptor["views"], options={"action_id": descriptor["id"]})
        self.case.assertIn("list", views["views"])
        self.case.assertIn("form", views["views"])
        self.case.assertTrue(views["models"]["res.partner"]["fields"])
        records = model.search_read(
            domain + [("id", "=", self.partner.id)], ["id", "display_name"], limit=10, order="id",
        )
        self.case.assertEqual(len(records), 1)
        self.case.assertEqual(records[0]["id"], self.partner.id)
