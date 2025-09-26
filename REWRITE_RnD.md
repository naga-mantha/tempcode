# Mag360 Full Rewrite — Requirements & Design (R&D) v0.1

Status: Draft v0.1
Editors: Engineering
Scope: Blocks, Layouts, Permissions/Workflow facade, Theming, APIs, Content blocks

## 1. Executive Summary

- Re-architect the Blocks and Layouts system around a declarative BlockSpec, a small set of block services, and a thin layout composition layer.
- Use Bootstrap (components + JS) for UI, HTMX for partial updates, and DRF-style endpoints for data where needed.
- Adopt DB-wins for block display metadata (admin overrides allowed), with code as canonical for identity and features.
- Start with Blocks; permissions/workflow go through a PolicyService facade that returns permissive results initially and is hardened later.
- Add generic “content” blocks (spacer, text, button, card) that users can place in layouts.
- Add Bootstrap 5.3 light/dark mode support via data-bs-theme.

## 2. Goals, Non‑Goals, Success Metrics

Goals
- Consistent, extensible architecture for all block types (table, pivot, chart, content).
- Faster feature delivery via declarative BlockSpec + reusable services (FilterResolver, ColumnConfigResolver, QueryBuilder, Serializer, ExportOptions).
- Clean separation: Policy (permissions/workflow) → Blocks → Layouts.
- Better UX: lazy loading, robust error/empty states, offcanvas filters, light/dark theme.
- DB-wins for block display metadata with startup sync from registry.

Non‑Goals (v1)
- Replacing the entire permissions/workflow logic; we stub a facade and integrate later.
- SPA rewrite; we stay template-first with HTMX/Bootstrap.
- Server-side export queuing with Celery (planned post‑v1 if needed for large exports).

Success Metrics
- Time-to-add new block type ≤ 2 days including tests.
- P95 layout render time ≤ 1.5s with 4 lazy-loaded blocks (local pagination).
- 0 production incidents from permission regressions (once PolicyService is implemented).

## 3. Current State Summary (as-is)

- Blocks: Table/Pivot/Chart/Repeater live in `apps/blocks`, with a `TableBlock` that combines filter resolution, queryset building, serializer, and export options in one class.
- Layouts: Compose blocks using `Layout` and `LayoutBlock` with grid positions, filters, and per-instance defaults for block configs. Renders blocks by calling `block_impl.render()` and inserting HTML.
- Permissions/Workflow: Checks exist in `apps.permissions` and `apps.workflow`, used directly in blocks.

Pain Points
- Block classes are stateful and do too much; hard to test and extend.
- GET namespacing for embedded blocks is brittle.
- Mixed permission calls scattered across layers.
- No content-only blocks for layout composition.

## 4. Target Architecture

Layers
- PolicyService (facade): One place to answer read/write field checks and filter querysets by state. Phase 1 returns permissive results; later integrates real rules.
- Blocks: Declarative BlockSpec + small services per block instance:
  - FilterResolver: schema + parsing.
  - ColumnConfigResolver: fields/dimensions/labels.
  - QueryBuilder: queryset/aggregation, paging/sort.
  - Serializer: JSON-serializable payload.
  - ExportOptions: CSV/XLSX/PDF option generators.
- Registry & Sync: Registry holds all BlockSpecs, validates them, and syncs to DB `Block` rows (DB-wins for display fields).
- Layouts: Pure composition layer. Loads and renders blocks via partials/HTMX, persists per-instance settings, and handles shared filter UIs.

Execution Flow (per block render)
1) FilterResolver resolves schema + values from request.
2) ColumnConfigResolver resolves visible fields/config.
3) QueryBuilder builds dataset (server-side pagination/sort optional).
4) Serializer produces payload.
5) ExportOptions returns download options.
6) Template renders block chrome + content.

## 5. Technology Choices

- UI: Bootstrap 5.3 (CSS + JS) for accordions/offcanvas/modals/tooltips.
- Interactions: HTMX for partial GET/POST updates; Django templates remain primary.
- Data APIs: Django views for HTMX partials; lightweight DRF-style JSON endpoints for data-heavy blocks if needed.
- Theming: Bootstrap color modes via `data-bs-theme` (light/dark); persist in localStorage + cookie.

Note on libraries: see Section 23 for a full add/keep/drop inventory and dev tooling.

## 6. BlockSpec Contract

Concept
- BlockSpec is a typed, declarative definition for a block: identity, kind, template, supported features, default config, and service classes.

Required Fields
- id: unique string (e.g., "purchase.orders.table").
- name: human-friendly default name.
- kind: one of "table", "pivot", "chart", "kanban", "gantt", "content".
- template: Django template path for the block content.
- supported_features: subset of [filters, column_config, export, inline_edit, drilldown].
- services: classes for FilterResolver, ColumnConfigResolver, QueryBuilder, Serializer, ExportOptions (content blocks may omit).

Optional Fields
- description, category, version, permissions (declared intents), defaults (e.g., pagination size).

Validation Rules (registry)
- Unique id; allowed kind; template exists; supported_features subset is valid.
- If features include column_config, a ColumnConfigResolver must be present.
- If features include export, an ExportOptions provider must be present.

Example (sketch)
```
BlockSpec(
  id="purchase.orders.table",
  name="Purchase Orders",
  kind="table",
  template="blocks/table/table_block.html",
  supported_features=("filters","column_config","export"),
  services=Services(
    filter_resolver=DefaultFilterResolver,
    column_resolver=TableColumnResolver,
    query_builder=PurchaseOrderQuery,
    serializer=TableRowSerializer,
    export_options=TableExportOptions,
  ),
  category="Purchasing",
  description="Purchase orders listing with filters and exports",
)
```

## 7. PolicyService (Phase 1: permissive)

Interface (used everywhere instead of direct checks)
- `filter_queryset(user, qs) -> qs`
- `can_read_field(user, model, field, obj=None) -> bool`
- `can_write_field(user, model, field, obj=None) -> bool`

Phase 1 Behavior
- Return `qs` unchanged; return True for all field checks.

Phase 2 (post‑v1)
- Integrate `apps.permissions.checks` and `apps.workflow.permissions` behind this facade. Add caching where safe.

## 8. Registry & DB Sync (DB‑wins)

Startup/Command Sync (`manage.py sync_blocks`)
- For each BlockSpec.id, get_or_create `apps.blocks.models.Block(code=id)`.
- If a DB row exists with name/description/category, keep DB values (DB-wins); otherwise set from BlockSpec defaults.
- Mark DB rows that have no matching BlockSpec as disabled and report them.
- `code` is read-only in admin; expose `enabled`, `category`, and an "override_display" flag if we want to lock DB overrides per row.

