Layout App Documentation

Overview

- Purpose: Define, render, and manage page layouts composed of reusable Blocks (e.g., TableBlock, ChartBlock). Users can create layouts, add blocks, control order and width, and apply layout-wide filters that propagate into every block instance.
- Tech: Django app with templates (Bootstrap grid), forms, and views. Integrates with apps.blocks (registry, block models and filter mixins).

Key Concepts

- Layout: A named dashboard owned by a user, optionally public. Identified by user + slug. Contains many LayoutBlocks.
- LayoutBlock: A placement of a Block within a Layout. Ordered linearly (position); rendered in a single Bootstrap row with col-XX widths (Bootstrap handles wrapping).
  - Per-instance defaults: Each LayoutBlock can optionally set a default Block filter and a default Block column configuration ("view") by name. This lets duplicate blocks on the same layout start with different saved presets for filters and columns. These defaults resolve against the viewing user’s saved configs.
- LayoutFilterConfig: Saved filter presets at the layout level for a user. Has the same default/constraints semantics as table filters.

Models (apps/layout/models.py)

- Layout
  - Fields: name, slug (auto from name), user (owner), visibility (private/public).
  - Constraints: unique (user, name), unique (user, slug).
  - save(): derives slug from name.

- LayoutBlock
  - Fields: layout (FK), block (FK to apps.blocks.models.Block), position (int, absolute order), base `col` (int, Bootstrap span: 1,2,3,4,6,12; default 12), optional responsive overrides: `col_sm`, `col_md`, `col_lg`, `col_xl`, `col_xxl`.
  - Optional preferences per instance: `preferred_filter_name`, `preferred_column_config_name` (used to select the viewer’s saved Block filter/view by name for that block instance).
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
- AddBlockForm: Add block to layout (field: `block` only). All widths default to inherit (base remains 12 by default). User adjusts widths later on the edit page.
- LayoutBlockForm: Edit responsive widths (fields: `col_sm`, `col_md`, `col_lg`, `col_xl`, `col_xxl`), title/note, and a per-block "Default Block Filter" selector backed by your saved block filters for that block. Base `col` remains at its model value and is not edited in the UI.
  - Also includes a per-block "Default Columns/View" selector backed by your saved column configurations (views) for that block. This lets duplicate blocks start with different column sets.
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
  - Column/view propagation to blocks:
    - If a LayoutBlock has a preferred column config name and the viewer has a matching `BlockColumnConfig`, the instance’s namespaced `column_config_id` is injected so that block uses the chosen view by default.
  - UI:
    - “Layout Filter” dropdown lists saved presets, with default preselected.
    - “Filter Conditions” collapsible renders dynamic filter fields for live overrides (non-persistent) using `components/filter_fields.html`.
    - On dropdown change, clears any `filters.*` overrides so the selected preset populates fields; reloads with `filter_config_id` only.
    - “Manage Filters” goes to filter config page; “Reset” links to the base URL (no query params).
  - Default filters are provided by signals only (no lazy creation in view).

