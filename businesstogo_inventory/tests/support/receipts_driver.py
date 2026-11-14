from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError


class ReceiptsDriver:
    def __init__(self, case):
        self.case = case
        self.env = case.env
        self.user = self.env["res.users"].create({
            "name": "Receipt tester", "login": "businesstogo-receipt-tester",
            "group_ids": [Command.set([self.env.ref("base.group_user").id,
                self.env.ref("stock.group_stock_user").id,
                self.env.ref("businesstogo_connector.group_connector_user").id])],
        })
        self.product = self.env["product.product"].create({
            "name": "Disposable receipt test", "is_storable": True, "type": "consu",
            "uom_id": self.env.ref("uom.product_uom_unit").id,
        })
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        self.picking = self.env["stock.picking"].create({
            "picking_type_id": warehouse.in_type_id.id,
            "location_id": self.env.ref("stock.stock_location_suppliers").id,
            "location_dest_id": warehouse.lot_stock_id.id,
            "move_ids": [Command.create({"product_id": self.product.id,
                "product_uom_qty": 3, "product_uom": self.product.uom_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": warehouse.lot_stock_id.id})],
        })
        self.picking.action_confirm()
        self.api = self.env["businesstogo.receipts"].with_user(self.user)
        self.original = self.api.receipt(self.picking.id)
        self.current = self.original

    def save(self, quantity):
        self.current = self.api.save(self.picking.id, self.current["revision"],
            [{"id": self.picking.move_ids.id, "quantity": quantity}])

    def validate(self):
        self.result = self.api.validate(self.picking.id, self.current["revision"])

    def shouldRemainOpenWithCount(self, quantity):
        self.case.assertNotEqual(self.picking.state, "done")
        self.case.assertEqual(self.current["lines"][0]["quantity"], quantity)
        self.case.assertEqual(self.picking.move_ids.product_uom_qty, 3)

    def shouldComplete(self):
        self.case.assertEqual(self.result, {"id": self.picking.id, "state": "done"})
        self.case.assertEqual(self.picking.state, "done")

    def shouldRejectStaleSave(self):
        with self.case.assertRaises(ValidationError), self.env.cr.savepoint():
            self.api.save(self.picking.id, self.original["revision"],
                [{"id": self.picking.move_ids.id, "quantity": 1}])

    def shouldRejectPartialValidation(self):
        with self.case.assertRaises(ValidationError), self.env.cr.savepoint():
            self.api.validate(self.picking.id, self.current["revision"])

    def shouldRejectUnassignedUser(self):
        self.user.group_ids -= self.env.ref("businesstogo_connector.group_connector_user")
        with self.case.assertRaises(AccessError):
            self.api.receipt(self.picking.id)

    def shouldRejectTrackedProduct(self):
        self.product.tracking = "lot"
        with self.case.assertRaises(UserError):
            self.api.receipt(self.picking.id)

    def shouldIgnoreValidationBypassContext(self):
        self.api = self.api.with_context(skip_sanity_check=True, skip_backorder=True,
            button_validate_picking_ids=[999999])
        self.shouldRejectPartialValidation()