Admin
- Allow name/description/category edits; `code` read-only.
- Show registry status badge (in registry / orphan / disabled).

## 9. Data Model Changes

Block (apps.blocks.models.Block)
- Add fields: `enabled: bool = True`, `category: CharField(blank=True)`, `override_display: bool = True`.

LayoutBlock (apps.layout.models.LayoutBlock)
- Add `settings: JSONField(default=dict)` to store per-instance block settings (especially for content blocks and minor per-instance tweaks for data blocks).
- Keep x/y/w/h (Gridstack), position, title, note, preferred_* fields.

Constraints
- Preserve existing uniqueness/default constraints on per-user configs (column/filter configs).

## 10. UI/UX Specifications

Global
- Theme toggle in the header; persist selection; apply `data-bs-theme` on `<html>`.
- Error/empty states: standardized alert cards with icon and retry.

Layout Detail
- Header: left — Edit Layout; right — Layout Filter dropdown + Manage + Reset.
- Sidebar Offcanvas (closed by default; persisted):
  - Filter Conditions (accordion of fields from layout’s filter schema).
  - Private Layouts; Public Layouts (alphabetical, highlight current, scroll if long).
- Content area: grid with lazy-loaded blocks (skeletons until content arrives).

Blocks
- Standard block chrome: title, optional note, action toolbar (export, configure), and body.
- HTMX-driven updates for filters/pagination/sort/inline edit saves (where allowed).
- Table: server-side pagination for large result sets; local for small.

Content Blocks (v1)
- SpacerBlock: settings = height (px/rem), responsive visibility.
- TextBlock: settings = content (Markdown/HTML), alignment, variant (lead/muted), safe_html.
- ButtonBlock: settings = label, href (URL or route + params), variant (primary/secondary/link), size, target, optional icon.
- CardBlock: settings = header/body/footer content (Markdown/HTML), bg/variant, border, shadow.
- All content blocks: `kind="content"`, no data services, render template directly using `LayoutBlock.settings`.

## 11. Server Endpoints (HTMX + JSON)

HTMX Partials (HTML)
- `GET  /blocks/<block_code>/partial` → render block content (accepts query args for filters, paging, instanceId).
- `POST /blocks/<block_code>/config/columns` → save column config (private/public), returns status + updated menu.
- `POST /blocks/<block_code>/config/filters` → save filter config (private/public), returns status + updated menu.
- `POST /layouts/<username>/<slug>/blocks/<id>/settings` → save per-instance settings (content/data minor tweaks).

JSON (optional for data-heavy or charts)
- `GET  /api/blocks/<block_code>/schema` → filter schema, column config options.
- `GET  /api/blocks/<block_code>/data` → dataset (with paging/sort params).
- `POST /api/blocks/<block_code>/export` → initiate export; return file or job id.

Paging/Sort Contract (tables)
- `page`, `page_size`, `sort_by`, `sort_dir` (asc/desc).

## 12. Filtering & Column Configs

Filter Schema
- Types: text, number, date, select, multiselect, boolean.
- Choices can be provided static or via callable; if `choices_url` is present, client hits the URL.
- Token support for dates: `__today__`, `__start_of_month__`, `__end_of_month__`, `__start_of_year__`, `__end_of_year__`, fiscal-year tokens.

Column Configs
- Per-user, private/public with a single default per block.
- Validation ensures selected fields exist/are readable (via PolicyService once implemented).

## 13. Exports

- Small datasets: synchronous CSV/XLSX/PDF responses with options from ExportOptions provider.
- Large datasets (post‑v1): Celery job + notification link; server streams when ready.
- Options: file name, sheet name, header styles; shallow merge defaults + overrides.

## 14. Security & Compliance

- Phase 1: PolicyService returns permissive checks; still authenticate all endpoints and log access.
- Phase 2: Enforce base + state permissions via PolicyService in QueryBuilder and Serializer layers.
- CSRF on POST endpoints; validate filter inputs against schema; reject unknown keys.

## 15. Performance & Observability

- QueryBuilder enforces select_related/prefetch where applicable; cap relation depth; allow per-model allow/deny lists for relations.
- Server-side pagination for tables by default beyond N rows.
- Cache expensive choice lists with short TTLs.
- Metrics: per-block render time, query counts, pagination latency; structured logs for slow blocks.

## 16. Testing Strategy

Unit
- Filter token resolution (date/fiscal boundaries).
- Relation path inference and depth limits.
- Column config discovery with permission/display rules.
- PolicyService behavior (stub → real).

Integration
- Registry validation and DB sync (DB-wins).
- End-to-end table block: schema → data → serialize → template context.
- Layout render with multiple blocks + offcanvas filters + content blocks.

UI/UX
- Template snapshot tests for block chrome and layout pages.
- Playwright tests for filter interactions, pagination, and theme toggle.

## 17. Migration & Rollout Plan

Phase A — Foundations
- Add PolicyService facade (permissive) and route all checks through it.
- Implement BlockSpec + registry + `sync_blocks` (DB-wins policy).
- Add `settings` JSONField to `LayoutBlock` and admin/edit forms for content blocks.

Phase B — First Vertical Slice (Table)
- Extract Table services and wire controller (keep existing templates initially).
- Add HTMX endpoints for table partial render, paging/sort, export.

Phase C — Layout & Content Blocks
- Add Spacer/Text/Button/Card blocks with modal-based settings; integrate into "Add Block" flow.
- Implement offcanvas filters, lazy block loading, and standardized block chrome.

Phase D — Broader Adoption
- Migrate key existing tables to the new pattern.
- Implement Pivot/Chart services and migrate selected blocks.
- Add theme toggle across base templates.

Phase E — Permissions/Workflow Integration
- Replace permissive PolicyService with real checks; add unit/integration tests; feature flag rollout.

Cutover
- Run new and old systems in parallel if needed (behind URLs/flags) for 1–2 sprints.
- Switch layout pages to new render paths; remove legacy paths after sign-off.

## 18. Risks & Mitigations

- Risk: Permission regressions when enabling real PolicyService.
  - Mitigation: Add comprehensive tests; shadow-run policy evaluations in logs before enforcing.
- Risk: Performance regression with server-side pagination.
  - Mitigation: Add metrics; load-test; cap page sizes; index hot fields.
- Risk: Registry/DB drift.
  - Mitigation: Sync on startup + CI command; admin badges for orphan/disabled blocks.
- Risk: Stakeholder churn on UI changes.
  - Mitigation: Wireframes and early demos; feature flags; iterative rollout.

## 19. Timeline (Strawman)

