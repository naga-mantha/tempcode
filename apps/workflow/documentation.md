# Workflow App Guide

The `apps.workflow` app models finite state workflows for your domain objects
and provides utilities to: define workflows and states, configure allowed
transitions with group-based rules, render transition buttons, enforce
workflow-aware permissions at the instance and field level, and log state
changes.

## Concepts

- Workflow: Links to a Django model (`content_type`) and defines a set of
  named `State` rows and `Transition` edges between them.
- State: A named node in a workflow graph. One state can be marked as the
  start state; end states are informational.
- Transition: A directed edge from `source_state` to `dest_state` with an
  optional set of `allowed_groups` that may trigger it.
- TransitionLog: Immutable audit trail recording who transitioned an object,
  when, and from/to states.
- Model integration: Models can use `WorkflowModelMixin` to store a `workflow`
  and current `workflow_state` and to auto-assign the start state on creation.

## Installation

1) Add the app and include its URL for the generic transition endpoint.

```python
INSTALLED_APPS = [
    # ...
    "apps.workflow",
]

urlpatterns = [
    # ...
    path("workflow/", include("apps.workflow.urls", namespace="workflow")),
]
```

2) Ensure the permissions middleware from the permissions app is installed so
   per-request `has_perm` caching is cleared properly.

```python
MIDDLEWARE = [
    # ...
    "apps.permissions.middleware.PermissionCacheMiddleware",
]
```

## Applying transitions

Use `get_allowed_transitions(obj, user)` to list available transitions from the
current state. Use `apply_transition(obj, name, user, comment="")` to perform
one. A generic POST view is available at
`workflow:workflow_perform_transition`.

```python
from apps.workflow.apply_transition import get_allowed_transitions, apply_transition

transitions = get_allowed_transitions(order, request.user)
apply_transition(order, "approve", request.user, comment="Looks good")
```

Front-end helpers can render buttons for all allowed transitions:

```python
from apps.workflow.frontend import render_transition_buttons
buttons = render_transition_buttons(order, request.user)
# Each item: {label, transition_name, from_state, to_state, url}
```

## Workflow-aware permissions

The workflow app layers state-aware checks on top of the base permissions app.
It reuses model/instance/field checks from `apps.permissions.checks` and adds
state-specific permission codenames:

- Instance-level: `"{app}.{action}_{model}_{state}"`
- Field-level:    `"{app}.{action}_{model}_{field}_{state}"`

where `{state}` is a slugified version of the state name (via Django's
`slugify`), ensuring punctuation and whitespace are normalized.

Helpers in `apps.workflow.permissions` include:

- `can_view_instance_state(user, instance)`
- `can_change_instance_state(user, instance)`
- `can_delete_instance_state(user, instance)`
- `can_read_field_state(user, model, field_name, instance=None)`
- `can_write_field_state(user, model, field_name, instance=None)`
- `filter_viewable_queryset_state(user, queryset, *, chunk_size=2000)`
- `filter_editable_queryset_state(user, queryset, *, chunk_size=2000)`
- `filter_deletable_queryset_state(user, queryset, *, chunk_size=2000)`

Form integration is available via `WorkflowFormMixin` which removes unreadable
fields and disables uneditable ones based on the current state.

```python
from django import forms
from apps.workflow.forms import WorkflowFormMixin

class OrderForm(WorkflowFormMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

form = OrderForm(user=request.user, instance=order)
```

## Generating permissions per state

The signal `apps.workflow.signals.generate_workflow_permissions` creates
instance- and field-level permissions for each workflow state after migrations.
As you add states, re-run migrations to generate the new codenames.

You can also rebuild on demand:

```bash
python manage.py rebuild_workflow_permissions           # all apps/models
python manage.py rebuild_workflow_permissions --app app_label
python manage.py rebuild_workflow_permissions --app app_label --model ModelName
```

Notes:
- Permissions are created for concrete, editable model fields.
- Instance codenames: view/change/delete per state.
- Field codenames: view/change per field per state.

## Queryset filtering

Use the state-aware queryset helpers to limit lists to objects the user may
view/change/delete at their current state. For large datasets, pre-filter with
cheap criteria (e.g., ownership/org) before applying state-aware checks. Tune
`chunk_size` for very large result sets to balance memory vs. DB roundtrips.

## Behavior of staff and superusers

Superusers bypass workflow checks. Staff behavior mirrors the permissions app
via `PERMISSIONS_STAFF_BYPASS` (default True). To require explicit permissions
for staff, set `PERMISSIONS_STAFF_BYPASS = False` in project settings.

Example:

```python
# settings.py
PERMISSIONS_STAFF_BYPASS = False
```

The workflow app reads this setting when evaluating transition and state
checks.

## Template tags

Load `workflow_tags` to check workflow permissions in templates:

```django
{% load workflow_tags %}

{# Instance checks #}
{% if user_can_view_instance_state obj %} ... {% endif %}
{% if user_can_change_instance_state obj %} ... {% endif %}
{% if user_can_delete_instance_state obj %} ... {% endif %}

{# Field checks #}
{% if user_can_read_state Order 'status' order %} {{ order.status }} {% endif %}
{% if user_can_write_state user Order 'status' order %} ... {% endif %}

{# Transition check by name #}
{% if user_can_transition order 'approve' %}
  <form method="post" action="...">...</form>
{% endif %}
```

## Recommendations

- Keep state names concise; they become part of permission codenames.
- Model methods like `can_user_view/change/delete(self, user)` from the
  permissions app continue to apply in addition to state checks.
- For templates, conditionally render transition actions based on
  `get_allowed_transitions` or the `*_state` helpers above.

## Workflow status behavior

- Active: creation and transitions are allowed.
- Deprecated: creation of new objects with a deprecated workflow is blocked; transitions on existing objects remain allowed.
- Inactive: creation and transitions are blocked.
