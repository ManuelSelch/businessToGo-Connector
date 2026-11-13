# JSON-2 API, version 1

Use Odoo 19's standard JSON-2 authentication and database selection:

- `Authorization: bearer <user-api-key>`
- `Content-Type: application/json`
- `X-Odoo-Database: <database>` when required by the deployment

All connector methods require an assigned **ordinary internal user**. They
are available as public model methods, not custom HTTP controllers.
Keep keys out of logs, source control and shared screenshots.

## Capabilities

`POST /json/2/businesstogo.connector/capabilities`

Body: `{}`

Response:

```json
{
  "api_version": 1,
  "addon_version": "19.0.1.0.0",
  "odoo_major": 19,
  "capabilities": ["menu_discovery", "window_action_resolution"],
  "action_types": ["ir.actions.act_window"]
}
```

An unavailable model/method means installation or version needs checking.
An access error means the caller is not eligible/assigned; do not request
administrator credentials as a runtime workaround.

## Menus

`POST /json/2/businesstogo.connector/list_menus`

Body: `{}`

Returns an ordered, flat array of supported action menus and their ancestors:

```json
[
  {"id": 134, "name": "Contacts", "parent_id": false, "children": [135], "has_action": false},
  {"id": 135, "name": "Contacts", "parent_id": 134, "children": [], "has_action": true}
]
```

IDs above are illustrative, not stable identifiers. Empty results are successful.
Ordering follows Odoo's visible menu tree. Unsupported action-only branches
are omitted; a folder can remain when it has supported descendants.

## Action resolution

`POST /json/2/businesstogo.connector/resolve_action`

Body: `{"menu_id": 135}`

Returns only:

```json
{
  "id": 182,
  "type": "ir.actions.act_window",
  "name": "Contacts",
  "res_model": "res.partner",
  "res_id": false,
  "views": [[124, "list"], [129, "kanban"], [127, "form"], [false, "activity"]],
  "domain": false,
  "context": "{'default_is_company': True}",
  "search_view_id": 128,
  "target": "current",
  "limit": 80
}
```

The action view list is preserved, including view types the client may not
support. A false view ID requests the model's default view of that type.
Domain/context retain Odoo's expression strings (or false for an unset domain).
Do not convert arbitrary Python expressions with quote replacement.

Non-positive/non-integer menu IDs produce a validation error. Hidden, missing,
unsupported and folder-only menu actions produce access errors. Record-specific
actions are rejected when the record is missing or unreadable. Error bodies
use Odoo's standard JSON-2 format; clients must not expose debug tracebacks.

## Next calls

1. Merge the correctly interpreted action context with the user's context.
2. Request selected action view pairs using
   `POST /json/2/<res_model>/get_views`, with `views`,
   `options: {"action_id": <id>}` and `context`.
3. Use `search_read` with the action domain, selected fields, limit/offset,
   deterministic ordering and context. A `res_id` action instead opens that record.

The connector does not grant extra permissions for these standard methods.