- Week 1: PolicyService stub; BlockSpec + registry; sync command; migrations for Block + LayoutBlock.settings; theme toggle base.
- Week 2: Table services + HTMX endpoints; migrate 1–2 table blocks; content blocks MVP (Text/Spacer).
- Week 3: Layout offcanvas filters + lazy loading; Button/Card blocks; exports polished.
- Week 4: Pivot/Chart services for 1 example each; expand tests; telemetry.
- Week 5–6: Permissions/workflow integration behind flag; rollout; deprecate legacy paths.

## 20. Open Questions

- Which blocks are v1 must-haves beyond Table/Pivot/Chart? (KPI, Kanban, Calendar?)
- Server-side export queue (Celery) needed in v1 or v2?
- Any compliance requirements (PII, audit retention) affecting logs/exports?

## 21. Appendices

Appendix A — Minimal Interfaces (Python sketches)
```
@dataclass(frozen=True)
class BlockSpec:
    id: str
    name: str
    kind: Literal["table","pivot","chart","content"]
    template: str
    supported_features: Sequence[str]
    services: Services | None = None  # content blocks may omit
    category: str | None = None
    description: str = ""

class PolicyService:
    def filter_queryset(self, user, qs):
        return qs
    def can_read_field(self, user, model, field, obj=None) -> bool:
        return True
    def can_write_field(self, user, model, field, obj=None) -> bool:
        return True

class BlockController:
    def __init__(self, spec: BlockSpec, policy: PolicyService):
        self.spec, self.policy = spec, policy
    def render_partial(self, request, instance_id: str | None = None):
        # 1) filters 2) config 3) dataset 4) payload 5) options
        ...
```

Appendix B — Content Block Settings (JSON schema examples)
- SpacerBlock
```
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "height": {"type": "string", "pattern": "^\\d+(px|rem)$", "default": "24px"},
    "visible_on": {"type": "array", "items": {"enum": ["xs","sm","md","lg","xl"]}}
  },
  "required": ["height"]
}
```
- TextBlock
```
{
  "type": "object",
  "properties": {
    "content": {"type": "string", "default": ""},
    "align": {"enum": ["start","center","end"], "default": "start"},
    "variant": {"enum": ["body","lead","muted"], "default": "body"},
    "safe_html": {"type": "boolean", "default": false}
  },
  "required": ["content"]
}
```

Appendix C — Theme Toggle
- Add a small script to read `localStorage['theme']` and set `data-bs-theme` on `<html>`; provide a header dropdown to change and persist it.

## 22. Detail Pages (Context-Aware Layouts)

Overview
- Enable building model object detail pages entirely from blocks. A "detail layout" is mapped to a model (and optionally an individual object) and each block scopes its data to the current object via bindings.

Routing & Layout Mapping
- Add a mapping from model label to a Layout used in detail mode.
  - Data model addition (Layout):
    - `scope_type`: enum {`global` (default), `model_detail`, `object_detail`}.
    - `scope_ref`: string; for `model_detail` use `"app_label.ModelName"`; for `object_detail` use `"app_label.ModelName:pk"`.
- Example route: `GET /purchase/orders/<pk>/` → fetch PO(id=pk), resolve the best layout:
  1) object-specific layout if present (`object_detail`), else
  2) model detail layout (`model_detail`), else
  3) fallback template.

Context Object
- On render, construct and pass a context object to all blocks on the page:
  - `{"model": "common.PurchaseOrder", "id": 123, "slug": "123", "extra": {}}`
  - Controller is responsible for fetching the object and verifying access before building context.

Bindings (LayoutBlock.settings)
- Allow per-block bindings that map context → block filters/config. Stored in `LayoutBlock.settings`:
  - Example: `{"bindings": {"purchase_order_id": "context.id"}}`
  - For related blocks (e.g., receipts): `{"bindings": {"vendor_id": "context.obj.business_partner_id"}}` (controller can precompute `extra` as needed to avoid arbitrary expressions on the client).
- Resolution order in FilterResolver:
  1) Context bindings (from settings),
  2) Active saved filter config (if any),
  3) Request query params (win over others).

HTMX & Params
- All block partial endpoints accept the context (model label + object id) as hidden inputs or query params so subsequent paging/sorting/filter requests remain scoped.

Security
- Server re-fetches the object by id on each request (or validates object exists and user has access). Do not trust client-provided context alone.
- PolicyService still applies (phase 1 permissive; phase 2 enforces read/write/state rules).

Performance
- Prefer server-side pagination for heavy tables scoped by `context.id`.
- Cache small choice lists; measure per-block render times to identify slow blocks.

Example Blocks for Purchase Order Detail
- Lines table (filter `purchase_order_id = context.id`).
- Receipts table (join via line → PO).
- KPI cards (totals, open quantity/value).
- Workflow card (state + actions).
- Notes/attachments (repeater).
- Content blocks (Text/Spacer/Button/Card) for headings, descriptions, links.

Comments (django-comments-xtd)
- We will support user comments on any model instance (e.g., PurchaseOrderLine) using `django-contrib-comments` + `django-comments-xtd`.
- Integration
  - Install & settings: add `"django_comments"` and `"django_comments_xtd"` to `INSTALLED_APPS`; set `COMMENTS_APP = "django_comments_xtd"`.
  - URLs: include `path("comments/", include("django_comments_xtd.urls"))`.
  - Templates: override comment list/form templates as needed under `templates/comments/` or `templates/django_comments_xtd/`.
  - Usage in detail pages: in a PO or POL detail template use `{% render_xtdcomment_tree for object %}` and `{% render_comment_form for object %}`.
  - Notifications/moderation: enable xtd’s follow-up notifications and moderation workflow via settings; customize the form to restrict who can comment.
- Block option: provide a `CommentsBlock` (kind=`content`) that renders the comment tree and form for the current context object. It relies on the context binding (`model`, `id`) described above; visibility/permission can be gated via PolicyService later.

### 22.1 Data Model & Migration Notes (Detail Pages)

Schema changes
- Layout (apps.layout.models.Layout)
  - `scope_type`: CharField(choices=[global, model_detail, object_detail], default=global)
  - `scope_ref`: CharField(blank=True, default="") — holds `app_label.Model` or `app_label.Model:pk`
  - Index: (`scope_type`, `scope_ref`, `visibility`, `user`) to speed lookup
- LayoutBlock (apps.layout.models.LayoutBlock)
  - `settings`: JSONField(default=dict) — per-instance configuration/bindings
- Block (apps.blocks.models.Block)
  - `enabled`: BooleanField(default=True)
  - `category`: CharField(blank=True, default="")
  - `override_display`: BooleanField(default=True)