- LayoutEditView
  - URL: /layouts/<username>/<slug>/edit/
  - Combined editor: add blocks and edit/reorder/delete blocks on one page.
  - Add block: top card with a block picker; selecting a block immediately adds it via AJAX and updates the grid (no Add button). Appends at `position = max+1`. All responsive cols default to inherit; base remains default 12.
  - Edit block settings: responsive grid of cards (one card per block). Each card shows:
    - Title and Note fields.
    - Default Block Filter dropdown listing your saved Block filters (by name) for that specific block, with a “Manage filters” link.
      Selecting one makes that filter the default for this instance only. Leave blank to inherit the block’s default.
    - Default Columns/View dropdown listing your saved column configurations for that block (if applicable), with a “Manage views” link. Leave blank to inherit the block’s default view.
    - Five dropdowns for `sm`, `md`, `lg`, `xl`, `xxl` responsive widths (labels above the fields). Changing any control auto-saves.
  - Card layout:
    - Row 1: Title | Default Block Filter | Default Column View
    - Row 2: Small | Medium | Large | Extra Large | Extra Extra Large
    - Row 3: Notes
  - Drag/drop ordering: powered by SortableJS using the card drag handle. Reordering auto-saves via AJAX to `/reorder/` without a page postback.
  - Delete block: Delete button on each card triggers an AJAX call and removes the card instantly.
  - Edit layout details: Name and Description auto-save via AJAX (no save button). If the name changes, slug and URLs update automatically.

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
- POST /layouts/<username>/<slug>/rename/ → `layout_rename` (AJAX: update name/description; returns JSON with updated URLs)
- GET/POST /layouts/<username>/<slug>/edit/ → `layout_edit` (GET-only UI; edits via AJAX)
- POST /layouts/<username>/<slug>/delete/ → `layout_delete`
- GET/POST /layouts/<username>/<slug>/filters/ → `layout_filter_config`
- POST /layouts/<username>/<slug>/reorder/ → `layout_reorder` (AJAX endpoint to persist block order)
- POST /layouts/<username>/<slug>/block/<id>/update/ → `layout_block_update` (AJAX update of responsive widths and title/note)
  - POST /layouts/<username>/<slug>/block/<id>/delete/ → `layout_block_delete` (AJAX delete of a block)
  - POST /layouts/<username>/<slug>/block/add/ → `layout_block_add` (AJAX add block and return updated table body)

Templates (apps/layout/templates/layout/)

- layout_list.html: Lists layouts and includes the create form.
- layout_detail.html: Renders layout header, Layout Filter dropdown, live Filter Conditions (collapsible), and block grid.
- layout_edit.html: Combined Add Block card (block picker only, AJAX add) + drag/drop grid of cards for ordering, per-block default filter selection, and responsive width edits (sm/md/lg/xl/xxl). Displays “auto-saves” for changes.
  - Also includes per-block default column/view selection and “Manage filters/views” links when supported.
 - _layout_rows.html: Partial used to render the card items; returned by AJAX add. Intentionally does not render formset ORDER/DELETE fields because ordering and deletion are AJAX-only.
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
- Propagation to blocks (filters): For each block, the merged values are namespaced and injected into the block’s GET (`{block_name}__{layout_block_id}__filters.<key>`). Blocks consume these instance-scoped filters and render accordingly.
- Propagation to blocks (columns/views): If a LayoutBlock sets `preferred_column_config_name` and the viewer has a matching `BlockColumnConfig`, the namespaced `{block_name}__{layout_block_id}__column_config_id` is injected so that instance uses the chosen column view by default.
 - Single-default invariant is enforced at the database level to avoid race conditions under concurrent updates.

Text Rendering

- Layout description and LayoutBlock note support multi-line input. On the detail page they render with preserved line breaks.

Visibility Changes and Signals

- private → public: create a "None" layout filter for all users.
- public → private: delete all non-owner layout filter configs.

Edit Semantics

- Edit page itself performs no POST submits; all state changes occur via AJAX endpoints. SortableJS must be present for drag/drop; without it, the list renders statically and reordering is disabled.

Cross-References

- See blocks documentation for per-block "None" filters and interaction between block-level and layout-level filters.

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
The layout detail page supports selecting a saved preset and applying live overrides.

- filter_config_id: ID of the saved layout filter preset to activate.
- filters.<key>: Live override values merged into the active preset using FilterResolutionMixin.
- Behavior: Changing the preset clears any existing filters.* overrides before reloading.

Access Control

- View: Any authenticated user may view public layouts; private layouts are viewable only by their owner.
- Edit/Delete: Allowed for staff users, or the owner when the layout is private. Owners cannot edit/delete public layouts.

AJAX Endpoints

- Reorder: POST JSON to /layouts/<username>/<slug>/reorder/ with {"ordered_ids": [..]}.
- Update block: POST JSON to /layouts/<username>/<slug>/block/<id>/update/ with any of:
  - `title`, `note`
  - `preferred_filter_name`, `preferred_column_config_name`
  - responsive fields: `col_sm`, `col_md`, `col_lg`, `col_xl`, `col_xxl`
- Delete block: POST to /layouts/<username>/<slug>/block/<id>/delete/.
- Add block: POST JSON to /layouts/<username>/<slug>/block/add/ with {"block": "<code>"}.
- Notes: Endpoints expect CSRF tokens and return JSON.

