"""Class-based views for managing dashboard layouts."""

from __future__ import annotations

from typing import Any, Dict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import generic

from apps.blocks.forms.layouts import LayoutBlockFormSet, LayoutForm
from apps.blocks.models.layout import Layout, VisibilityChoices


class LayoutAccessMixin(LoginRequiredMixin):
    """Base mixin supplying the default queryset for layout views."""

    model = Layout
    context_object_name = "layout"

    def get_queryset(self):
        user = self.request.user
        base = Layout.objects.select_related("owner")
        if user.is_staff:
            return base
        return base.filter(Q(owner=user) | Q(visibility=VisibilityChoices.PUBLIC))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("user", self.request.user)
        return kwargs


class LayoutUserSlugMixin(LayoutAccessMixin):
    """Mixin filtering querysets by ``username``/``slug`` URL kwargs."""

    slug_url_kwarg = "slug"

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        username = self.kwargs.get("username")
        if username:
            qs = qs.filter(owner__username=username)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if slug:
            qs = qs.filter(slug=slug)
        return qs


class LayoutListView(LayoutAccessMixin, generic.ListView):
    """Display layouts available to the current user."""

    template_name = "blocks/layouts/list.html"
    context_object_name = "layouts"
    paginate_by = 20

    def get_queryset(self):  # type: ignore[override]
        qs = super().get_queryset()
        user = self.request.user
        return (
            qs.annotate(
                ownership_priority=Case(
                    When(owner=user, visibility=VisibilityChoices.PRIVATE, then=Value(0)),
                    When(owner=user, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                )
            )
            .order_by("ownership_priority", "owner__username", "name")
            .distinct()
        )


class LayoutCreateView(LayoutAccessMixin, generic.CreateView):
    """Create a new layout owned by the requesting user."""

    form_class = LayoutForm
    template_name = "blocks/layouts/form.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        if form is not None:
            context.setdefault("layout", form.instance)
        context.setdefault("block_formset", None)
        return context

    def form_valid(self, form: LayoutForm) -> HttpResponse:
        self.object = form.save()
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:  # type: ignore[override]
        return reverse(
            "blocks:layout_edit",
            kwargs={
                "username": self.object.owner.username,
                "slug": self.object.slug,
            },
        )


class LayoutEditView(LayoutUserSlugMixin, generic.UpdateView):
    """Update an existing layout along with any associated blocks."""

    form_class = LayoutForm
    template_name = "blocks/layouts/form.html"
    context_object_name = "layout"
    formset_class = LayoutBlockFormSet

    def get_object(self, queryset=None):  # type: ignore[override]
        obj = super().get_object(queryset)
        if not (self.request.user.is_staff or obj.owner_id == self.request.user.id):
            raise PermissionDenied("You do not have permission to modify this layout.")
        return obj

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        context = super().get_context_data(**kwargs)
        if "block_formset" not in context:
            context["block_formset"] = self._build_formset()
        return context

    def _formset_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "instance": self.object,
            "user": self.request.user,
        }
        if self.request.method in {"POST", "PUT"}:
            kwargs.update({
                "data": self.request.POST,
                "files": self.request.FILES,
            })
        return kwargs

    def _build_formset(self):
        return self.formset_class(**self._formset_kwargs())

    def form_valid(self, form: LayoutForm) -> HttpResponse:
        formset = self.formset_class(**self._formset_kwargs())
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, block_formset=formset))
        self.object = form.save()
        formset.instance = self.object
        formset.save()
        return redirect(self.get_success_url())

    def get_success_url(self) -> str:  # type: ignore[override]
        return reverse(
            "blocks:layout_edit",
            kwargs={
                "username": self.object.owner.username,
                "slug": self.object.slug,
            },
        )


class LayoutDetailView(LayoutUserSlugMixin, generic.DetailView):
    """Render the detail view for a layout."""

    template_name = "blocks/layouts/detail.html"
    context_object_name = "layout"


class LayoutDeleteView(LayoutUserSlugMixin, generic.DeleteView):
    """Delete an existing layout after confirming ownership."""

    template_name = "blocks/layouts/confirm_delete.html"
    context_object_name = "layout"

    def get_object(self, queryset=None):  # type: ignore[override]
        obj = super().get_object(queryset)
        if not (self.request.user.is_staff or obj.owner_id == self.request.user.id):
            raise PermissionDenied("You do not have permission to delete this layout.")
        return obj

    def get_success_url(self) -> str:  # type: ignore[override]
        return reverse("blocks:layout_list")


class LayoutFilterManageView(LayoutUserSlugMixin, generic.DetailView):
    """Placeholder view for managing filter configurations on a layout."""

    template_name = "blocks/layouts/manage_filters.html"
    context_object_name = "layout"

    def get_object(self, queryset=None):  # type: ignore[override]
        obj = super().get_object(queryset)
        if not (self.request.user.is_staff or obj.owner_id == self.request.user.id):
            raise PermissionDenied("You do not have permission to manage filters for this layout.")
        return obj