Migrations
- Create schema migration adding the above fields.
- Data migration:
  - For all existing Layout rows, set `scope_type = 'global'`, `scope_ref = ''`.
  - Initialize `settings = {}` for existing LayoutBlock rows.
- Admin updates:
  - Make Block.code read-only; expose `enabled`, `category`, `override_display`.
  - In Layout admin, show `scope_type`/`scope_ref` with simple help text.

Compatibility
- Existing pages continue to use global layouts.
- Detail pages opt-in by creating a `model_detail` or `object_detail` layout.

### 22.2 Controller Flow (Purchase Order Detail)

Route
- `GET /purchase/orders/<pk>/` → Purchase Order detail page composed of blocks.

Flow (sketch)
```
class PurchaseOrderDetailLayoutView(LoginRequiredMixin, View):
    template_name = "layout/layout_detail.html"  # or a dedicated detail template

    def get(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        # Access check (phase 1: authenticated; phase 2: PolicyService)
        # policy.ensure_object_viewable(request.user, po)

        model_label = "common.PurchaseOrder"
        layout = resolve_detail_layout(model_label, obj_id=po.pk, user=request.user)

        context_obj = {"model": model_label, "id": po.pk, "slug": str(po.pk), "extra": {}}

        blocks = []
        for lb in layout.blocks.select_related("block").order_by("position", "id"):
            # Apply settings.bindings → namespaced GET for this block instance
            params = build_params_from_bindings(lb.settings.get("bindings", {}), context_obj)
            params.update({"embedded": "1", "instance_id": str(lb.id)})
            html = render_block_partial(lb.block.code, request, params)
            blocks.append({"id": lb.id, "x": lb.x, "y": lb.y, "w": lb.w, "h": lb.h, "html": html,
                           "title": lb.title, "note": lb.note})

        return render(request, self.template_name, {"layout": layout, "blocks": blocks, "object": po})

def resolve_detail_layout(model_label: str, obj_id: int, user) -> Layout:
    # Prefer object-specific, then model-specific, then fallback
    qs = Layout.objects.filter(enabled=True)
    # object_detail for this user/private or public
    obj_ref = f"{model_label}:{obj_id}"
    layout = (qs.filter(scope_type="object_detail", scope_ref=obj_ref)
                .filter(Q(visibility="public") | Q(user=user)).order_by("-visibility").first())
    if layout:
        return layout
    # model_detail
    layout = (qs.filter(scope_type="model_detail", scope_ref=model_label)
                .filter(Q(visibility="public") | Q(user=user)).order_by("-visibility").first())
    if layout:
        return layout
    # fallback: raise or use a default global layout
    return qs.filter(scope_type="global").filter(Q(visibility="public") | Q(user=user)).first()

def build_params_from_bindings(bindings: dict, ctx: dict) -> dict:
    # Minimal safe evaluator: only supports "context.id" and static values
    out = {}
    for key, expr in (bindings or {}).items():
        if expr == "context.id":
            out[key] = str(ctx.get("id"))
        else:
            out[key] = str(expr)
    return out

def render_block_partial(block_code: str, request, params: dict) -> str:
    # HTMX-style render of a block partial; may internally call the registry/controller
    # Returns HTML string (catch and wrap exceptions into an alert)
    ...
```

## 23. Dependencies & Tooling

Runtime — Python/Django (keep)
- django, django-environ, psycopg2, django-extensions (dev)
- Forms/UI: django-crispy-forms, crispy_bootstrap5, django_widget_tweaks
- Data/ETL: pandas, django-pandas, numpy, python-dateutil, openpyxl, requests
- Charts: plotly

Runtime — Frontend (keep)
- bootstrap, bootstrap-icons
- tabulator-tables, tom-select, sortablejs
- gridstack (CDN for now)

Add (to enable HTMX architecture and APIs)
- htmx (frontend) and django-htmx (backend helper)
- djangorestframework (optional, for JSON endpoints where needed)
- sentry-sdk (error tracking), django-redis (caching) — optional
- weasyprint (optional, for server-side PDF generation) or playwright (alt.)

Drop (when verified unused)
- alpinejs (prefer Bootstrap JS + HTMX)
- django-contrib-comments, django-comments-xtd (if not used in UI)

Dev Tooling (quality/type/automation)
- django-stubs: type hints for Django internals (makes mypy effective)
- mypy: static type checker; enforces typed interfaces for services
- ruff: fast linter (flake8/pylint class), import rules, simple fixes
- black: opinionated code formatter; consistent style
- isort: import sort/sectioning; works with black
- pre-commit: run ruff/black/isort/mypy/pytest hooks before commits
- pytest, pytest-django, pytest-cov, pytest-xdist, factory-boy: tests

Packaging Notes
- Pin versions in requirements (base/dev) and lock Node deps; split dev-only tools into a separate requirements-dev.txt and pre-commit-config.yaml.

## 24. Requirements Profiles (Proposed)

We will split Python dependencies into base (prod) and dev/test profiles. Version pins are suggestions and can be adjusted to match current Python/Django versions.

requirements.txt (base/prod)
- Django>=4.2,<5.1
- django-environ>=0.11
- psycopg2>=2.9
- django-crispy-forms>=2.1
- crispy-bootstrap5>=2024.2
- django-widget-tweaks>=1.5
- pandas>=2.2
- django-pandas>=0.6
- numpy>=1.26
- python-dateutil>=2.8
- openpyxl>=3.1
- requests>=2.32
- plotly>=5.24
- djangorestframework>=3.15  # optional JSON APIs
- django-htmx>=1.17           # HTMX helpers
- weasyprint>=62.3            # Optional, HTML→PDF
- playwright>=1.47             # Optional alternative for PDF via headless Chromium
- django-contrib-comments>=2.2
- django-comments-xtd>=2.9    # threaded comments on instances
- sentry-sdk>=2.0             # optional, prod only
- django-redis>=5.4           # optional caching backend

requirements-dev.txt (dev/test only)
- -r requirements.txt
- django-extensions>=3.2
- mypy>=1.10
- django-stubs[compatible-mypy]>=4.2
- ruff>=0.5
- black>=24.8
- isort>=5.13
- pre-commit>=3.7
- pytest>=8.3
- pytest-django>=4.8
- pytest-cov>=5.0
- pytest-xdist>=3.6
- factory-boy>=3.3
- pytest-playwright>=0.5      # if using Playwright in tests

Node (package.json)
- Keep: bootstrap, bootstrap-icons, tabulator-tables, tom-select, sortablejs, gulp toolchain, sass, autoprefixer, cssnano.
- Add: htmx via CDN (no npm package required) or vendor a local copy; gridstack via CDN is acceptable.

## 25. New Block Types — Kanban and Gantt

