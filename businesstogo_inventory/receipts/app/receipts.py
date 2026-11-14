from odoo import api, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..domain.contract import counts, positive_id, revision


class BusinessToGoReceipts(models.AbstractModel):
    _name = "businesstogo.receipts"
    _description = "businessToGo receipt operations"

    @api.model
    def receipt(self, receipt_id):
        self = self._safe_context()
        picking = self._picking(receipt_id)
        if picking.state in ("done", "cancel"):
            return {"id": picking.id, "state": picking.state}
        return self._snapshot(picking)

    @api.model
    def save(self, receipt_id, expected_revision, quantities):
        self = self._safe_context()
        picking = self._locked(receipt_id)
        snapshot = self._snapshot(picking)
        self._check_revision(snapshot, expected_revision)
        try:
            values = counts(snapshot["lines"], quantities)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        for move in picking.move_ids.filtered(lambda move: move.state != "cancel"):
            # Standard inverse maintains detailed operations. Never change demand.
            move.write({"quantity": values[move.id], "picked": values[move.id] > 0})
        self.env.flush_all()
        self.env.invalidate_all()
        return self._snapshot(picking)

    @api.model
    def validate(self, receipt_id, expected_revision):
        self = self._safe_context()
        picking = self._locked(receipt_id)
        snapshot = self._snapshot(picking)
        self._check_revision(snapshot, expected_revision)
        if not all(line["quantity"] == line["expected"] for line in snapshot["lines"]):
            raise ValidationError("Save all expected quantities before validating.")
        # Do not let hostile client contexts bypass checks or operate on other pickings.
        picking.with_context(
            skip_backorder=False, cancel_backorder=False, skip_sanity_check=False,
            picking_ids_not_to_backorder=[], button_validate_picking_ids=picking.ids,
        ).button_validate()
        self.env.flush_all()
        if picking.state != "done":
            # Raising rolls back any side effects, including transient wizard creation.
            raise UserError("This receipt requires an Odoo confirmation or quality workflow. Complete it in Odoo.")
        return {"id": picking.id, "state": "done"}

    def _safe_context(self):
        return self.with_context({key: value for key, value in self.env.context.items()
                                  if key in ("lang", "tz", "allowed_company_ids")})

    def _picking(self, receipt_id):
        self.env["businesstogo.connector"]._require_connector_user()
        try:
            positive_id(receipt_id)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        picking = self.env["stock.picking"].browse(receipt_id).exists()
        if not picking:
            raise AccessError("Receipt is unavailable.")
        picking.check_access("read")
        if picking.company_id not in self.env.companies or picking.picking_type_code != "incoming":
            raise AccessError("Incoming receipt is unavailable.")
        return picking

    def _locked(self, receipt_id):
        picking = self._picking(receipt_id)
        picking.check_access("write")
        # Lock picking, then moves, then details in stable ID order. Under Odoo's
        # REPEATABLE READ a concurrent committed update causes serialization retry;
        # the retried request compares the original client revision again.
        self.env.flush_all()
        self.env.cr.execute("SELECT id FROM stock_picking WHERE id = %s FOR UPDATE", [picking.id])
        self.env.cr.execute("SELECT id FROM stock_move WHERE picking_id = %s ORDER BY id FOR UPDATE", [picking.id])
        self.env.cr.execute("SELECT id FROM stock_move_line WHERE picking_id = %s ORDER BY id FOR UPDATE", [picking.id])
        self.env.invalidate_all()
        picking = self._picking(receipt_id)
        picking.check_access("write")
        picking.move_ids.check_access("write")
        picking.move_line_ids.check_access("write")
        return picking

    def _check_revision(self, snapshot, expected_revision):
        if not isinstance(expected_revision, str) or snapshot["revision"] != expected_revision:
            raise ValidationError("The receipt changed. Reload before saving or validating.")

    def _snapshot(self, picking):
        if picking.state not in ("assigned", "confirmed"):
            raise UserError("Only open, ready or confirmed incoming receipts are supported.")
        moves = picking.move_ids.filtered(lambda move: move.state != "cancel").sorted("id")
        moves.check_access("read")
        picking.move_line_ids.check_access("read")
        if not moves or len(moves) > 200:
            raise UserError("This receipt is empty or too large for the scanner.")
        lines = []
        fingerprints = []
        for move in moves:
            product = move.product_id
            product.check_access("read")
            if (product.tracking != "none" or not product.is_storable
                    or move.product_uom != product.uom_id
                    or move.product_uom != self.env.ref("uom.product_uom_unit")
                    or move.state not in ("assigned", "confirmed")
                    or move.product_uom_qty <= 0 or move.product_uom_qty > 1000000
                    or not float(move.product_uom_qty).is_integer()
                    or not float(move.quantity).is_integer() or not 0 <= move.quantity <= move.product_uom_qty
                    or len(move.move_line_ids) > 1
                    or move.origin_returned_move_id or move.scrap_id
                    or move.location_id != picking.location_id or move.location_dest_id != picking.location_dest_id):
                raise UserError("Unsupported tracking, unit, quantity or detailed operation. Use Odoo for this receipt.")
            details = []
            for detail in move.move_line_ids:
                if (detail.lot_id or detail.lot_name or detail.package_id or detail.result_package_id or detail.owner_id
                        or detail.product_uom_id != move.product_uom
                        or detail.location_id != move.location_id or detail.location_dest_id != move.location_dest_id):
                    raise UserError("Split locations, packages, owners or tracked products require Odoo.")
                details.append([detail.id, detail.write_date, detail.quantity, detail.picked])
            # Odoo's reserved quantity is not an operator-confirmed received count.
            quantity = int(move.quantity) if move.picked else 0
            lines.append({"id": move.id, "name": product.display_name, "barcode": product.barcode or "",
                          "expected": int(move.product_uom_qty), "quantity": quantity})
            fingerprints.append([move.id, move.write_date, move.quantity, move.picked, move.product_uom_qty,
                                 product.id, product.write_date, product.barcode, details])
        codes = [line["barcode"] for line in lines if line["barcode"]]
        if len(codes) != len(set(codes)):
            raise UserError("Duplicate product barcodes require Odoo.")
        return {
            "id": picking.id, "reference": picking.name, "supplier": picking.partner_id.display_name or "",
            "source": picking.origin or "", "destination": picking.location_dest_id.display_name,
            "lines": lines,
            "revision": revision([picking.id, picking.write_date, picking.state, picking.company_id.id,
                                  picking.location_id.id, picking.location_dest_id.id, fingerprints]),
        }
