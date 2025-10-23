"""View-level permission utilities.

This module provides mixins and decorators to enforce permissions in
Django views. Supported actions include ``"view"``, ``"add"``, ``"change"``,
and ``"delete"``.

Usage with class-based views::

    from django.views.generic import CreateView, DetailView, ListView
    from apps.django_bi.permissions.views import (
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

Usage with function-based views::

    from django.shortcuts import get_object_or_404
    from apps.django_bi.permissions.views import (
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
"""

from functools import wraps
from typing import Callable

from django.core.exceptions import PermissionDenied

from .checks import get_instance_check, get_model_check


class ModelPermissionRequiredMixin:
    """Mixin enforcing model-level permissions for class-based views.

    Valid ``permission_action`` values are ``"view"``, ``"add"``, ``"change"``,
    and ``"delete"``.
    """

    permission_action = "view"
    permission_model = None

    def dispatch(self, request, *args, **kwargs):
        action = getattr(self, "permission_action", "view")
        model = self.permission_model or getattr(self, "model", None)
        if not model:
            raise ValueError(
                "ModelPermissionRequiredMixin requires 'permission_model' or 'model'"
            )

        check_func = get_model_check(action)

        if not check_func(request.user, model):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class InstancePermissionRequiredMixin:
    """Mixin enforcing instance-level permissions for class-based views."""

    permission_action = "view"
    permission_object = None

    def get_permission_object(self):
        return self.permission_object

    def dispatch(self, request, *args, **kwargs):
        action = getattr(self, "permission_action", "view")
        instance = self.get_permission_object()
        if instance is None:
            raise ValueError(
                "InstancePermissionRequiredMixin requires a permission object; "
                "override 'get_permission_object'."
            )

        check_func = get_instance_check(action)

        if not check_func(request.user, instance):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


def model_permission_required(model, action: str = "view"):
    """Decorator for function-based views enforcing model-level permissions.

    Parameters
    ----------
    model:
        The model class to check permissions against.
    action:
        Permission action to check (``"view"``, ``"add"``, ``"change"``, or ``"delete"``).
    """

    def decorator(view_func: Callable):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            check_func = get_model_check(action)
            if not check_func(request.user, model):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def instance_permission_required(get_instance: Callable, action: str = "view"):
    """Decorator enforcing instance-level permissions for function-based views.

    Parameters
    ----------
    get_instance:
        Callable receiving ``(request, *args, **kwargs)`` and returning the
        object to check permissions against.
    action:
        Permission action to check (``"view"``, ``"change"``, or ``"delete"``).
    """

    def decorator(view_func: Callable):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            instance = get_instance(request, *args, **kwargs)
            check_func = get_instance_check(action)
            if not check_func(request.user, instance):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