### 25.1 KanbanBlock

Purpose
- Visualize items grouped by a status/category with drag-and-drop between lanes; optional WIP limits and ordering.

Spec
- kind: "kanban"
- supported_features: ("filters", "inline_edit" optional, "export" optional)
- per-instance settings (stored in LayoutBlock.settings):
  - group_by: field path for lane grouping (e.g., `status`)
  - swimlanes (optional): secondary grouping (e.g., `assignee`)
  - wip_limits: { lane_value: int }
  - order_field: field used for within-lane ordering
  - card_fields: [field paths] for card title/subtitle/badges
  - templates (optional): small Jinja/Django snippets for card body

Services
- FilterResolver: reuse date tokens/choices
- CardConfigResolver: analogous to ColumnConfigResolver, decides which fields are on the card
- QueryBuilder: fetch queryset, apply PolicyService.filter_queryset, bucket by group_by, compute order indices
- Serializer: lanes = [{id, title, wip, cards: [{id, fields…}], order: [...] }]
- ExportOptions: optional CSV export of items with lane assignment

UI
- Use SortableJS (already present) for drag-and-drop between lanes and reordering within a lane.
- Endpoints
  - GET partial render (initial + lane refresh)
  - POST /move with {item_id, from_lane, to_lane, position} to update status/order atomically; return refreshed affected lanes

Notes
- Enforce WIP limits server-side; optimistic concurrency on move
- Audit trail optional (signals on move)

### 25.2 GanttBlock (Plotly)

Purpose
- Visualize tasks scheduled over time (start/end/duration), with groups and dependencies; read-only in v1, optional edits later.

Spec
- kind: "gantt"
- supported_features: ("filters", "export" optional)
- per-instance settings (LayoutBlock.settings):
  - start_field, end_field (or start + duration)
  - label_field (task name), progress_field (optional)
  - group_by (e.g., project/resource), color_by (status)
  - time_window: {from, to} with tokens allowed (e.g., `__start_of_month__`)
  - zoom: day|week|month (affects layout x-axis tick formatting)
  - dependencies (optional): field(s) defining links (from_id → to_id)

Services
- FilterResolver: reuse existing tokens and schema
- QueryBuilder: build tasks [{id, name, start, end, progress, group, color}], links [{source, target, type}] within time_window; apply PolicyService
- Serializer: {tasks: [...], links: [...], window: {...}}
- ExportOptions: export a flattened CSV of tasks or a static PNG via Plotly image export (optional)

Rendering Library
- Use Plotly Python to produce a Gantt-style figure:
  - Prefer plotly.express `px.timeline(data_frame, x_start, x_end, y=label, color=...)` to build the base chart; or use figure_factory.create_gantt if specific features are needed.
  - Integrate with existing Chart template plumbing (similar to ChartBlock): return a Plotly figure JSON and render via plotly.js.
- Interactivity
  - V1: read-only interactions (hover, select, zoom). Plotly does not support drag-resize-edit of tasks; if interactive editing is required later, consider swapping to a specialized library (e.g., Frappe Gantt or a commercial component) behind the same BlockSpec.

Performance
- Server-side windowing (only fetch tasks in the visible time range)
- Cap number of tasks per render; paginate or filter by project/resource when large

## 26. FormBlock (ModelForm)

Purpose
- Render a Django ModelForm to create or edit any model instance, styled with Crispy Forms (Bootstrap 5). Decoupled from table inline edits.

Spec
- kind: "form"
- supported_features: ("inline_edit" optional for local toggles; typically none)
- Modes:
  - Create: no object_id; apply defaults and context bindings
  - Edit: object_id provided via page context or querystring

Per-instance Settings (LayoutBlock.settings)
- model_label: string (e.g., "common.PurchaseOrderLine")
- fields: { include?: [..], exclude?: [..], order?: [..] }
- layout: JSON describing sections/tabs/rows/columns (see mapping below)
- defaults: { field: value | token ("__today__") | binding ("context.id") }
- widgets: { field: { type: "select|textarea|date|number|text", attrs: {...} } }
- submit: { label?: "Save", redirect?: url, refresh_blocks?: [block_ids], emit_event?: "form:saved" }
- read_only: boolean (force view mode)
- edit_selector: "context.id" | "query.object_id" | null
- display_fields (read-only summaries): ["supplier.name", "buyer.email"]

JSON → Crispy Layout Mapping (runtime)
- Input JSON
```
{
  "sections": [
    { "title": "Main", "rows": [
      { "cols": [
        { "width": {"md":6}, "fields": ["order", "buyer"] },
        { "width": {"md":6}, "fields": ["supplier", "category"] }
      ] }
    ] },
    { "title": "Notes", "rows": [ { "cols": [ {"fields": ["notes"]} ] } ] }
  ],
  "tabs": [ {"title": "Tab A", "sections": [...]}, {"title": "Tab B", "sections": [...]} ]
}
```
- Mapping rules
  - section → Crispy `Fieldset(title, ...)`
  - tab holder → Crispy `TabHolder(Tab("A", ...), Tab("B", ...))`
  - row → Crispy `Row(...)`
  - col width → Crispy `Column(..., css_class=f"col-md-{n}")`
  - field string → Crispy `Field("name")`; per-field overrides applied before render
  - If no layout provided, render `{% crispy form %}` with default ordering

ModelForm & Crispy Helper
- For each FormBlock render, build a ModelForm subclass dynamically:
  - Meta.model from model_label
  - Meta.fields computed from include/exclude/order and PolicyService (phase 2)
  - Widgets from settings.widgets (Tom Select for FKs/M2M, date for DateField, etc.)
- Attach a `FormHelper` with `template_pack="bootstrap5"`, method/action, submit/cancel buttons, and optional HTMX attributes.

Endpoints (HTMX)
- GET  `/blocks/<code>/form` → render form partial
  - Params: `model_label`, `object_id?`, `instance_id`, context (model/id) optional
- POST `/blocks/<code>/form` → validate and save
  - On success: return success partial (toast) and re-render form (view mode or cleared for create); optionally emit `hx-trigger="form:saved"` with `{model, id}`
  - On error: return form with crispy-rendered validation errors

Permissions & Read-only
- Phase 1: permissive (all fields editable)
- Phase 2:
  - Object-level: verify user can view/edit instance via PolicyService
  - Field-level: if readable but not writable → disabled/readonly; if not readable → hide from form and layout
  - FK queryset restriction: filter choices via PolicyService

FK Read-only Displays
- Render `display_fields` near the form using dotted paths; only show if readable per PolicyService
- Live summary on FK change (create/edit): add `hx-get` on the FK widget to fetch a small summary partial for the selected object and swap into a target div

