# Blocks Application Architecture

## High-Level Concepts

### Specifications and Services
Blocks are described by immutable `BlockSpec` records declared in Python modules. A specification captures the runtime identity (`id`), presentation metadata (`name`, `category`, `description`), template, and feature flags for a block, and it advertises which Django model it queries when using the built-in table/pivot services.【F:apps/blocks/specs.py†L18-L36】  Each spec may attach a `Services` bundle that points to concrete resolver, serializer, and query classes; omitting this bundle yields a static content block without server-side data plumbing.【F:apps/blocks/specs.py†L9-L15】【F:apps/blocks/controller.py†L28-L45】

The registry bootstrapper (`apps.blocks.register`) preloads core specs and lazily imports optional ones. This keeps the registry idempotent while allowing downstream apps to contribute blocks simply by exposing a `BlockSpec` instance.【F:apps/blocks/register.py†L6-L41】

### Policy Service
All resolver and serializer code is guarded by the `PolicyService` façade. The default implementation is permissive—it returns unfiltered querysets and allows read/write access to every field—but the API is intentionally minimal so project-specific authorization logic can be dropped in without modifying the rest of the stack.【F:apps/blocks/policy.py†L1-L25】  The controller passes the active policy instance to table/pivot builders so they can enforce per-field visibility when constructing filter schema, rows, and column catalogs.【F:apps/blocks/controller.py†L86-L98】【F:apps/blocks/services/model_table.py†L177-L248】

### Controller Lifecycle
`BlockController` orchestrates the request lifecycle for both table and pivot specs. It detects whether a spec publishes services and then chooses a rendering path:
- Content blocks with no services get a minimal context payload (DOM IDs and URLs) so the frontend can mount a shell without querying data.【F:apps/blocks/controller.py†L28-L45】
- Table specs execute `_build_table_context`, which coordinates filters, saved table layouts, column resolution, and initial row serialization when remote pagination is disabled.【F:apps/blocks/controller.py†L47-L230】
- Pivot specs route through `_build_pivot_context`, reusing filter plumbing and then delegating to a pivot engine to calculate aggregates.【F:apps/blocks/controller.py†L232-L399】

The controller also wires up AJAX endpoints for refreshing blocks, exporting data, and fetching deferred filter choices by embedding the relevant URLs in the returned context and the `frontend_config` payload that powers the JavaScript components.【F:apps/blocks/controller.py†L170-L229】【F:apps/blocks/controller.py†L319-L398】

## Persistence Models

### Block Registry Overrides
`Block` stores user-editable metadata about a spec, including whether it is enabled and any custom display strings. The ORM model ties dynamic registry data to database overrides so administrators can toggle or rename blocks without code changes.【F:apps/blocks/models/block.py†L4-L16】

### User-Scoped Configurations
Multiple models derive from `BaseUserConfig`, an abstract helper that enforces “exactly one default per (block, user)” semantics. Saving a config automatically promotes the first entry to default or demotes other defaults inside a transaction; deleting the last config raises an error to preserve a usable default.【F:apps/blocks/models/base_user_config.py†L1-L63】

The concrete user config models capture different personalization layers:
- `BlockColumnConfig` stores ordered field lists and a visibility scope (`private` versus `public`). Its custom delete handler promotes the next available config when the default is removed.【F:apps/blocks/models/block_column_config.py†L1-L39】
- `BlockFilterConfig` persists saved filter values, again with per-user/public visibility toggles.【F:apps/blocks/models/block_filter_config.py†L1-L24】
- `PivotConfig` captures saved pivot schemas (row/column dimensions and measures) and shares the same visibility semantics.【F:apps/blocks/models/pivot_config.py†L1-L29】

### Layout Metadata
`BlockFilterLayout` keeps the persisted arrangement of filter controls for a user, falling back to administrator-provided templates when no per-user layout exists.【F:apps/blocks/models/block_filter_layout.py†L1-L20】

`FieldDisplayRule` gives administrators the ability to mark individual model fields as mandatory or excluded. The field catalog builder consults these rules while compiling the column list for a model-driven table.【F:apps/blocks/models/field_display_rule.py†L1-L21】【F:apps/blocks/services/field_catalog.py†L33-L128】

### Table Configurations
`BlockTableConfig` stores saved column layouts for classic tables. It mirrors the visibility flags from other config models and adds a uniqueness constraint that ensures only one default exists per (block, user). The save method uses transactions to demote competing defaults and to auto-promote the first layout to default.【F:apps/blocks/models/table_config.py†L1-L39】

## Table Blocks

