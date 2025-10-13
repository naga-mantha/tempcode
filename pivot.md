# Pivot Block Notes

## 1. New Files to Create
- `apps_v2/blocks/tables` equivalent for pivots, e.g. `apps_v2/blocks/pivots/my_pivot.py` defining the `BlockSpec`, service wiring, and optional demo view.
- Service implementations tailored for pivots under `apps_v2/blocks/services`, e.g. `pivot_table.py` containing `PivotQueryBuilder`, `PivotSerializer`, and any pivot-specific resolver.
- Templates: `templates/v2/blocks/pivot/pivot.html` (wrapper) and supporting partials (filter panel, config drawers) if they differ from the table layout.
- Frontend bundle: a new JS module (likely `apps/common/src/js/v2-pivot-filters.js` and compiled static copy) to initialize the pivot library, handle filter submissions, and integrate with saved configs.
- URL registration: add demo routes in `apps_v2/blocks/urls.py` and optional dedicated view functions.
- Tests/documentation: new documentation section in `v2.md` or a dedicated `pivot.md` (this file) plus unit tests covering service behavior.

## 2. Files/Components to Reuse
- Core registry infrastructure (`BlockSpec`, `Services`, `register`, `load_specs`).
- Policy facade (`apps_v2/policy/service.py`).
- Saved-config helpers (`apps_v2/blocks/configs.py`) for filter presets, assuming pivots share the same models.
- Filter schema parsing (`SchemaFilterResolver`, `prune_filter_values`) if pivot filters behave like table filters.
- Frontend filter submission helper (`v2-table-filters.js`) for saved-filter metadata; can be reused or adapted with minimal changes.
- Export pipeline: `DefaultExportOptions` and `export_spec` endpoint can be extended to support pivot outputs.
- Layout chrome (once consolidated) and saved filter templates in `apps/common/templates/v2/blocks/filter/`.

## 3. Out-of-the-box Features
- Saved filter presets (private/public) with clear/override support thanks to shared helpers.
- Filter layout customization (accordion sections, user/admin layouts) if the pivot uses the same filter templates.
- Download options (CSV/XLSX/PDF stubs) leveraging the existing export view.
- Policy-aware field pruning provided by the shared service base classes.
- HTMX partial rendering and Tabulator-like bootstrapping once a pivot-specific frontend is supplied.

## Notes
- Table-specific code (Tabulator options, column reorder support) must be abstracted or copied for pivot semantics.
- A pivot block likely needs aggregation logic and a dedicated serializer; these will live alongside the table equivalents in `apps_v2/blocks/services`.
- Once the shared block chrome is implemented (per R&D plan), pivot blocks will automatically inherit consistent headers and saved-config controls.