Decoupling from Table Inline Edits
- Inline row edits in TableBlock remain separate endpoints and logic
- Optional coordination via events: FormBlock can emit `form:saved` and TableBlock may listen to refresh itself; no hard linkage

Testing
- Unit: defaults/bindings resolution; JSON→Crispy mapping; widget application; permission masking of fields
- Integration: create/edit happy paths; validation errors; HTMX submit/response flow
- E2E: open from Table row into modal, save, and refresh table via event

## 27. RepeaterBlock (Compositional)

Purpose
- Render a set of panels by enumerating distinct values from a dataset and, for each value, embedding a child block (Table/Chart/Pivot/Form/etc.). Enables dashboards like “one table per buyer” or “one chart per category”.

Spec
- kind: "repeater"
- supported_features: ("filters") optional
- Per-instance settings (LayoutBlock.settings):
  - child_block_code: BlockSpec id (e.g., "purchase.orders.table")
  - group_by: field path for distinct enumeration (e.g., `buyer__username`)
  - label_field: optional display label path; defaults to `group_by`
  - include_null: bool; null_sentinel: any (string/number) to pass to child when value is null
  - order_by: "label" | "metric"; order: "asc" | "desc" | "none"; limit: int
  - metric_mode: "aggregate" (DB aggregation) | "child" (derive metric from child); metric_agg: "count"|"sum"|"avg"|"min"|"max"; metric_field: field path when needed
  - child_filters_map: { child_filter_key: "value" | "label" | literal }
  - child_filter_config_name: name of a saved BlockFilterConfig to apply to the child
  - child_column_config_name: name of a saved BlockColumnConfig to apply to the child
  - cols: 1–12 (Bootstrap grid width per panel)
  - title_template: string, e.g. "{label}" or "{label} ({metric})"
  - title: optional overall section title

Services & Flow
- Enumerator (QueryBuilder specialization):
  - Determine base queryset: prefer child.get_enumeration_queryset(user); else, if child declares a model_label, use `model.objects.all()`
  - Apply PolicyService.filter_queryset to base queryset
  - Build distinct values and labels using `.values(...).distinct()`; for metric sorting, annotate with aggregation when `metric_mode = aggregate`
  - Respect include_null, order_by/order, limit; return [{value, label, metric?}]
- Orchestrator:
  - For each enumerated item, build a small child parameter payload from `child_filters_map` (map "value"/"label"/literal)
  - Resolve and inject child saved configs by name for the current user
  - Render the child block partial and collect `{title, html}` into `panels`
- Template:
  - Render a responsive grid of panels (cols width), each with `title` and the child HTML

Endpoints (HTMX)
- `GET  /blocks/<repeater_code>/partial` → full render (or shell + placeholders)
- Optional `GET /blocks/<repeater_code>/panel?key=…` for progressive per‑panel loading (improves TTI for many panels)

Permissions
- Enumerator filters base queryset via PolicyService (phase 1 permissive; phase 2 enforce)
- Child blocks still run their own PolicyService checks (row and field‑level)

Performance
- Prefer `metric_mode = aggregate` for fast DB‑side ranking and limiting
- For large N, cap `limit` and use progressive HTMX loading; cache enumeration briefly per user/filter

Testing
- Unit: enumeration (distinct + aggregation), child_filters_map resolution, ordering/limit, name→id resolution of saved configs
- Integration: error handling when child unavailable; progressive loading; policy filtering applied

## 28. Filter Layout Customization

Purpose
- Allow admins and users to control the visual arrangement of filter fields for a block (order, grouping, visibility), reused across Table/Chart/Pivot.

Model
- BlockFilterLayoutTemplate (admin-defined, per Block, optional default)
- BlockFilterLayout (per-user override, per Block)

Behavior
- FilterResolver returns the schema (types/labels); the layout describes presentation only (order/sections/columns, hide)
- Resolution order: user layout → admin template → schema order
- UI: a “Manage Filter Layout” dialog to drag-drop fields into sections/columns; save per user or admin template (staff only)

Testing
- Ensure hidden fields don’t render; order honored; fallback works

## 29. Workflow Actions Block

Purpose
- Display available workflow transitions for the current object and allow users to execute them with confirmation and notes.

Spec
- kind: "workflow_actions"
- supported_features: ()
- settings: { model_label, action_style (buttons|dropdown), confirm: bool }

Endpoints
- GET partial: render current state and available transitions from Workflow engine
- POST apply: perform transition (phase 1 permissive; phase 2 via PolicyService + workflow rules)

UX
- Show current state badge; list transitions as Bootstrap buttons or a dropdown; optional notes textarea in a modal before submit
- On success: emit `workflow:transitioned` event with new state; other blocks may refresh

## 30. KPI Block (Single Value / Dial)

Purpose
- Show an aggregate metric (count, sum, avg, etc.) with optional threshold coloring and a small trend.

Spec
- kind: "kpi"
- supported_features: ("filters", "export" optional)
- settings: { metric: {agg, field}, label, prefix/suffix, thresholds: [{op, value, class}], trend: {period, field, agg} }

Services
- QueryBuilder computes the metric (and optional trend series)
- Serializer returns {value, formatted, trend: [...]} for template

Rendering
- Option A: Plain numeric card with icon and conditional class
- Option B: Dial (reuse existing dial pattern or a small Plotly gauge)

## 31. Layout Edit Mode (Gridstack)

Scope
- Document the edit experience for layouts and persistence of positions/sizes/settings.

Features
- Drag/drop to reorder; resize blocks; add/remove; duplicate
- Edit per-block settings via modal (content + data blocks)
- Set per-instance preferred column/filter config names for data blocks
- Save: persist x/y/w/h/position and `settings` JSON in LayoutBlock; throttle updates
- Keyboard accessibility: move focusable handles; provide “Move Up/Down/Left/Right” actions for non-pointer users

## 32. Drilldown & Cross‑Filtering

Purpose
- Enable blocks to emit filter changes or navigate to detail pages when users click a data point, without tight coupling.

Mechanism
- Blocks can declare drilldown events (e.g., `chart:point-click` with payload)
- Layout listens and translates into: (a) update another block’s filters via HTMX; or (b) navigate to a model detail layout using the clicked id
- Security: only allow declared filter keys; validate payload

## 33. Accessibility & i18n

Accessibility
- Ensure color-contrast; keyboard navigability for offcanvas, modals, grid edit; ARIA labels on controls; focus management

i18n
- Mark user-visible strings for translation; keep date/number formatting consistent; load locale‑aware formats in templates

## 34. Management Commands & Admin Ops

