# Permissions App User Guide

The `permissions` app enhances Django's built-in permission system with
caching, field-level checks and a set of utilities that make permission-aware
UI and APIs easier to build. This document walks through the main features with
examples you can adapt to your own models.

## Installation

1. Add the app and its signal handlers:

```python
INSTALLED_APPS = [
    # ...
    "apps.permissions",
]
```

2. Clear the per-request permission cache by adding the middleware. Without it,
   calls to `User.has_perm` accumulate for the life of the process.

```python
MIDDLEWARE = [
    # ...
    "apps.permissions.middleware.PermissionCacheMiddleware",
]
```

After migrations the app automatically creates view/change permissions for each
editable field. Use the management command at the end of this guide to rebuild
them on demand.

## Permission cache

`apps.permissions.checks` caches `user.has_perm` calls during a request. Clear
stale results with `clear_perm_cache()` or let the middleware do it for you. To
bypass caching temporarily use the `disable_perm_cache` context manager.

```python
from apps.permissions.checks import disable_perm_cache

with disable_perm_cache():
    request.user.has_perm("auth.view_user")  # fresh permission check
```

## Template tags

Load `permissions_tags` to check permissions directly in templates. Omitting
the user argument uses the current request user; otherwise pass a user
explicitly.

```django
{% load permissions_tags %}

{% if user_can_add_model Project %}
  <a href="{% url 'project_add' %}">Add Project</a>
{% endif %}

{% if user_can_change_instance project %}
  <a href="{% url 'project_edit' project.pk %}">Edit</a>
{% endif %}

{% if user_can_read Project 'status' %}
  {{ project.status }}
{% endif %}
```

## View helpers

### Class-based views

`ModelPermissionRequiredMixin` and `InstancePermissionRequiredMixin` check model
and instance permissions respectively.

```python
from django.views.generic import DetailView, ListView
from apps.permissions.views import (
    ModelPermissionRequiredMixin,
    InstancePermissionRequiredMixin,
)
from myapp.models import Project

class ProjectListView(ModelPermissionRequiredMixin, ListView):
    model = Project
    permission_action = "view"

class ProjectDetailView(InstancePermissionRequiredMixin, DetailView):
    model = Project
    permission_action = "change"

    def get_permission_object(self):
        return self.get_object()
```

### Function-based views

Use decorators for function views. The example below restricts a `Task` detail
view to users who can delete the task.

```python
from django.shortcuts import get_object_or_404
from apps.permissions.views import instance_permission_required
from myapp.models import Task

@instance_permission_required(lambda request, pk: get_object_or_404(Task, pk=pk), "delete")
def task_detail(request, pk):
    ...
```

## Field utilities

Field-level checks allow you to hide or disable individual fields based on
permissions.

```python
from apps.permissions.checks import get_editable_fields, get_readable_fields
from myapp.models import Article

readable = get_readable_fields(request.user, Article)
editable = get_editable_fields(request.user, Article, instance=article)
```

## Queryset filtering

Limit querysets to objects a user may view, change or delete. This pairs well
with list views.

```python
from apps.permissions.checks import filter_viewable_queryset
from myapp.models import Project

qs = Project.objects.all()
viewable = filter_viewable_queryset(request.user, qs)
```

## Form mixin

`PermissionFormMixin` removes unreadable fields and disables uneditable ones. It
expects a `user` keyword argument.

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

## Rebuilding field permissions

Run the management command to regenerate field-level permissions.

```bash
# All models
python manage.py rebuild_field_permissions

# Specific app
python manage.py rebuild_field_permissions --app blog

# Single model
python manage.py rebuild_field_permissions --app blog --model Article
```

These utilities provide a flexible foundation for permission-aware
applications. Use them to tailor visibility and editability of data throughout
your project.
