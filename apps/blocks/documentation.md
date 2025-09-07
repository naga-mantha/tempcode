# Blocks App Guide

The `apps.blocks` app provides a pluggable framework for building reusable UI “blocks” that render data-rich widgets such as tables and charts. Blocks are registered once and can be embedded inside pages or rendered standalone, with optional per‑user configurations for filters and (for tables) visible columns.

This guide covers concepts, how to implement new blocks, available views, templates, and configuration models.

## Concepts

- Block: A Python class implementing `BaseBlock` that separates config from data and renders a template.
- Registry: The global `block_registry` maps a stable block code to a block instance.
- Config vs Data: `get_config()` returns metadata needed to render controls; `get_data()` returns the payload (rows, figure JSON, etc.).
- Instance namespace: When embedding the same block multiple times, GET params are namespaced using `"<block>__<instance>__..."` to avoid collisions.
- User configs: Persisted per‑user selections (filters and table columns) stored in `BlockFilterConfig` and `BlockColumnConfig`.

## Base Building Blocks

- `BaseBlock` (`apps/blocks/base.py`)
  - Required methods: `get_config(request, instance_id=None)`, `get_data(request, instance_id=None)`.
  - `render(request, instance_id=None)` merges config + data into the template context.
  - `supported_features`: descriptive list (e.g., `["filters", "column_config"]`).

- Registry (`apps/blocks/registry.py`)
  - `block_registry.register(code, instance)` to register; `block_registry.get(code)` to resolve.
  - Stores metadata (class, app name/label, supported features) for discovery.

## URL Endpoints

Defined in `apps/blocks/urls.py`:

- Tables
  - `GET /blocks/table/<block_name>/` → `render_table_block`
  - `POST /blocks/table/<block_name>/edit/` → inline edit API
  - `GET|POST /blocks/table/<block_name>/columns/` → manage column views
  - `GET|POST /blocks/table/<block_name>/filters/` → manage saved filters
  - `POST /blocks/table/<block_name>/filters/<config_id>/delete/` → delete saved filter

- Charts
  - `GET /blocks/chart/<block_name>/` → `render_chart_block`
  - `GET|POST /blocks/chart/<block_name>/filters/` → manage saved filters
  - `POST /blocks/chart/<block_name>/filters/<config_id>/delete/` → delete saved filter

- Pivots
  - `GET /blocks/pivot/<block_name>/` → render pivot page (includes partial)
  - `GET|POST /blocks/pivot/<block_name>/settings/` → manage pivot settings (rows/column/measure)
  - `GET|POST /blocks/pivot/<block_name>/filters/` → manage saved filters for pivots

Notes
- Add `?embedded=1` to render only the partial for embedding inside other pages.
- Standalone pages include a header and include the partial internally.

## Templates

- Table partial: `blocks/table/table_block.html`
- Table page: `blocks/table/table_block_page.html`
- Chart partial: `blocks/chart/chart_block.html`
- Chart page: `blocks/chart/chart_block_page.html`
- Filter editor partial: `components/filter_fields.html`

- Pivot partial: `blocks/pivot/pivot_table.html`
- Pivot page: `blocks/pivot/pivot_block_page.html`
- Pivot settings page: `blocks/pivot/pivot_config_view.html`
- Pivot filters page: `blocks/pivot/pivot_filter_config_view.html`

Both table and chart partials include a “Manage Filters” link and dynamic filter UI. Tables additionally include a “View” selector and “Manage Views” (column sets). There are also convenience links to open a standalone page:
- Tables: “Table Link” → `{% url 'render_table_block' block_name %}`
- Charts: “Chart Link” → `{% url 'render_chart_block' block_name %}`
Pivots include “Manage Settings” and a “Pivot Link” → `{% url 'render_pivot_block' block_name %}`. The header also shows “Saved Pivots” and “Saved Filters” dropdowns that persist selections using namespaced GET params.

## Filters (shared)

- Schema driven via `FilterResolutionMixin` (`block_types/table/filter_utils.py`).
- Schema format (per key): `{ type, label, choices?, tom_select_options? }` where:
  - `type`: `text` (default), `select`, `multiselect`, `boolean`.
  - `choices`: list or callable(user) → list for select/multiselect.
  - `tom_select_options`: optional dict of Tom Select settings merged into defaults.