Formset Behavior

- The edit page uses a formset for rendering controls only; persistence is handled entirely via AJAX endpoints (no traditional Save submit).

Auto-Creation of "None" Filters

- On layout creation: a "None" filter preset (empty values) is created for the owner if private, or for all users if public.
- On new user creation: a "None" filter is created for each existing public layout for that user.

Future Developments

- Duplicate layout: Add an action to clone a layout, including its blocks and filter presets.
- Sharing controls: Allow sharing layouts with specific users or groups, beyond public/private.
- Export/Import: Provide JSON export/import for layouts (blocks + filter presets) across environments.
- Responsive preview: Add a visual overlay to preview effective Bootstrap columns at each breakpoint.
- `filter_config_id`: Active saved LayoutFilterConfig id.
- `filters.*`: Live overrides (cleared automatically when switching saved filter).

Query Parameters (Layout page)

- `filter_config_id`: Active saved LayoutFilterConfig id.
- `filters.*`: Live overrides (cleared automatically when switching saved filter).

How To Use

- Create a layout:
  - Go to Layouts and use the Create Layout form (name + visibility) to make a new layout. You will be redirected to the layout page.
- Open the editor:
  - Click Edit on your layout (URL: `/layouts/<username>/<slug>/edit/`). You must be the owner (or staff for public layouts) to edit.
- Add blocks (AJAX):
  - In the Add Block card, select a block from the dropdown. It is added instantly to the end of the list. Repeat to add more.
- Reorder blocks (AJAX):
  - Drag the ≡ handle on each block card to reorder. The order auto-saves; no Save button needed.
- Set responsive widths (AJAX):
  - Each block card has five dropdowns labeled `sm`, `md`, `lg`, `xl`, `xxl`.
  - Choose a value from the allowed sizes (1, 2, 3, 4, 6, 12). Changes auto-save.
  - Select `— inherit —` to inherit from the next smaller breakpoint.
  - Notes:
    - Base (extra-small) width remains at 12 and is not edited in the UI.
    - If all dropdowns are `— inherit —`, the block will render at the base width (12) on all devices.
- Delete a block (AJAX):
  - Use the Delete button on the block card; confirm the prompt. The card disappears immediately.
- View the layout:
  - Click Back to layout to see the rendered grid. Bootstrap classes are applied according to the responsive settings; blocks wrap into rows automatically.
- Manage layout-wide filters (optional):
  - Use the Filters page (`/filters/`) to save named filter presets per layout. The active preset propagates into all blocks on the layout.
- Troubleshooting:
  - If an action fails (e.g., network error), a toast appears at the bottom-right. Refresh the page to reload current state.
- Per-block (injected): `{block_name}__{layout_block_id}__filters.<key>` used internally to pass layout filters into blocks.

Typical Workflows

- Create a layout: Go to /layouts/, use the Create Layout form. You’re redirected to the layout.
- Add blocks: Open Edit Layout, pick a block from the dropdown; it adds immediately via AJAX. Widths inherit initially; adjust below.
 - Reorder/resize: Drag rows to change order (auto-saves). Changing any width dropdown auto-saves.
- Manage per-block defaults: In Edit Layout, choose a Default Block Filter and/or Default Columns/View for each block instance. Use the adjacent links to manage your saved filters and views.
- Manage layout filters: Use Layout Filter dropdown to select a preset; expand Filter Conditions to apply live overrides across all blocks; Manage Filters saves presets (persistent), while the collapsible applies live, non-persistent overrides.
- Reset: Click Reset to clear all query params and return to default view.

Edge Cases and Rules

- LayoutFilterConfig delete is protected when it’s the only config; deleting a default promotes another to default.
- Visibility: Non-staff layouts default to private; staff can set public via form. Owners cannot edit or delete public layouts unless staff; delete view restricts non-staff to private layouts.
- Slug uniqueness: Enforced per user for clarity and stable routing.

Extensibility Notes

- New block types automatically contribute to layout filter schema by implementing `get_filter_schema()`.
- Additional per-block UI can remain independent; layout-level filters will continue to override via the injected GET mechanism.
