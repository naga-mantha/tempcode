Layout App Documentation

Overview

- Purpose: Define, render, and manage page layouts composed of reusable Blocks (e.g., TableBlock, ChartBlock). Users can create layouts, add blocks, control order and width, and apply layout-wide filters that propagate into every block instance.
- Tech: Django app with templates (Bootstrap grid), forms, and views. Integrates with apps.blocks (registry, block models and filter mixins).

Key Concepts

- Layout: A named dashboard owned by a user, optionally public. Identified by user + slug. Contains many LayoutBlocks.
- LayoutBlock: A placement of a Block within a Layout. Ordered linearly (position); rendered in a single Bootstrap row with col-XX widths (Bootstrap handles wrapping).
- LayoutFilterConfig: Saved filter presets at the layout level for a user. Has the same default/constraints semantics as table filters.

Models (apps/layout/models.py)

- Layout
  - Fields: name, slug (auto from name), user (owner), visibility (private/public).
  - Constraints: unique (user, name), unique (user, slug).
  - save(): derives slug from name.

- LayoutBlock
  - Fields: layout (FK), block (FK to apps.blocks.models.Block), position (int, absolute order), base `col` (int, Bootstrap span: 1,2,3,4,6,12; default 12), optional responsive overrides: `col_sm`, `col_md`, `col_lg`, `col_xl`, `col_xxl`.
  - Meta: ordering by (position, id).
  - Notes: We removed row/width/height; wrapping handled by Bootstrap.
  - Responsive cols: When a breakpoint value is set, we emit `col-{breakpoint}-{n}` (e.g., `col-sm-6`, `col-xxl-4`) in addition to the base `col-{col}`. If left blank, it inherits from the next smaller breakpoint.

- LayoutFilterConfig
  - Fields: layout (FK), user (FK), name (str), values (JSON), is_default (bool).
  - Constraints: unique (layout, user, name); plus a conditional unique constraint enforcing a single default per (layout, user).
  - save(): wrapped in a transaction — if first for (layout,user) becomes default; when marked default, unsets others atomically; if it is the only config, it remains default (cannot unset when only one exists).
  - delete(): wrapped in a transaction — prevents deleting last config; if deleting a default, promotes another to default atomically.
  - Auto-creation of "None":
    - On Layout creation, a per-owner default filter named "None" with empty values is created (signals).

Forms (apps/layout/forms.py)

- LayoutForm: Create layout (fields: name, visibility; visibility hidden for non-staff).
- AddBlockForm: Add block to layout (field: `block` only). All widths default to inherit (base remains 12 by default). User adjusts widths later on the edit table.
- LayoutBlockForm: Edit responsive widths (fields: `col_sm`, `col_md`, `col_lg`, `col_xl`, `col_xxl`). Base `col` remains at its model value and is not edited in the UI.
- LayoutFilterConfigForm: Manage layout filter presets (fields: name, is_default). Filter values are collected from request via FilterResolutionMixin helpers.

Views (apps/layout/views.py)

- LayoutListView
  - GET: Lists user’s private layouts and all public layouts. Provides inline LayoutForm to create a new layout.
  - POST: Creates layout from the inline form; redirects to the new layout.

- LayoutDetailView
  - URL: /layouts/<username>/<slug>/
  - Assembles a combined filter schema by aggregating get_filter_schema() from all blocks in the layout and resolving displayable choices via FilterResolutionMixin.
  - Determines active layout filter config from `?filter_config_id=` or defaults to the saved default.
  - Collects live overrides from `filters.*` query params and merges them with the active saved values into `selected_filter_values`.
  - Renders blocks in order of `position` using a single `<div class="row">`; each has `class="col-{{ col }}"` to leverage Bootstrap wrapping.
  - Filter propagation to blocks:
    - For each block instance (LayoutBlock id = LID, block_name = BNAME), a proxy request is built that injects namespaced GET params for each selected filter: `BNAME__LID__filters.<key>`.
    - Blocks (TableBlock/ChartBlock) read instance-scoped filters and thus all instances receive the layout-level filters automatically.
  - UI:
    - “Layout Filter” dropdown lists saved presets, with default preselected.
    - “Filter Conditions” collapsible renders dynamic filter fields for live overrides (non-persistent) using `components/filter_fields.html`.
    - On dropdown change, clears any `filters.*` overrides so the selected preset populates fields; reloads with `filter_config_id` only.
    - “Manage Filters” goes to filter config page; “Reset” links to the base URL (no query params).
  - Default filters are provided by signals only (no lazy creation in view).

- LayoutEditView
  - URL: /layouts/<username>/<slug>/edit/
  - Combined editor: add blocks and edit/reorder/delete blocks on one page.
  - Add block: top card with a block picker; selecting a block immediately adds it via AJAX and updates the table (no Add button). Appends at `position = max+1`. All responsive cols default to inherit; base remains default 12.
  - Edit block widths: table with one row per block; edit `col_sm`, `col_md`, `col_lg`, `col_xl`, `col_xxl`.
  - Drag/drop ordering: powered by SortableJS. Reordering auto-saves via AJAX to `/reorder/` without a page postback.
  - Delete block: per-row Delete triggers AJAX call and removes the row instantly.

- LayoutDeleteView
  - Confirms and deletes an entire layout. Template: layout_confirm_delete.html.

