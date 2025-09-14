# Auto-Compute, Importers, and Admin Policies

This document explains how auto-computed fields, importer options, and admin settings work together in the `apps/common` app. It covers what each mechanism is for, how they interact, and when to use them.

## Concepts and Responsibilities

- `AutoComputeMixin` (models)
  - Purpose: Declare which fields can be auto-computed and how to compute them.
  - Key API: add an `AUTO_COMPUTE` mapping and implement compute methods.
  - Default behavior: `save()` computes "all" fields in `AUTO_COMPUTE` unless a caller passes `recalc`/`recalc_exclude` to override.

- `recalc` / `recalc_exclude` (runtime policy)
  - Purpose: Choose which auto-computed fields to recalculate on a specific `save()` call.
  - Usage: Pass to `save(recalc=..., recalc_exclude=...)` from admin, importers, or any code path that persists a model.

- Importers (management commands)
  - Purpose: Load data from files and apply targeted recomputation, avoiding unwanted overwrites of file‑sourced values.
  - Strategy: Use `method="save_per_instance"` so model `save()` is called, and pass `recalc` so only the necessary computed fields are refreshed.

- Admin policy toggle (`PURCHASE_ADMIN_SKIP_BACK_ORDER_RECALC`)
  - Purpose: Prevent the admin UI from recomputing certain fields (e.g., `back_order`) when saving objects, if you want to respect values coming from batch imports.
  - Implemented by `BaseAutoComputeAdmin` subclass overrides that add items to `recalc_exclude` based on the setting.

## Model Declaration: `AUTO_COMPUTE`

Declare on the model which fields are computable and which method returns the value. For example, `PurchaseOrderLine`:

```python
# apps/common/models/purchase_order_lines.py
class PurchaseOrderLine(AutoComputeMixin, WorkflowModelMixin):
    ...
    def compute_final_receive_date(self):
        return self.modified_receive_date or self.supplier_confirmed_date or self.initial_receive_date

    def compute_back_order(self):
        total = self.total_quantity or 0
        received = self.received_quantity or 0
        return total - received

    def compute_amount_home_currency(self):
        # Converts amount_original_currency to home currency using FX
        ...

    AUTO_COMPUTE = {
        "final_receive_date": "compute_final_receive_date",
        "back_order": "compute_back_order",
        "amount_home_currency": "compute_amount_home_currency",
    }
```

Notes:
- The mixin computes values just before saving. Callers can opt out or limit this via `recalc`/`recalc_exclude`.
- Keep compute methods side‑effect free and fast; they should only return a value.

## Runtime Controls: `recalc` and `recalc_exclude`

Accepted values for `recalc`:
- `"all"` (default): compute all fields listed in `AUTO_COMPUTE`.
- `"none"`: compute nothing.
- `{\"field1\", \"field2\"}`: compute only the listed subset.

`recalc_exclude` is a set of fields to remove from the computed set, after the above selection. Example:

```python
obj.save(recalc={"final_receive_date", "amount_home_currency"}, recalc_exclude={"amount_home_currency"})
```

The example computes only `final_receive_date`.

## Importer Workflows and Policies

The text importer (`apps/common/importers/text.py`) supports two modes:
- `method="bulk_create"`: fast upsert (no `save()`), with conflict handling. Use when no per‑row computation is required.
- `method="save_per_instance"`: calls `save()` per row so `AutoComputeMixin` runs. Use when you need computed fields.

Additional options used in our commands:
- `recalc`, `recalc_exclude`, `recalc_always_save`: control which computed fields to update, even when no direct field changed.
- `override_fields`: force specific field values on imported rows (e.g., `status="open"`).
- `relation_override_fields`: apply overrides when creating missing related objects (e.g., set a newly created `po_line.status="closed"`).

### Purchase Order Lines: `create_purchase_order_lines`

- File: `apps/common/management/commands/create_purchase_order_lines.py`
- Behavior:
  - Close all existing lines upfront (`status="closed"`).
  - Import snapshot with `method="save_per_instance"`.
  - `override_fields={"status": "open"}` for rows present in the file.
  - `recalc={"final_receive_date", "amount_home_currency"}` to refresh only those computed fields while respecting file‑sourced `back_order`.

### Purchase Orders: `create_purchase_orders`

- File: `apps/common/management/commands/create_purchase_orders.py`
- Behavior:
  - `method="save_per_instance"`.
  - `recalc={"category"}` so `PurchaseOrder._compute_category()` assigns a category from the order prefix.

### Receipt Lines: `create_receipts_lines`

- File: `apps/common/management/commands/create_receipts_lines.py`
- Behavior:
  - `method="save_per_instance"`.
  - File columns supply `amount_home_currency`; we do not compute it in the model here.
  - `recalc={"days_offset", "classification"}` so the model computes timing and classification.
  - `relation_override_fields={"po_line": {"status": "closed"}}` so missing `PurchaseOrderLine` rows created during import are marked closed.

## Admin Behavior and Global Toggle

- Base admin: `apps/common/admin_mixins.py::BaseAutoComputeAdmin` forwards `recalc` policy to `save()`.
- `PurchaseOrderLineAdmin.get_auto_compute_save_kwargs` consults `settings.PURCHASE_ADMIN_SKIP_BACK_ORDER_RECALC`:
  - When `True`, adds `"back_order"` to `recalc_exclude` for admin saves, avoiding recomputing that field.
  - When `False` (default), admin saves compute the default set (`"all"`) unless the admin class sets a different policy.

## When To Use Each

- Use `AUTO_COMPUTE` to declare what can be computed, once per model.
- Use `recalc`/`recalc_exclude` at call sites to tailor which computed fields are refreshed for that operation:
  - Importers: specify only what depends on the imported columns to avoid overriding file values.
  - Admin: follow your UX policy (e.g., skip back‑order recompute if administrators are merely fixing metadata).
  - Batch fixes/scripts: pass `recalc="all"` to fully refresh computed fields after a data change.

## Practical Examples

- Fully recompute on an object:

```python
pol.save(recalc="all")
```

- Compute only `final_receive_date` and skip `back_order`:

```python
pol.save(recalc={"final_receive_date"}, recalc_exclude={"back_order"})
```

- Import snapshot and force an override:

```python
result = import_rows_from_text(
    model="common.PurchaseOrderLine",
    ...,
    method="save_per_instance",
    recalc={"final_receive_date", "amount_home_currency"},
    override_fields={"status": "open"},
)
```

- Create missing related object with an override on creation:

```python
result = import_rows_from_text(
    model="common.ReceiptLine",
    ...,
    method="save_per_instance",
    relation_override_fields={"po_line": {"status": "closed"}},
)
```

## Notes

- For `bulk_create` with unique constraints and no updatable fields, the importer automatically falls back to `ignore_conflicts=True` to avoid errors.
- Computed fields should be deterministic from the instance fields and safe to run multiple times.
