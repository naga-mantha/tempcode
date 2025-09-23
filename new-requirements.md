# Application Requirements Overview

This document captures the capabilities implemented across the Permissions, Workflow, Common, Blocks, and Layout Django apps. It is derived directly from the source code so a rewrite can re-implement the same behaviours.

## Permissions App

### Purpose
Provide a reusable permission framework that layers per-request caching, model/instance/field checks, and integration hooks for views, forms, templates, and querysets.

### Feature Requirements
- Cache repeated `user.has_perm` evaluations per request using `ContextVar` storage with opt-out contexts and automatic cleanup after each request. (`PermissionCacheMiddleware`, `clear_perm_cache`, `disable_perm_cache`).
- Allow superusers and optionally staff (`settings.PERMISSIONS_STAFF_BYPASS`) to bypass all permission checks.
- Expose helpers to verify model-level (`can_view_model`, `can_add_model`, `can_change_model`, `can_delete_model`), instance-level (`can_view_instance`, etc.), and field-level (`can_read_field`, `can_write_field`) access, including support for auto-generated field permissions.
- Provide queryset filters (`filter_viewable_queryset`, `filter_editable_queryset`, `filter_deletable_queryset`) that stream rows and only return objects the user may act on.
- Generate per-field permissions for editable fields on concrete models (`generate_field_permissions_for_model`).
- Supply class-based view mixins (`ModelPermissionRequiredMixin`, `InstancePermissionRequiredMixin`) and decorators (`model_permission_required`, `instance_permission_required`) to enforce permissions.
- Offer a form mixin (`PermissionFormMixin`) that removes unreadable fields and disables unwritable fields before validation.
- Ship template tags (`user_can_*`) for checking model, instance, and field permissions inside templates.

### Key Libraries & Dependencies
- Django core (`django.conf.settings`, `django.core.exceptions.PermissionDenied`, `django.db.models.QuerySet`, template library, middleware integration).
- Standard library modules: `contextlib`, `contextvars`, `functools`, `typing`.
- ASGI helper `asgiref.sync.iscoroutinefunction` for async-aware middleware teardown.

## Workflow App

### Purpose
Implement configurable state machines that attach to business models, enforce transition rules, and extend permission checks with workflow state awareness.

### Feature Requirements
- Persist workflows tied to Django content types, with status flags (`active`, `deprecated`, `inactive`) that gate creation and transitions (`Workflow` model).
- Manage workflow states with uniqueness per workflow, automatic first-state start designation, and support for marking start/end states (`State` model).
- Define transitions between states with optional group-based access control and staff/superuser bypass (`Transition` model).
- Record transition history including actor, states, transition, and comment via a generic relation (`TransitionLog` model).
- Provide a mixin (`WorkflowModelMixin`) for business models that enforces workflow status rules on creation and assigns default start states.
- Expose utilities to retrieve allowable transitions for a user/object and to apply transitions with permission checks, workflow inactivity enforcement, persistence, and audit logging (`get_allowed_transitions`, `apply_transition`).
- Extend permission checks to consider workflow state when inspecting instances, fields, and querysets (`can_*_instance_state`, `can_*_field_state`, `filter_*_queryset_state`).
- Generate workflow/state-specific permissions for models and fields (`generate_workflow_permissions_for_model`).
- Provide a form mixin (`WorkflowFormMixin`) to hide or disable fields based on workflow-state permissions.
- Supply a POST-only view helper to trigger transitions and surface success/error messages (`perform_transition`).

### Key Libraries & Dependencies
- Django models, generic foreign keys, content types, auth groups, and messaging framework.
- Django settings for staff bypass configuration.
- Plotly is **not** used here (charting lives in Blocks); dependencies are limited to Django core and slug utilities.

## Common App

### Purpose
House shared business entities, utilities, and helper functions that power purchasing, sales, production, scheduling, and reporting features.