- Resolution: `_resolve_filter_schema` normalizes types and resolves callable choices.
- Collection: `_collect_filters(qd, schema, base, prefix, allow_flat)` extracts values from request data, merging with saved config defaults.
- GET namespacing: keys look like `"<block>__<instance>__filters.<name>"` when embedded, or `"<block>__filters.<name>"` otherwise.

Persisted filters
- Model: `BlockFilterConfig(block, user, name, values, is_default)`.
- Behavior: First saved config per block/user becomes default. Marking another as default clears others. Delete endpoint enforces at least one config remains.
- UI: Filter management views use the block’s runtime schema to render inputs.

Pivot filters use the same storage and schema, with a dedicated UI at `/blocks/pivot/<block>/filters/` to allow future pivot-specific tweaks. The pivot page clears ad‑hoc overrides when switching between saved filters to ensure the saved values apply cleanly.

## Tables

Base class: `TableBlock` (`block_types/table/table_block.py`)
- Template: `blocks/table/table_block.html` (Tabulator 6.x)
- Supported features: `["filters", "column_config"]`
- Must implement:
  - `get_model()` → Django model used for permissions/labels.
  - `get_queryset(user, filters, active_column_config)` → filtered queryset.
  - `get_column_defs(user, column_config)` → list of `{field, title, ...}` for Tabulator.
- Optional:
  - `get_tabulator_options(user)` → additional Tabulator options dict.

Runtime workflow
- User selections resolved via `_select_configs` (active view + filter config).
- Filter schema is resolved and request overrides are applied.
- Queryset built and serialized to JSON respecting selected fields and readability.
- Column metadata derived from `get_column_defs` and Django’s `label_for_field`.

Column configuration
- Model: `BlockColumnConfig(block, user, name, fields, is_default)`.
- UI: `ColumnConfigView` lists, creates, deletes, and marks defaults.
- Helpers: `helpers/column_config.get_model_fields_for_column_config` expands FK subfields, applies field display rules, and respects `apps.permissions` checks.

Inline editing (optional)
- Endpoint: `POST /blocks/table/<block_name>/edit/` with JSON `{id, field, value}`.
- Validates via `apps.workflow.permissions.can_write_field_state` and model field cleaning.

## Charts

Base class: `ChartBlock` (`block_types/chart/chart_block.py`)
- Template: `blocks/chart/chart_block.html` (Plotly)
- Supported features: `["filters"]`
- Must implement:
  - `get_filter_schema(request)` or `get_filter_schema(user)`.
  - `get_figure(user, filters)` that returns a `plotly.graph_objects.Figure` or a `{data, layout}`‑like dict. You may also subclass the provided helpers:
    - `DonutChartBlock.get_chart_data(user, filters)` → `{labels, values}`
    - `BarChartBlock.get_chart_data(user, filters)` → `{x, y}`
    - `LineChartBlock.get_chart_data(user, filters)` → `{x, y}`
- Optional:
  - `get_layout(user)` to inject default Plotly layout (merged with figure layout).
  - `has_view_permission(user)` to apply permission checks.

UI elements
- Filter selector + Manage Filters link.
- “Chart Link” to open the standalone page for the chart.

## Signals

`apps/blocks/signals.py` maintains convenience default filters named “None”:
- On new user creation: creates an empty filter for all existing blocks; first filter is default.
- On new block creation: creates an empty filter for all existing users.

## Persistence Models

- `Block` (`code`, `name`, `description`): defines admin‑managed records used to tie user configurations to concrete block instances.
- `BaseUserConfig` (abstract): common logic ensuring exactly one default per user+block, and preventing deletion of the last remaining config.
- `BlockFilterConfig` and `BlockColumnConfig` extend `BaseUserConfig` to store saved filters and column sets respectively.

## Implementing a New Table Block

Example skeleton:

