# Permissions

## Cache clearing

`apps.permissions.checks` caches calls to `User.has_perm` for the life of a
request. To avoid cache leakage between requests you must clear this cache
either via Django's `request_finished` signal or by using the middleware.
The signal hook is registered automatically when `apps.permissions` is in
`INSTALLED_APPS`. If you prefer middleware, add it to your `MIDDLEWARE`
setting:

```python
MIDDLEWARE = [
    # ...
    "apps.permissions.middleware.PermissionCacheMiddleware",
]
```

Either the middleware or the signal hook must be enabled to prevent
unbounded cache growth.

## Temporarily disabling the cache

For cases where clearing the cache is undesirable, the
`disable_perm_cache` context manager bypasses caching within its block.

```python
from apps.permissions.checks import disable_perm_cache

with disable_perm_cache():
    user.has_perm("auth.view_user")
```

This is useful in tests or one-off scripts that require fresh permission
checks. To remove cached results entirely, see
[Cache clearing](#cache-clearing).

## Permission Template Tags

This project exposes template tags that mirror the utilities in
`apps.permissions.checks`. They allow model-, instance-, and field-level
permission checks directly in Django templates so you can conditionally render
UI elements.

```django
{% load permissions_tags %}

{# Model-level check #}
{% if user_can_add_model MyModel %}
    <a href="{% url 'mymodel_add' %}">Add Model</a>
{% endif %}

{# Instance-level check #}
{% if user_can_change_instance object %}
    <a href="{% url 'mymodel_edit' object.pk %}">Edit</a>
{% endif %}

{# Field-level check without an instance #}
{% if user_can_read MyModel 'status' %}
    {{ object.status }}
{% endif %}

{# Field-level check honoring instance-level permissions #}
{% if user_can_write MyModel 'status' object %}
    <!-- render editable field -->
{% endif %}
```

All of these tags delegate to similarly named functions in
`apps.permissions.checks` and return booleans indicating whether the request's
user has the requisite permission. If you need to check permissions for a
different user, pass them as the first argument to the tag. When omitting the
user argument, the template context must include ``request`` so the current
user can be inferred; otherwise pass the user explicitly.

## View Mixins

`ModelPermissionRequiredMixin` and `InstancePermissionRequiredMixin` provide
permission checks for class-based views. Set `permission_action` to the desired
operation (`"view"`, `"add"`, `"change"`, or `"delete"` for model-level
checks).

```python
from django.views.generic import CreateView, DetailView, ListView
from apps.permissions.views import (
    ModelPermissionRequiredMixin,
    InstancePermissionRequiredMixin,
)
from myapp.models import Project

class ProjectListView(ModelPermissionRequiredMixin, ListView):
    model = Project
    permission_action = "view"

class ProjectCreateView(ModelPermissionRequiredMixin, CreateView):
    model = Project
    permission_action = "add"

class ProjectDetailView(InstancePermissionRequiredMixin, DetailView):
    model = Project
    permission_action = "change"

    def get_permission_object(self):
        return self.get_object()
```

## View Decorators

Function-based views can enforce permissions with the
`model_permission_required` and `instance_permission_required` decorators.

```python
from django.shortcuts import get_object_or_404
from apps.permissions.views import (
    model_permission_required,
    instance_permission_required,
)
from myapp.models import Project

@model_permission_required(Project, "view")
def project_list(request):
    ...

@model_permission_required(Project, "add")
def project_create(request):
    ...

@instance_permission_required(lambda request, pk: get_object_or_404(Project, pk=pk), "change")
def project_detail(request, pk):
    ...
```

## Field Utilities

`get_readable_fields` and `get_editable_fields` return the set of field names a
user may view or modify on a model or instance. They are handy when building
custom forms or serializers that should respect field-level permissions.

```python
from apps.permissions.checks import get_readable_fields, get_editable_fields
from myapp.models import Project

readable = get_readable_fields(request.user, Project)
editable = get_editable_fields(request.user, Project, instance=project)
```

These helpers power [PermissionFormMixin](#form-permissions), which removes
unreadable fields and disables uneditable ones automatically.

## Queryset Filtering

To restrict querysets to only those objects a user may act upon, use
`filter_viewable_queryset`, `filter_editable_queryset`, and
`filter_deletable_queryset`.

```python
from apps.permissions.checks import (
    filter_viewable_queryset,
    filter_editable_queryset,
    filter_deletable_queryset,
)
from myapp.models import Project

qs = Project.objects.all()
viewable = filter_viewable_queryset(request.user, qs)
editable = filter_editable_queryset(request.user, qs)
deletable = filter_deletable_queryset(request.user, qs)
```

These utilities pair well with [ModelPermissionRequiredMixin](#view-mixins) to
ensure list views display only objects the user can view, edit, or delete.

## Form Permissions

`PermissionFormMixin` filters form fields based on a user's permissions.
Unreadable fields are removed and uneditable fields are disabled, similar to
the checks provided by the [View Mixins](#view-mixins).

```python
from django import forms
from apps.permissions.forms import PermissionFormMixin
from myapp.models import Project

class ProjectForm(PermissionFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = "__all__"

form = ProjectForm(user=request.user, instance=project)
```

This mixin applies permission logic at the form level and complements the
view-based utilities.

## Rebuilding Field Permissions

Field-level permissions can be regenerated using the
`rebuild_field_permissions` management command. It processes all models by
default but can target a specific app or model.

```bash
# Rebuild for every model
python manage.py rebuild_field_permissions

# Rebuild for an app
python manage.py rebuild_field_permissions --app auth

# Rebuild for a single model
python manage.py rebuild_field_permissions --app auth --model User
```