### Feature Requirements
- Core master data models with workflow support and pandas integration, including Items, Item Groups/Types, Units of Measure, Currencies, Exchange Rates, Programs, and Business Partners. Many models expose both standard `objects` managers and `django_pandas` `DataFrameManager` for analytics.
- Order management models spanning purchasing (`PurchaseOrder`, `PurchaseOrderLine`), sales (`SalesOrder`, `SalesOrderLine`), and production (`ProductionOrder`, `ProductionOrderOperation`, `ProductionOrderSchedule`), all workflow-aware.
- Scheduling and capacity planning models: `Calendar`, `CalendarDay`, `CalendarShift`, `ShiftTemplate`, `WorkCenter`, `Machine`, `Labor`, `LaborVacation`, `MachineDowntime`, with fields for dates, availability, and notes.
- MRP and planning artefacts: `PlannedPurchaseOrder`, `PlannedProductionOrder`, `PurchaseMrpMessage`, `ProductionMrpMessage`, and `MrpRescheduleDaysClassification`, plus receipt tracking (`Receipt`, `ReceiptLine`, `PurchaseTimelinessClassification`) and global purchase settings.
- Task and ToDo tracking models with simple relational fields and workflow hooks (`Task`, `ToDo`).
- Utility modules for consistent clock handling (`utils.clock.now/today`), robust text file ingestion that tolerates encoding differences and integrates pandas/numpy (`functions.files`), and importer helpers.
- Filter factories for AJAX/autocomplete style endpoints (e.g., item choice builders that honor search terms and optionally scope to open purchase orders).
- Context processors supplying layouts for navigation and branding metadata.

### Key Libraries & Dependencies
- Django ORM and admin integrations, plus reusable mixins from the Workflow app.
- Third-party: `django_pandas` `DataFrameManager`, `pandas`, `numpy`, `python-dateutil`'s `relativedelta` for date math.
- Standard library: `datetime`, `os`, `shutil`, among others for utility helpers.

## Blocks App

### Purpose
Deliver a pluggable block/widget system for analytics and data exploration, including tables, charts, pivots, and repeaters with user-customisable filters and columns.

### Feature Requirements
- Base block interface that separates configuration from runtime data and renders Django templates (`BaseBlock`).
- Global registry for block implementations with metadata capture (app label/name, supported features) and duplicate/type validation (`BlockRegistry`, `block_registry`).
- Chart blocks leveraging Plotly to render donut, bar, line, and dial visualisations with reusable filter resolution, layout overrides, and permission-aware queryset filtering (`ChartBlock` hierarchy, `DialBlock`).
- Table block implementation that drives column configuration, queryset inference via `select_related`/`prefetch_related`, permission-aware row serialisation (masking unreadable fields, per-row edit flags), and integration with user-managed filter/column templates (`TableBlock`).
- Filter resolution utilities that normalize schema definitions, support special date tokens (today, start/end of fiscal periods), and consult global settings for fiscal calendars (`FilterResolutionMixin`).
- Services for applying registered filter handlers to querysets based on block-provided schemas (`apply_filter_registry`).
- Helpers to compute column display rules, manage block filter layouts, and integrate with permissions/workflow state checks throughout rendering.

### Key Libraries & Dependencies
- Django views, ORM, admin utilities, messaging, and template rendering.
- Plotly (`plotly.graph_objects`) for chart generation.
- Standard library modules (`abc`, `uuid`, `json`, `logging`, `calendar`, `datetime`).
- Integrations with other internal apps: Permissions (`filter_viewable_queryset`, field checks), Workflow (state-aware filtering), Common (`GlobalSettings` for fiscal tokens).

## Layout App

### Purpose
Provide dashboard/page composition tooling that arranges blocks for users, manages filter presets, and exposes CRUD interfaces with permission-aware access control.

### Feature Requirements
- Layout container model with per-user slug uniqueness, visibility settings (private/public), categories, and auto-slugification on save (`Layout`).
- Block placement model storing grid positions, display metadata, and preferred default filter/column configs with validation on coordinates and spans (`LayoutBlock`).
- User-specific layout filter configurations with default management enforced via atomic transactions (`LayoutFilterConfig`), including safeguards against deleting the final config.
- Access mixins ensuring only owners or staff can manage private layouts while public layouts remain viewable to authenticated users (`LayoutAccessMixin`).
- Filter schema mixin that aggregates block filter schemas according to user-defined layouts and reuses block filter resolution helpers (`LayoutFilterSchemaMixin`).
- Views for listing, creating, renaming, deleting, and editing layouts, including AJAX endpoints to render individual blocks, add blocks, and manage layout filter selections. Views reuse Django class-based views, handle messaging, enforce POST requirements, and rebuild formsets/templates after mutations.
- Forms and helpers that parse JSON payloads, namespace query parameters for embedded blocks, and coordinate with block filter/column config models.

### Key Libraries & Dependencies
- Django class-based views (`TemplateView`, `DeleteView`, `View`), mixins (`LoginRequiredMixin`), forms, and messaging utilities.
- Django ORM transactions and expression wrappers for grid placement calculations.
- Standard library utilities (`json`) and Django template rendering (`render_to_string`).
- Tight coupling with Blocks (registry, models), Permissions (through block usage), and Workflow (via block integrations).