```python
from apps.blocks.block_types.table.table_block import TableBlock
from myapp.models import Project

class ProjectTable(TableBlock):
    def __init__(self):
        super().__init__(block_name="project_table")

    def get_model(self):
        return Project

    def get_filter_schema(self, user):
        return {
            "status": {"type": "select", "label": "Status", "choices": lambda u: [(s, s) for s in ["Open","Closed"]]},
            "owner": {"type": "text", "label": "Owner"},
        }

    def get_queryset(self, user, filters, active_column_config):
        qs = Project.objects.all()
        if status := filters.get("status"):
            qs = qs.filter(status=status)
        if owner := filters.get("owner"):
            qs = qs.filter(owner__username__icontains=owner)
        return qs

    def get_column_defs(self, user, column_config):
        return [
            {"field": "id", "title": "ID"},
            {"field": "name", "title": "Name"},
            {"field": "status", "title": "Status"},
        ]
```

Register the block (e.g., in an app config `ready()`):

```python
from apps.blocks.registry import block_registry
from .blocks import ProjectTable

block_registry.register("project_table", ProjectTable())
```

Create a `Block` record in admin with `code="project_table"` and a friendly name.

Visit: `/blocks/table/project_table/`.

## Pivots

Base class: `PivotBlock` (`block_types/pivot/pivot_block.py`)
- Template: `blocks/pivot/pivot_table.html` (Tabulator-based grid of aggregated results)
- Supported features: `["filters"]`
- Must implement in a concrete subclass:
  - `get_model()` → Django model used to derive labels, permissions, and default queryset.
  - `get_filter_schema(request)` → same schema structure as tables/charts; handlers operate on the base queryset before aggregation.
  - `build_columns_and_rows(user, filter_values)` in custom subclasses; `GenericPivotBlock` provides a ready data engine from a saved schema.

Generic, user-configurable pivot: `GenericPivotBlock` (`block_types/pivot/generic_pivot_block.py`)
- Storage model: `PivotConfig(block, user, name, is_default, schema)`.
- Schema fields:
  - `rows`: list of grouping field paths (checked items order defines grouping order)
  - `cols`: optional single column-dimension (0–1)
  - `measures`: list with one entry for MVP: `{source: <numeric field>, agg: sum|count|avg|min|max, label?: <title>}`
- Settings UI (`/blocks/pivot/<block>/settings/`):
  - Saved settings selector with set‑default/delete actions.
  - Top row inputs: Name | Column | Measure | Label | Aggregation.
  - “Rows” below as a sortable checklist (drag to reorder; checked items are applied in order).
  - Save updates existing config (when editing) or creates a new one.
- Runtime UI (pivot page):
  - Header shows “Saved Pivots” and “Saved Filters” dropdowns and links: “Manage Settings”, “Manage Filters”, and “Pivot Link”.
  - Filter Conditions panel uses the block’s filter schema with namespaced GET params.
  - Downloads: Excel and PDF via Tabulator client-side download helpers; options provided by the block.

Data engine (GenericPivotBlock)
- Applies saved filter config plus live overrides, then builds an annotated queryset: `values(*rows, *cols)` + the configured aggregation(s).
- Sanitizes aggregation aliases for safe SQL identifiers and uses label mapping for column titles.
- Shapes the output into Tabulator `columns` and `data` based on the selected rows/cols/measures.
- Supports at most one column dimension in MVP; no subtotals/grand totals yet.

Persistence and selection
- Saved Pivots: `PivotConfig` per block/user with single-default semantics (via `BaseUserConfig`).
- Saved Filters: same `BlockFilterConfig` model used by tables and charts.
- URL/state: the pivot template uses namespaced GET params `"<block>__<instance>__pivot_config_id"` and `"<block>__<instance>__filter_config_id"` so selections persist across reloads and when applying live filters.

## Repeaters

Base class: `RepeaterBlock` (`block_types/repeater/repeater_block.py`)
- Template (partial): `blocks/repeater/repeater_block.html`
- Page wrapper: `blocks/repeater/repeater_block_page.html`
- Settings page: `blocks/repeater/repeater_config_view.html`
- Supported features: Saved settings (no filters/downloads at repeater level)

URLs
- Render: `GET /blocks/repeater/<block_name>/` (adds `?embedded=1` for partial only)
- Manage settings: `GET|POST /blocks/repeater/<block_name>/settings/`

Saved settings UI
- The partial header shows a “Saved Settings” dropdown populated from the user’s `RepeaterConfig` rows for this block and marks the active one.
- Switching saved settings updates the namespaced `repeater_config_id` in the URL: `"<block>__<instance>__repeater_config_id"` when embedded; plain `repeater_config_id` on the standalone page.
- “Manage Settings” links to the settings page; “Repeater Link” opens the standalone page.

