# Optional Inventory addon

- Package: `businesstogo_inventory`, version `19.0.1.0.0`; depends on `businesstogo_connector` and `stock`. The base discovery addon remains unchanged and has no stock dependency.
- Install only after testing on a disposable Odoo 19 database. Copy `businesstogo_inventory/` alongside the existing connector in the custom addons path, restart Odoo, refresh the Apps list, remove the Apps filter and install **businessToGo Inventory**. No new groups, ACL grants, tables or automatic user assignments are added.
- Callers must be ordinary internal users assigned Connector Access, with their own existing stock-model access and allowed companies. There is no `sudo()` for receipt operations. Standard JSON-2 authentication and errors apply.

## Endpoints

- `POST /json/2/businesstogo.receipts/receipt`: `{"receipt_id": 42}` → receipt snapshot; completed/cancelled receipts return `{"id":42,"state":"done"}` or `"cancel"` for reconciliation after unknown outcomes.
- `POST /json/2/businesstogo.receipts/save`: `{"receipt_id":42,"expected_revision":"<snapshot revision>","quantities":[{"id":7,"quantity":2}]}` → new snapshot. Supply every active move exactly once. Saves received counts and picked flags, never demand or validation.
- `POST /json/2/businesstogo.receipts/validate`: `{"receipt_id":42,"expected_revision":"<saved revision>"}` → `{"id":42,"state":"done"}` only after normal Odoo validation reaches Done. This call never writes received quantities.
- Snapshots contain `id`, `reference`, `supplier`, `source`, `destination`, opaque `revision`, and `lines` (`id` = stock move ID, `name`, `barcode`, integer `expected`, integer `quantity`). Unpicked reservation quantities are represented as zero received, not as confirmed counts.
- Only open incoming receipts in Assigned/Confirmed state are editable. Full saved demand is required for validation. Unit products only (`uom.product_uom_unit`), untracked storable products, positive whole demand up to 1,000,000 per line, up to 200 moves, no over-receipts, duplicate nonempty barcodes, returns, scrap, multiple detailed lines, package/owner/lot details or differing detail locations. Unsupported receipts must be completed in Odoo.

## Transactions and concurrency

- Each mutation checks connector membership, read/write access and allowed company, then locks the picking, moves and detail rows in stable ID order before comparing an opaque snapshot hash. The hash includes quantities, picked flags, demand, detail identities/write dates and relevant picking/product metadata; an outdated client cannot silently overwrite a changed receipt.
- Uses Odoo's standard transaction and serialization-retry handling. No commit or mutation retry occurs inside the addon. Separate request revisions stop a retried old request after a conflicting update. Multi-connection race behavior still needs real PostgreSQL/Odoo integration testing.
- Only language, timezone and allowed-company context are retained. Caller flags cannot bypass stock validation, backorder or sanity checks. A wizard/non-Done result raises a user error, rolling back that entire validation request; use Odoo for those workflows.
- After an unknown network outcome, reload authoritative state before retrying. Save and Validate are deliberately separate transactions; a successful save remains even if later validation fails.

## Verification and deployment handoff

- `python3 scripts/check.py`: syntax, packaging, pure count/revision contract and isolated save/validate orchestration tests; these do not prove ORM behavior, ACLs or SQL locking.
- Rollback-isolated real ORM scenarios: `businesstogo_inventory/tests/test_receipts.py`, through its test driver. Run on a disposable database with `odoo -d businesstogo_inventory_test --addons-path=<standard addons>,<this repo> -i businesstogo_inventory --test-enable --test-tags /businesstogo_inventory --stop-after-init --http-port=8079`. For an installed test addon use `-u` instead of `-i`; check both exit status and test summary.
- ORM scenarios and live mutations have **not run**. Manual deployment is owned by the user. Authenticated read-only inspection of `odoo.manuelselch.de` confirmed Odoo 19 field/filter contracts and base Connector v2; the inventory endpoint currently returns 404 because this addon is not installed. No existing business receipt was saved or validated.
- After deployment, verify receipt read, partial Save (state still open, stock not booked), reopen saved counts, full Save then separate Validate, and stale snapshot rejection using only disposable test receipts. Also exercise denied users, record rules, multiple companies, wizard rollback and concurrent database connections before production use.