- `sync_blocks`: sync BlockSpec to DB (DB‑wins for display); report orphans; optionally disable
- `rebuild_workflow_permissions`: existing command — keep and document
- `rebuild_field_permissions`: existing command — keep and document
- `seed_block_configs`: optional helper to create common column/filter layouts per user group

## 35. Browser Support & Performance Budgets

Support
- Modern evergreen browsers (latest Chrome/Edge/Firefox/Safari); mobile Safari/Chrome latest

Budgets
- First interaction on layout page with 4 lazy blocks ≤ 1.5s (typical data)
- Block partial response ≤ 400ms P95 under normal load (local pagination)
- JS/CSS payloads minimized via gulp pipeline; defer Plotly/Tabulator when not needed

## 36. Layout Duplication

Purpose
- Let users duplicate an existing layout (public or their own) into their private space to customize without affecting the original.

Behavior
- From layout detail/edit, "Duplicate" opens a dialog to choose new name, category, visibility (defaults to private).
- Copy semantics
  - Duplicate `Layout` (name/description/category/visibility) with current user as owner
  - Duplicate `LayoutBlock` rows with x/y/w/h/position, title, note, settings, preferred_* names (filter/column)
  - Option: "Include my layout filters" — copies the caller’s `LayoutFilterConfig` rows to the new layout preserving is_default; otherwise do not copy
  - Do not copy block-level per-user configs (BlockColumn/Filter) — these remain tied to Block and user
- Constraints: enforce unique name per user; auto-suffix "(Copy)" if collision

Endpoints
- POST `/layouts/<username>/<slug>/duplicate` → returns redirect to new layout

Permissions
- Anyone can duplicate a public layout; a user can duplicate their own private layout; for shared layouts, only viewers/editors can duplicate

Testing
- Ensure deep copy of blocks/settings; optional filter configs; uniqueness handling

## 37. Layout Sharing (Share by Copy)

Purpose
- Share a layout by creating recipient‑owned copies, so recipients can customize independently. Permissions apply during copy and at view time.

Behavior
- Owner selects one or more users to share with. For each recipient:
  - Create a new `Layout` owned by the recipient (visibility: private by default)
  - Deep copy all `LayoutBlock` records (x/y/w/h/position/title/note/settings/preferred_* names)
  - Copy the owner’s LayoutFilterConfig set (optional toggle: include my filters). The recipient receives their own copies, preserving is_default semantics (ensure exactly one default exists per recipient)
- Resolve Block preferred config names on each block:
    - If the recipient already has a PUBLIC BlockFilterConfig/BlockColumnConfig with that name → reuse it
    - If the recipient already has a PRIVATE config with that name → create a new recipient‑owned copy from the owner’s config with a suffixed name (e.g., "<name> (copy)"), pruning fields/filters the recipient cannot read
    - If no config exists → create a recipient‑owned copy from the owner’s config, with pruning
    - Default semantics: only set the copied config as default if the owner’s was default AND the recipient has no existing default for that block
  - Name collisions: append “(from <owner>)” or “(Copy)” to the new layout and config names as needed
- One‑time copy: subsequent edits by owner do not propagate. (A future “push updates” is out of scope.)

Permissions during copy
- When duplicating configs to the recipient:
  - Remove column fields the recipient cannot read; if a config becomes empty, skip and fall back to defaults
  - Remove filter keys for fields the recipient cannot read; resolve tokens as usual
  - If a block itself is not viewable to the recipient (policy denies base queryset), keep the block but it will render empty for that user

UI
- “Share” button opens a modal with user multiselect and an option:
  - [x] Include my layout filters
  - [x] Include my per‑block column/filter configs (pruned by permissions)
- On submit, show a success list with links to each created layout under each recipient

Endpoints
- POST `/layouts/<username>/<slug>/share` → performs copy to selected users; returns summary

Testing
- Deep copy correctness (blocks/settings)
- Config pruning by permissions and maintenance of a single default
- Idempotency and collision handling for repeat shares (e.g., create a new copy with suffix)

## 38. Layout PDF Export

Purpose
- Download an entire layout as a PDF for sharing or reporting. Also support programmatic PDF generation by specifying block codes + filters.

Profiles
- `LayoutExportProfile` (optional): name, page_size (A4/Letter), orientation, margins, header_html, footer_html, scale; public/private

Inputs
- Mode A (by layout): `layout = <username>/<slug>`, plus optional filter config id or explicit filters
- Mode B (by blocks): `blocks = [{ code, filters, column_config_id?, filter_config_id? }, ...]`, optional title/description
- PDF profile: by name or inline settings

Rendering
- Server assembles a print-friendly HTML using a dedicated minimal template (no interactive chrome)
- Blocks render in a printable mode (suppress toolbars, ensure full content for selected pagination scope)
- CSS print rules ensure page breaks; optional headers/footers from profile

Engine
- Preferred: WeasyPrint (pure Python) to render HTML → PDF with paged media CSS
- Alternative (if WeasyPrint stack is unavailable): headless Chromium via Playwright to "print to PDF"; keep behind a feature flag

Endpoints
- POST `/export/layout/pdf` → returns `application/pdf`
  - Body: one of Mode A or Mode B plus profile, and a max page limit/scope param

Permissions
- Only include blocks the user can view; omit or mark others with a notice
- Respect layout sharing/visibility rules and PolicyService filters

Testing
- Snapshot rendered HTML; generate small PDFs in CI; verify headers/footers and page breaks; verify block exceptions are handled gracefully

## 39. Implementation Plan (Phased Delivery)

Overview
- Sequenced phases to land foundations first, deliver working slices early, and integrate advanced features safely. Each phase has an acceptance gate. Estimated durations are indicative and depend on team size and scope.

Phase 0 — Prep (0.5–1 week)
- Confirm R&D v1.0; extract this plan into tickets/milestones.
- Create working copy repo; split requirements into base/dev with pins.
- Bootstrap 5 and crispy settings verified; theme toggle scaffolded (no behavior change).
Acceptance: repo builds; dependencies pinned; base UI unchanged.

Phase 1 — Core Platform (1 week)
- PolicyService stub with `filter_queryset`, `can_read_field`, `can_write_field` (permissive).
- BlockSpec dataclass + Registry with validation; `sync_blocks` command (DB‑wins).
- Migrations: Block.enabled/category/override_display; LayoutBlock.settings JSON; Layout.scope_type/scope_ref + indexes.
Acceptance: `sync_blocks` runs cleanly; legacy pages still render; no regressions.

Phase 2 — HTMX Wiring (2–3 days)
- Add django-htmx; base template includes/CSRF.
- Generic block partial endpoint/renderer that accepts `instance_id`, filters, and optional context.
Acceptance: trivial sample block renders via HTMX partial.

