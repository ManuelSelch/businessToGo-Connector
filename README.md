# businessToGo Connector

Odoo server-side integration for the businessToGo app family.

The `businesstogo_connector` addon provides opt-in, access-checked menu and
window-action discovery for ordinary internal users. Native apps remain
responsible for view parsing and rendering.

## Requirements

- Self-hosted **Odoo 19**, with the standard `base` and `web` modules.
- Administrator access for installation and explicit user assignment.
- Existing business-model permissions for each assigned user.

## Install

Copy `businesstogo_connector/` into your custom addons path, restart Odoo,
update the Apps list, remove the **Apps** filter, and install **businessToGo
Connector**. It is a technical addon, not a separate home-screen application.

Under **Settings → Users & Companies → Users**, enable
**businessToGo / Connector: Access** for selected internal users, then save.
No users are assigned automatically, and no technical-model ACLs are added.

The addon uses the same icon as businessToGo ERP.

## Development

```sh
python3 scripts/check.py
```

This runs packaging checks, Python syntax checks and isolated tests without
installing Odoo. Real ORM integration tests are included but require your own
disposable Odoo test database; they are not covered by the isolated checks.

- [Installation and testing](docs/installation.md)
- [JSON-2 API](docs/api.md)
- [Architecture and security](docs/architecture.md)

License: LGPL-3.0-only; see [LICENSE](LICENSE).
