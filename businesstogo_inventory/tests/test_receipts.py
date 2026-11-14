from odoo.tests import TransactionCase, tagged
from .support.receipts_driver import ReceiptsDriver


@tagged("post_install", "-at_install")
class TestReceipts(TransactionCase):
    def setUp(self):
        super().setUp()
        self.receipts = ReceiptsDriver(self)

    def test_save_partial_then_validate_separately(self):
        self.receipts.save(2)
        self.receipts.shouldRemainOpenWithCount(2)
        self.receipts.shouldRejectPartialValidation()
        self.receipts.shouldRejectStaleSave()

        self.receipts.save(3)
        self.receipts.shouldRemainOpenWithCount(3)
        self.receipts.validate()
        self.receipts.shouldComplete()

    def test_save_zero_preserves_demand(self):
        self.receipts.save(0)
        self.receipts.shouldRemainOpenWithCount(0)

    def test_connector_assignment_is_required(self):
        self.receipts.shouldRejectUnassignedUser()

    def test_tracking_is_unsupported(self):
        self.receipts.shouldRejectTrackedProduct()

    def test_context_cannot_bypass_validation(self):
        self.receipts.shouldIgnoreValidationBypassContext()
