# Architecture and security

## Responsibility

`businesstogo_connector` is a technical Odoo 19 addon. It registers the
stateless abstract model `businesstogo.connector`; it creates no business
tables, screens, controller routes or business-record proxy endpoints.

The discovery slice owns:

- `discovery/app/connector.py`: group gates, Odoo visibility/access checks,
  bounded action-definition reads and public model methods.
- `discovery/domain/action_contract.py`: pure menu-tree projection, input
  validation and the allowlisted action response.

The mobile app owns navigation state, XML interpretation and native rendering.
Resolved views and business records are requested directly from standard Odoo
methods under the user's existing permissions. The ERP app is not wired to the
connector in this repository.

## Access flow

All three public methods require both internal-user status and the dedicated
`businesstogo_connector.group_connector_user` group. Portal/public users are
rejected even if someone assigns the connector group to them.

Discovery uses Odoo's non-debug `ir.ui.menu.load_menus(False)` tree. This
includes Odoo's menu-group, model-access, blacklist and reachable-ancestry
filtering. The connector further checks each supported window action's groups
(including implied membership) and the target model's read access. Unsupported
action menus and empty folder branches are omitted.

Resolution accepts a **menu ID**, not an arbitrary action ID. It repeats the
visibility and action checks before returning the definition. A direct-record
action additionally requires read access to that existing record, including
record rules, in the original user environment.

## Elevated-read boundary

The only explicit `sudo()` is for reading the specific window-action record
referenced by a visible menu. It permits action-group inspection and the
allowlisted response fields without granting general technical-model read ACLs.
There is no elevated business-record or resolved-view access.

Menu visibility and target-model access are necessary but do not grant access
to every record. Standard record rules and field permissions continue to apply
to subsequent view/data requests. Connector membership does not add business
permissions and is not a restriction on standard APIs users already have.

## Contracts and limitations

- Discovery supports window actions only; it does not execute actions,
  server code, reports, client actions or URL actions.
- Action domain/context expressions are returned unchanged; they are not
  evaluated or rewritten by the connector. A client must interpret the
  supported expressions correctly or explicitly reject them.
- IDs are database-local. Preserve returned action view order and explicit
  view IDs when calling `get_views`.
- Responses are computed per caller; the connector maintains no shared
  elevated-user cache. Odoo owns its standard menu cache invalidation.
- Module installation/updates manage group definitions; there is no
  client-side admin provisioning or automatic assignment to current/future users.

## Verification boundaries

Local tests validate pure contracts and adapter orchestration using fake Odoo
objects. They cannot establish real ACL, record-rule, cache or JSON-2 behavior.
The addon also includes real ORM scenarios in `businesstogo_connector/tests/`.
No installation or Odoo integration test has been performed during initial
development, at the user's request.

The module icon is a byte-for-byte copy of businessToGo ERP's
`Assets.xcassets/AppIcon.appiconset/AppIcon.png`.