Enumeration and child rendering
- The repeater renders the configured child block once per distinct value of a group-by field.
- Enumeration base is provided by the child:
  - Preferred: child implements `get_enumeration_queryset(user)` returning a pre-filtered queryset.
  - Fallback: child exposes `get_model()`; the repeater uses `model.objects.all()`.
- Distinct values are derived from `group_by`; optional `label_field` provides human-readable titles.
- An “Unassigned” panel may be added for null values when `include_null` is enabled.

Fixed child vs generic
- Concrete repeaters may lock the child by overriding `get_fixed_child_block_code()`; the settings UI will not expose a “Child Block” selector.
- If the child is fixed, the schema’s `block_code` is enforced internally.
- A truly generic repeater (if ever exposed) can allow the child selector in its own settings page.

Admin-defined defaults (templates)
- `RepeaterConfigTemplate(block, name, is_default, schema, site_key?)` can be created in admin.
- When a user has no `RepeaterConfig` for a repeater block, the block or settings page lazily clones the template to the user as their default.

Field reference (Repeater settings)
- Name: Saved configuration name for this repeater.
- Cols (Bootstrap span): Width of each panel (1,2,3,4,6,12) in a 12-column grid; e.g., 6 → two panels per row.
- Group By: Field path on the child’s model used to enumerate one panel per distinct value (e.g., `order__buyer`).
- Label Field: Field path used to title each panel; defaults to the group-by value. Commonly a readable display field (e.g., `order__buyer__username`).
- Include Null: Adds a panel for rows with `group_by` = null (e.g., “Unassigned”) if any exist.
- Limit: Optional cap on number of panels to render.
- Sort: `asc` | `desc` | `none` to order panels by label (or leave as DB order).
- Panel Title Template: String template for panel headers; supports `{label}` and `{value}`.
- Child Filters Map (JSON): Mapping of child filter keys → source for the value:
  - `"value"`: use the raw group-by value (e.g., an id)
  - `"label"`: use the label field’s value
  - any literal string: pass as-is
  Example: `{ "buyer": "value" }`.
- Null Sentinel: Value to send to the child when the group value is null (e.g., `"__none__"`).
- Child Filter Config Name: Name of a saved filter config on the child to apply to every repeated instance.
- Child Column Config Name: Name of a saved column/view on the child to apply to every repeated instance.

## Implementing a New Chart Block

```python
from apps.blocks.block_types.chart.chart_block import DonutChartBlock

class TaskStatusDonut(DonutChartBlock):
    def __init__(self):
        super().__init__(block_name="task_status_donut", default_layout={"legend": {"orientation": "h"}})

    def get_filter_schema(self, user):
        return {"assignee": {"type": "text", "label": "Assignee"}}

    def get_chart_data(self, user, filters):
        # Compute labels/values here
        return {"labels": ["Open", "Closed"], "values": [42, 13]}
```

Register with the registry and add a `Block` record with `code="task_status_donut"`. Visit `/blocks/chart/task_status_donut/`.

## Embedding and Namespacing

- Use the render endpoints with `?embedded=1` to include only the partial HTML in other pages or layouts.
- When rendering multiple instances of the same block, pass an `instance_id` to the block’s `render(request, instance_id=...)` so control state (filters/views) remains independent.
- The templates and views honor namespaced GET params like `"<block>__<instance>__filter_config_id"` and `"<block>__<instance>__filters.<name>"`.

## Permissions Integration

- Field visibility and editability leverage `apps.permissions` and `apps.workflow.permissions` helpers:
  - Read checks: `get_readable_fields_state`, `can_read_field`
  - Edit checks: `get_editable_fields_state`, `can_write_field_state`
- Ensure these apps are installed and configured if you rely on field‑level controls.

## Developer Notes

- Blocks should be added to the registry exactly once (app `ready()` is a good place).
- The database `Block.code` must match the registry code to link saved configs.
- Chart blocks only support filter configurations; table blocks support both filter and column configurations.
- The chart template expects Plotly (loaded via CDN) and the table template expects Tabulator (also via CDN).