### Column Catalog Resolution
Table specs usually rely on `ModelColumnResolver`, which wraps `build_field_catalog` to generate column metadata (key, label, type, mandatory flag) from the spec’s Django model. The catalog observes policy checks, respects allow/deny lists supplied through the spec, applies administrator rules from `FieldDisplayRule`, and can traverse relations up to `column_max_depth`. Mandatory fields bypass policy exclusions to match legacy behaviour.【F:apps/blocks/services/model_table.py†L149-L176】【F:apps/blocks/services/field_catalog.py†L1-L200】

When an active `BlockTableConfig` exists, the controller reorders the resolved columns to match the saved layout, ensuring the rendered table stays in sync with the user’s preferences.【F:apps/blocks/controller.py†L156-L205】

### Filter Schema and Values
Filter handling flows through a `filter_resolver` instance declared on the spec. The default `SchemaFilterResolver` reads request parameters according to the filter schema, performs type coercion (including tokenized date helpers such as `__start_of_month__`), and exposes a `clean` hook used to sanitize saved filter configs before merging them into the live query.【F:apps/blocks/services/model_table.py†L1-L143】  The controller trims schema entries and saved values using `prune_filter_schema` and `prune_filter_values`, which apply policy checks and key allow-lists so that removed filters cannot reappear from stale client data.【F:apps/blocks/services/model_table.py†L83-L148】【F:apps/blocks/controller.py†L86-L158】

Active filter values are composed from (1) the user’s selected filter preset, (2) any keys cleared via the frontend, and (3) request overrides. The controller also generates badge metadata for the UI by pairing each filter key with its human-readable label.【F:apps/blocks/controller.py†L120-L204】  Layout preferences are injected via `BlockFilterLayout` or administrator templates when available.【F:apps/blocks/controller.py†L205-L229】

### Query Execution and Serialization
`ModelQueryBuilder` translates cleaned filter values into ORM lookups, choosing sensible defaults (`icontains` for text, `__in` for multiselect, etc.) unless the schema overrides the lookup. After filtering, the active `PolicyService` scopes the queryset before it is serialized.【F:apps/blocks/services/model_table.py†L144-L212】  When remote pagination is disabled, the controller synchronously serializes the initial table payload using `ModelSerializer`, which traverses nested attributes safely and masks fields the policy forbids by returning `"***"`.【F:apps/blocks/services/model_table.py†L213-L277】【F:apps/blocks/controller.py†L170-L199】

### Table Options and Frontend Contract
Allowlisted Tabulator options are merged from the spec and sanitized through `merge_table_options`, preventing unexpected client overrides while letting specs opt into pagination or sorting behaviours.【F:apps/blocks/options.py†L1-L46】【F:apps/blocks/controller.py†L170-L229】  The assembled context includes DOM identifiers, URLs for refresh/data/export endpoints, active configuration IDs, and a `frontend_config` blob that mirrors the server decisions for consumption by the JavaScript widgets.【F:apps/blocks/controller.py†L170-L229】

## Pivot Blocks

### Saved Pivot Schemas
Pivot specs reuse the filter pipeline described above and then resolve a user-selected `PivotConfig`. Visibility and default selection follow the same rules as tables: the controller searches for a query parameter, then a named preference, then falls back to user/public defaults.【F:apps/blocks/controller.py†L240-L338】

### Aggregation Engine
`DefaultPivotEngine` executes the configured pivot by obtaining a queryset (either through the spec’s `query_builder` service or directly from the spec’s model), applying optional legacy integrations, and computing grouped aggregates. It supports time bucketing for day/month/quarter/year dimensions, deduplicates measure aliases, and formats row/column headers for display.【F:apps/blocks/services/pivot_table.py†L1-L198】【F:apps/blocks/services/pivot_table.py†L199-L288】  Results are returned as a `PivotResult` dataclass containing column metadata, row data, and the resolved active configuration for downstream persistence.【F:apps/blocks/services/pivot_table.py†L11-L32】【F:apps/blocks/controller.py†L339-L398】

### Pivot Frontend Payload
The pivot controller response mirrors the table payload: it bundles computed rows, serialized column definitions (converted into `{key, label}` for the frontend), active filter badges, download configuration, and the DOM/URL wiring required to refresh or export the pivot. Because pivot data is fully aggregated server-side, the `dataUrl` is blank and the frontend renders the provided dataset immediately.【F:apps/blocks/controller.py†L339-L398】

## Stored Configuration Accessors
Helper functions in `apps.blocks.configs` wrap the ORM to list and choose active table/filter/pivot configurations. They centralize default selection logic (e.g., prefer a user default, then a public default, then the first available entry) so both table and pivot controllers behave consistently.【F:apps/blocks/configs.py†L1-L55】
