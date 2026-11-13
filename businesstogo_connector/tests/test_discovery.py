from odoo.tests import TransactionCase, tagged

from .support.discovery_driver import DiscoveryDriver


@tagged("post_install", "-at_install")
class ConnectorDiscoveryTests(TransactionCase):
    def setUp(self):
        super().setUp()
        self.connector = DiscoveryDriver(self)

    def test_ordinary_assigned_user_can_discover_and_open_contacts(self):
        self.connector.shouldBeOrdinaryUser()
        self.connector.shouldDescribeCapabilities()
        self.connector.discover()
        self.connector.shouldIncludeContactsAndAncestors()
        self.connector.openContacts()
        self.connector.shouldPreserveAction()

    def test_unassigned_user_cannot_use_connector(self):
        self.connector.shouldRejectUnassignedUsers()

    def test_portal_user_is_rejected_even_if_assigned(self):
        self.connector.shouldRejectPortalEvenWithConnectorGroup()

    def test_restricted_action_cannot_be_opened_by_guessed_menu_id(self):
        self.connector.restrictActionToAdministrators()
        self.connector.shouldHideAndRejectContacts()

    def test_restricted_ancestor_hides_descendant(self):
        self.connector.restrictFolderToAdministrators()
        self.connector.shouldHideAndRejectContacts()

    def test_technical_only_ancestor_is_hidden(self):
        self.connector.restrictFolderToTechnicalMode()
        self.connector.shouldHideAndRejectContacts()

    def test_model_read_access_is_required(self):
        self.connector.removeModelReadPermission()
        self.connector.shouldHideAndRejectContacts()

    def test_inactive_menu_is_rejected(self):
        self.connector.archiveMenu()
        self.connector.shouldHideAndRejectContacts()

    def test_unsupported_action_is_not_exposed(self):
        self.connector.useUnsupportedAction()
        self.connector.shouldHideAndRejectContacts()

    def test_missing_menu_is_rejected(self):
        self.connector.shouldRejectMissingMenu()

    def test_invalid_menu_identifiers_are_rejected(self):
        self.connector.shouldRejectInvalidMenuIdentifiers()

    def test_folder_cannot_be_opened_as_action(self):
        self.connector.shouldRejectFolderAsAction()

    def test_discovery_does_not_grant_technical_permissions(self):
        self.connector.shouldNotGrantTechnicalModelAccess()
        self.connector.shouldNotChangePermissionsOnDiscovery()

    def test_action_target_record_rules_are_respected(self):
        self.connector.targetUnreadableRecord()
        self.connector.shouldRejectUnreadableTargetRecord()

    def test_resolved_views_and_record_page_use_ordinary_user(self):
        self.connector.shouldLoadResolvedViewsAndRecordPage()