Phase 3 — Table Refactor Slice (1–1.5 weeks)
- Extract services for one exemplar Table (FilterResolver, ColumnConfigResolver, QueryBuilder with relation inference, Serializer, ExportOptions).
- Orchestrate via Table controller; reuse existing templates; local pagination first.
- Tests: unit (tokens, inference), integration (context/data), HTML snapshot.
Acceptance: exemplar block works via HTMX partial with tests green.

Phase 4 — Layout UX + Content Blocks (1 week)
- Offcanvas filters; lazy load blocks; standardized block chrome.
- Add Spacer/Text/Button/Card content blocks with per‑instance settings.
Acceptance: users add content blocks, reposition, and render; blocks lazy‑load.

Phase 5 — Detail Pages + Comments (1 week)
- Implement model/object scoped layouts; route for a chosen model (e.g., Purchase Order).
- Context bindings → block filters; integrate django-comments-xtd; CommentsBlock.
Acceptance: detail layout renders scoped blocks; comments functional.

Phase 6 — Layout Duplication & Share by Copy (1 week)
- Duplicate layout (deep copy) + optional layout filter configs.
- Share by copy to selected users with config resolution/pruning and default rules.
Acceptance: flows complete; permissions/pruning honored; collisions handled.

Phase 7 — Layout PDF Export (1 week)
- Print template; WeasyPrint engine (Playwright fallback behind flag).
- Mode A (by layout) and Mode B (blocks+filters) with profiles.
Acceptance: PDF downloads with correct page breaks; permissions observed.

Phase 8 — FormBlock (1–1.5 weeks)
- ModelForm + Crispy (Bootstrap 5); JSON→Crispy layout mapping.
- HTMX GET/POST with validation; events on success; read‑only when non‑writable.
Acceptance: create/edit for target model works; modal pattern proven.

Phase 9 — Repeater Modernization (0.5–1 week)
- Enumerator (distinct/aggregate + PolicyService); orchestrator with payloads; optional progressive loading.
Acceptance: current repeater use‑cases reproduced with tests.

Phase 10 — Pivot/Chart/KPI/Gantt (1 week)
- Extract services for a pivot and a chart; add KPI; add Gantt via Plotly px.timeline (read‑only v1).
Acceptance: at least one pivot+chart+KPI+Gantt block functional.

Phase 11 — Permissions/Workflow Hardening (1–2 weeks)
- Replace stub with real PolicyService (wrap existing permissions/workflow) behind a flag.
- Shadow mode logging → enforce; prune invalid fields/filters on config save.
Acceptance: parity with legacy permissions; rollout flag enabled in staging→prod.

Phase 12 — Tooling & CI (ongoing; finalize here)
- Add ruff/black/isort/mypy/pre-commit; pytest config; basic coverage gates.
- Optional: sentry-sdk, django-redis; per‑block render metrics logs.
Acceptance: pre‑commit active; CI green; telemetry visible.

Phase 13 — Adjacent Enhancements (scaffold only)
- Wire the following foundations while refactoring Table so later features slot in without churn (full delivery in later phases):
  - Cross‑filtering & drill‑through: standard HTMX events (e.g., `block:filter-changed`, `chart:point-click`) and a layout event bus.
  - Global context bar: shared params (date range, site, currency) plumbed into block FilterResolver as optional inputs.
  - Block templating & layout variables: registry support for prebuilt block presets; per‑layout constants injected into blocks.
  - Scheduled layouts: background job placeholders and API contract to render a layout with parameter presets to PDF/email.
  - Forms foundations: endpoints pattern to support inline formsets, bulk edits, validation rules, and change requests later.
  - Workflow hooks: bulk transition endpoint pattern; SLA timer fields on workflow states (no UI yet); automation signal hooks.
  - Collaboration hooks: comment/mention/attachment endpoints; annotation model for charts; task linking model (minimal).
  - Search scaffolding: global search endpoint and command palette registration; saved searches API.
  - Analytics layer: metric/dimension registry interfaces; snapshot table naming conventions.
  - Import/export: import mapping model + endpoints; webhooks/API tokens; export preset model.
  - Security/governance: stubs for SSO/MFA integration points; PolicyService extension points for row/field security and PII masking; audit trail adapter.
  - Performance: enforce server‑side pagination by default thresholds; per‑block cache key strategy; structured perf logs.
  - Multi‑tenancy & SDK: tenant discriminator strategy notes; BlockSpec SDK packaging layout.
  - UI/UX: keyboard shortcuts and command palette placeholders; theming tokens; mobile layout breakpoints.
  - DevEx: pre‑commit, seed data & demo layouts, migration helpers for BlockSpec/registry changes.

Immediate Next Actions (Week 1)
- Merge migrations for Block/LayoutBlock/Layout fields.
- Add PolicyService stub; switch current blocks to use it via adapters.
- Implement BlockSpec/Registry and `sync_blocks`.
- Wire django-htmx and a minimal block partial route.

Phase 13 — Advanced Enhancements (full delivery)
- Cross‑filtering & drill‑through across a layout (≥3 blocks) via an event bus; drill to detail pages.
- Global context bar (date range/site/currency) with precedence rules vs per‑block filters; plumbed into FilterResolver.
- Block templating and per‑layout variables; library of prebuilt blocks with one‑click add.
- Scheduled layouts: email/PDF with parameter presets and audit logs.
- Forms: inline formsets, bulk edits with preview/undo, validation rules engine, change requests routing.
- Workflow: bulk transitions, SLA tracking/alerts, automation hooks (signals/webhooks/jobs).
- Collaboration: comments/mentions/attachments, chart annotations, tasks linked to records.
- Search: global search, command palette, saved searches; optional semantic search.
- Analytics: metric/dimension registry, daily/weekly snapshots, lineage.
- Import/export: import mapping UI, webhooks and API tokens, export presets and schedules.
- Security/governance: SSO/OIDC, MFA, PolicyService extensions for row/field security and PII masking, audit trails/history.
- Performance: caching strategy, per‑block perf telemetry, server‑side pagination defaults.
- Multi‑tenancy & SDK: tenant isolation strategy; BlockSpec SDK + example repo.
- UI/UX: keyboard shortcuts, theming tokens, mobile layout improvements.
- DevEx: seed/demo data, migration helpers, docs.

Acceptance (Phase 13)
- Cross‑filtering/drill‑through demonstrated on a layout with at least 3 blocks.
- Global context applies correctly and predictably; precedence documented and tested.
- Scheduled layout exports run reliably with audit logs; import/export presets usable.
- PolicyService row/field security and PII masking integrated behind a flag and audited.
- Perf telemetry active with meaningful thresholds and caching documented.