- LayoutFilterConfigView
  - URL: /layouts/<username>/<slug>/filters/
  - Functionality mirrors table filter config page:
    - Dropdown to choose existing saved filter (via `?id=`) or create new.
    - Create/update form with `name`, `is_default`, dynamic filter fields.
    - Delete button posts with `delete=1` and hidden `id`; view intercepts delete before form validation.
  - Uses the aggregated filter schema from all blocks; values are collected via FilterResolutionMixin.

URLs (apps/layout/urls.py)

- GET /layouts/ → `layout_list`
- POST /layouts/ → create new layout via inline form
- GET /layouts/<username>/<slug>/ → `layout_detail`
- GET/POST /layouts/<username>/<slug>/edit/ → `layout_edit`
- POST /layouts/<username>/<slug>/delete/ → `layout_delete`
 - GET/POST /layouts/<username>/<slug>/filters/ → `layout_filter_config`
  - POST /layouts/<username>/<slug>/reorder/ → `layout_reorder` (AJAX endpoint to persist block order)
  - POST /layouts/<username>/<slug>/block/<id>/update/ → `layout_block_update` (AJAX update of responsive widths)
  - POST /layouts/<username>/<slug>/block/<id>/delete/ → `layout_block_delete` (AJAX delete of a block)
  - POST /layouts/<username>/<slug>/block/add/ → `layout_block_add` (AJAX add block and return updated table body)

Templates (apps/layout/templates/layout/)

- layout_list.html: Lists layouts and includes the create form.
- layout_detail.html: Renders layout header, Layout Filter dropdown, live Filter Conditions (collapsible), and block grid.
- layout_edit.html: Combined Add Block card (block picker only, AJAX add) + drag/drop table for ordering and responsive width edits (sm/md/lg/xl/xxl). Displays “auto-saves” for reordering and width changes.
 - _layout_rows.html: Partial used to render the table rows; returned by AJAX add.
- layout_filter_config.html: Saved filters management UI, similar to table filter config.
- layout_confirm_delete.html: Simple delete confirmation.

Admin (apps/layout/admin.py)

- Registers Layout, LayoutBlock, LayoutFilterConfig with concise list displays for basic admin management.

Filter Mechanics

- Schema aggregation: LayoutDetail and LayoutFilterConfig aggregate filters from all blocks by calling each block’s `get_filter_schema()` and merging keys. Choices can be callables and are resolved per-user.
- Saved values: Stored per Layout+User in LayoutFilterConfig.values (JSON). Default selection enforced to be single using model logic similar to BlockFilterConfig.
- Default "None" presets: A saved filter named "None" with empty values is created automatically by signals:
- Layouts: On layout creation — for all users if public; only the owner if private. On new user creation — for all existing public layouts.
- Blocks: On block creation — for all existing users. On new user creation — for all existing blocks.
- Live overrides: Provided via GET under `filters.<key>`; merged with saved values using FilterResolutionMixin._collect_filters.
- Propagation to blocks: For each block, the merged values are namespaced and injected into the block’s GET (`{block_name}__{layout_block_id}__filters.<key>`). Blocks consume these instance-scoped filters and render accordingly.
 - Single-default invariant is enforced at the database level to avoid race conditions under concurrent updates.

Block Integration Details

- Instance namespacing: Blocks are rendered with `instance_id = str(LayoutBlock.id)`. TableBlock/ChartBlock read and write GET params with both block_name and instance_id, preventing collisions when multiple instances of the same block appear.
- Per-instance UI: Table/Chart templates use IDs suffixed by `instance_id` so multiple instances coexist (no duplicate DOM IDs). Column/filter config selectors and Tabulator/Plotly initialization are bound per instance.
- Default "None" block filters:
  - On new user creation, a signal creates a "None" filter (empty values) for every existing block for that user (first marked default).
  - If a user has only one saved block filter for a block, it remains default (cannot unset when only one exists).

Design Decisions

- No row management: Only `position` is used; Bootstrap’s grid wraps `col-XX` items into rows responsively.
- Column control: Users pick from allowed `col` sizes (1,2,3,4,6,12) for consistent grid behavior.
- Merge of pages: Add Block merged into Edit Layout; Create Layout merged into Your Layouts for simpler workflows.
 - Slugs reflect layout names. Renaming a layout updates its slug, changing the URL.

Query Parameters (Layout page)

- `filter_config_id`: Active saved LayoutFilterConfig id.
- `filters.*`: Live overrides (cleared automatically when switching saved filter).
- Per-block (injected): `{block_name}__{layout_block_id}__filters.<key>` used internally to pass layout filters into blocks.

Typical Workflows

- Create a layout: Go to /layouts/, use the Create Layout form. You’re redirected to the layout.
- Add blocks: Open Edit Layout, pick a block from the dropdown; it adds immediately via AJAX. Widths inherit initially; adjust below.
 - Reorder/resize: Drag rows to change order (auto-saves). Changing any width dropdown auto-saves.
- Manage layout filters: Use Layout Filter dropdown to select a preset; expand Filter Conditions to apply live overrides across all blocks; Manage Filters to edit or create presets.
- Reset: Click Reset to clear all query params and return to default view.

Edge Cases and Rules

- LayoutFilterConfig delete is protected when it’s the only config; deleting a default promotes another to default.
- Visibility: Non-staff layouts default to private; staff can set public via form.
- Slug uniqueness: Enforced per user for clarity and stable routing.

Extensibility Notes

- New block types automatically contribute to layout filter schema by implementing `get_filter_schema()`.
- Additional per-block UI can remain independent; layout-level filters will continue to override via the injected GET mechanism.
