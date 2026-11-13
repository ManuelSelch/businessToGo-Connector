# businessToGo Connector

Odoo server-side integration for the businessToGo app family.

- **Odoo addon display name:** businessToGo Connector
- **Odoo addon technical name:** `businesstogo_connector`
- **Initial target:** self-hosted Odoo 19

## Status

Repository initialized. The addon is not implemented yet.

## Planned first scope

- An integration group explicitly assigned to selected internal users.
- Menu/action discovery that validates the current user's menu visibility, action restrictions and target-model access.
- Narrow action metadata responses without granting broad read access to technical models.
- A capability/version method for installation and feature detection.
- Standard resolved-view and business-record requests under the current user's permissions; no elevated business-record access.

The iOS app remains responsible for generic view parsing and native rendering. The connector may later own additional integration settings and permissions; it should not duplicate Odoo business logic.

## Initial acceptance checks

- An assigned ordinary internal user can navigate Contacts menu → action → resolved list/form views → a limited page of records.
- Unassigned users cannot use connector discovery methods.
- Inaccessible menus/actions are rejected, including requests made directly by ID.
- No administrator rights or broad technical-model ACLs are required for ordinary users.

Installation, configuration and test instructions will be added with the implementation.
