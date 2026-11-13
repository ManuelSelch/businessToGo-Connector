# Installation and verification

## Install on self-hosted Odoo 19

1. Back up your database. First evaluate on staging.
2. Copy the entire `businesstogo_connector` directory to a configured custom
   addons path, preserving its directory name.
3. Restart Odoo, update the Apps list in developer mode, remove the default
   **Apps** filter and install **businessToGo Connector**.
4. Edit the intended internal user under **Settings → Users & Companies → Users**.
   Enable **businessToGo / Connector: Access** and save.
5. Retain the user's ordinary business permissions. Do not add Settings,
   Access Rights administration or broad technical-model ACLs.

The addon adds no custom screens or business app launcher. Its ERP icon
appears with its module entry. Installation does not assign users or change
existing business-model permissions. To revoke connector discovery access,
remove the user's connector group. Standard Odoo API access remains unchanged.

For upgrades, deploy the new addon files, restart Odoo and upgrade
`businesstogo_connector`. Review security changes before each upgrade.

## Local checks (no Odoo installation)

```sh
python3 scripts/check.py
```

The same command is declared in `.pi/pipeline.yaml` and GitHub Actions.
It checks package metadata, XML, imports by syntax parsing, icon integrity,
pure response contracts and isolated adapter behavior. Mocked checks do not
prove Odoo permissions or HTTP behavior.

## Real Odoo integration tests (not yet run)

Run only against a disposable Odoo 19 test database with this repository in
the addons path. The tests create users, menus, actions, a record rule and
contacts in rollback-isolated transactions. Never run them on production.

For a fresh disposable test database:

```sh
odoo -d businesstogo_connector_test \
  --addons-path=/path/to/odoo/addons,/path/to/businessToGo-Connector \
  -i businesstogo_connector --test-enable \
  --test-tags /businesstogo_connector --stop-after-init --http-port=8079
```

For an existing disposable database where the addon is installed, replace
`-i` with `-u`. Adapt the executable, database authentication and addons paths
to your installation. Check the process exit status AND Odoo's test summary.

Scenarios live in `businesstogo_connector/tests/test_discovery.py`; their driver
uses the real ORM, not fake permission checks. They cover assigned/non-admin,
unassigned and portal users; hidden ancestors; restricted actions; missing,
inactive and unsupported menus; model access; record rules; and resolved
views/record loading.

## Manual JSON-2 acceptance

Use an API key belonging to the assigned non-admin user. Follow
[the API contract](api.md): capabilities → menus → resolve a Contacts menu →
resolved list/form views → a limited record page. Repeat connector requests
with an unassigned user and attempt a hidden menu ID; both must fail.

No Docker/module installation, Odoo integration tests or installed-addon
HTTP acceptance check was performed during initial development.
