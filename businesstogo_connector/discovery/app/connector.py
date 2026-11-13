from odoo import api, models
from odoo.exceptions import AccessError, MissingError, ValidationError

from ..domain.action_contract import action_descriptor, menu_descriptors
from ..domain.action_contract import menu_id as validate_menu_id


class BusinessToGoConnector(models.AbstractModel):
    _name = "businesstogo.connector"
    _description = "businessToGo Connector"

    @api.model
    def capabilities(self):
        self._require_connector_user()
        return {
            "api_version": 1,
            "addon_version": "19.0.1.0.0",
            "odoo_major": 19,
            "capabilities": ["menu_discovery", "window_action_resolution"],
            "action_types": ["ir.actions.act_window"],
        }

    @api.model
    def list_menus(self):
        self._require_connector_user()
        tree, allowed = self._discovery()
        return menu_descriptors(tree, allowed)

    @api.model
    def resolve_action(self, menu_id):
        self._require_connector_user()
        try:
            requested_id = validate_menu_id(menu_id)
        except ValueError as error:
            raise ValidationError(str(error)) from error

        tree, allowed = self._discovery()
        if requested_id not in allowed:
            raise AccessError(self.env._("Menu action is unavailable."))

        # The ID comes from the caller's visible, reachable menu tree, never
        # from an arbitrary action ID supplied by the client.
        node = tree[requested_id]
        action = self.env["ir.actions.act_window"].browse(node["action_id"]).sudo()
        if not self._action_is_allowed(action):
            raise AccessError(self.env._("Menu action is unavailable."))

        values = action.read([
            "name", "res_model", "res_id", "views", "domain", "context",
            "search_view_id", "target", "limit",
        ])[0]
        if values["res_id"]:
            # This check MUST run in the original, non-sudo environment.
            record = self.env[values["res_model"]].browse(values["res_id"])
            if not record.exists():
                raise AccessError(self.env._("Menu action is unavailable."))
            record.check_access("read")
        return action_descriptor(values)

    @api.model
    def _require_connector_user(self):
        user = self.env.user
        if user.share or not user.has_group("base.group_user") or not user.has_group(
            "businesstogo_connector.group_connector_user"
        ):
            raise AccessError(self.env._("businessToGo Connector access is required."))

    @api.model
    def _discovery(self):
        # Odoo filters group visibility, model access, blacklist and ancestry.
        # load_menus may consult an HTTP session's debug state internally.
        # Intersect with explicit non-debug visibility and stop at hidden
        # ancestors rather than trusting a debug-enabled/cached input tree.
        menus = self.env["ir.ui.menu"]
        tree = menus.load_menus(False)
        visible_ids = menus._visible_menu_ids(debug=False)
        allowed = set()
        reachable = list(tree["root"]["children"])
        while reachable:
            node_id = reachable.pop()
            if node_id not in visible_ids:
                continue
            node = tree[node_id]
            reachable.extend(node["children"])
            if node["action_model"] != "ir.actions.act_window":
                continue
            action = self.env["ir.actions.act_window"].browse(node["action_id"]).sudo()
            if self._action_is_allowed(action):
                allowed.add(node_id)
        return tree, allowed

    @api.model
    def _action_is_allowed(self, action):
        # sudo is limited to reading the nominated action's definition/groups.
        # It is never used for model or business-record permission checks.
        if not action.exists():
            return False
        if action.group_ids and not (
            set(action.group_ids.ids) & set(self.env.user._get_group_ids())
        ):
            return False
        if action.res_model not in self.env:
            return False
        try:
            self.env[action.res_model].check_access("read")
        except (AccessError, MissingError):
            return False
        return True
