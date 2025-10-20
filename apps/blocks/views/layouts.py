"""Class-based views for managing dashboard layouts."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
    QueryDict,
)
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import generic
from django.views.generic.detail import SingleObjectMixin

from apps.blocks.controller import BlockController
from apps.blocks.forms.layout_filters import LayoutFilterConfigForm
from apps.blocks.forms.layouts import LayoutBlockFormSet, LayoutForm
from apps.blocks.models.block import Block
from apps.blocks.models.layout import Layout, VisibilityChoices
from apps.blocks.models.layout_block import LayoutBlock
from apps.blocks.models.layout_filter_config import LayoutFilterConfig
from apps.blocks.policy import PolicyService
from apps.blocks.register import load_specs
from apps.blocks.registry import get_registry
from apps.blocks.services.layout_filters import (
    aggregate_layout_filter_metadata,
    choose_layout_filter_config,
    extract_layout_filter_values,
    duplicate_layout_filter_config,
    list_layout_filter_configs,
    merge_layout_filter_values,
    parse_request_filter_overrides,
)
from apps.blocks.services.layouts import (
    DEFAULT_GRID_HEIGHT,
    DEFAULT_GRID_WIDTH,
    LayoutGridstackSerializer,
    get_grid_settings,
)


log = logging.getLogger(__name__)


FILTER_PANEL_WRAPPER_ID = "layoutFilterPanelWrapper"
FILTER_OFFCANVAS_ID = "layoutFilterOffcanvas"


def _resolve_block_template_name(spec) -> str:
    """Choose the correct partial template for a block spec."""

    if getattr(spec, "kind", None) == "table":
        return "blocks/table/table_card.html"
    if getattr(spec, "kind", None) == "pivot":
        return "blocks/pivot/pivot_card.html"
    return spec.template


def render_layout_grid_item(
    request,
    layout_block: LayoutBlock,
    *,
    registry=None,
    policy: PolicyService | None = None,
) -> str:
    """Render a layout block wrapped in grid metadata markup."""

    if registry is None:
        load_specs()
        registry = get_registry()
    layout = layout_block.layout
    spec = registry.get(layout_block.block.code)

    remove_url = reverse(
        "blocks:layout_block_remove",
        kwargs={
            "username": layout.owner.username,
            "slug": layout.slug,
            "block_slug": layout_block.slug,
        },
    )

    if spec is None:
        inner_html = (
            "<div class=\"alert alert-warning mb-0\">"
            f"Block template '{layout_block.block.code}' is unavailable."
            "</div>"
        )
    else:
        policy = policy or PolicyService()
        controller = BlockController(spec, policy)
        try:
            context = controller.build_context(request)
            context.update({
                "layout": layout,
                "layout_block": layout_block,
            })
            inner_html = render_to_string(
                _resolve_block_template_name(spec),
                context,
                request=request,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            log.exception("Failed to render block %s", layout_block.block.code)
            inner_html = (
                "<div class=\"alert alert-danger mb-0\">"
                "Unable to render this block. Please try again later."
                "</div>"
            )

    wrapper_context = {
        "layout_block": layout_block,
        "grid": get_grid_settings(layout_block),
        "inner_html": inner_html,
        "remove_url": remove_url,
    }
    return render_to_string(
        "blocks/layouts/_grid_item.html",
        wrapper_context,
        request=request,
    )


def render_layout_display_block(
    request,
    layout_block: LayoutBlock,
    *,
    registry=None,
    policy: PolicyService | None = None,
    filters: Dict[str, Any] | None = None,
) -> str:
    """Render a read-only layout block card with optional filter overrides."""

    if registry is None:
        load_specs()
        registry = get_registry()

    layout = layout_block.layout
    spec = registry.get(layout_block.block.code)

    if spec is None:
        inner_html = (
            "<div class=\"alert alert-warning mb-0\">"
            f"Block template '{layout_block.block.code}' is unavailable."
            "</div>"
        )
    else:
        policy = policy or PolicyService()
        controller = BlockController(spec, policy)
        original_get = request.GET
        try:
            query = QueryDict("", mutable=True)
            for key, value in (filters or {}).items():
                if value in (None, ""):
                    continue
                name = f"filters.{key}"
                if isinstance(value, (list, tuple)):
                    for item in value:
                        if item in (None, ""):
                            continue
                        query.appendlist(name, str(item))
                else:
                    query[name] = str(value)
            request.GET = query
            context = controller.build_context(
                request,
                dom_ns=layout_block.slug,
                allow_request_overrides=False,
            )
            context.update({
                "layout": layout,
                "layout_block": layout_block,
            })
            inner_html = render_to_string(
                _resolve_block_template_name(spec),
                context,
                request=request,
            )
        except Exception:  # pragma: no cover - defensive logging
            log.exception("Failed to render block %s", layout_block.block.code)
            inner_html = (
                "<div class=\"alert alert-danger mb-0\">"
                "Unable to render this block. Please try again later."
                "</div>"
            )
        finally:
            request.GET = original_get

    wrapper_context = {
        "layout_block": layout_block,
        "layout": layout,
        "inner_html": inner_html,
    }
    return render_to_string(
        "blocks/layouts/_block_card.html",
        wrapper_context,
        request=request,
    )


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


class LayoutOwnerPermissionMixin(LayoutUserSlugMixin):
    """Mixin enforcing owner/staff permissions for layout mutations."""

    def get_object(self, queryset=None):  # type: ignore[override]
        obj = super().get_object(queryset)
        if not (self.request.user.is_staff or obj.owner_id == self.request.user.id):
            raise PermissionDenied("You do not have permission to modify this layout.")
        return obj


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


class LayoutEditView(LayoutOwnerPermissionMixin, generic.UpdateView):
    """Update an existing layout along with any associated blocks."""

    form_class = LayoutForm
    template_name = "blocks/layouts/form.html"
    context_object_name = "layout"
    formset_class = LayoutBlockFormSet

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        context = super().get_context_data(**kwargs)
        context.setdefault("block_formset", self._build_formset())
        context.update(self._grid_context())
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

    def _grid_context(self) -> Dict[str, Any]:
        layout = getattr(self, "object", None)
        if layout is None or not layout.pk:
            return {
                "available_block_specs": [],
                "layout_grid_items": [],
                "layout_block_add_url": "",
                "layout_block_update_url": "",
                "layout_grid_margin": 15,
                "layout_grid_empty_message": "No blocks have been added yet.",
                "layout_block_defaults": {
                    "width": DEFAULT_GRID_WIDTH,
                    "height": DEFAULT_GRID_HEIGHT,
                },
            }

        load_specs()
        registry = get_registry()
        overrides = {
            block.code: block
            for block in Block.objects.filter(code__in=registry.keys())
        }

        available_specs: List[Dict[str, Any]] = []
        for spec_id, spec in registry.items():
            override = overrides.get(spec_id)
            if override and override.enabled is False:
                continue
            name = spec.name
            description = spec.description
            if override and override.override_display:
                name = override.name or name
                description = override.description or description
            available_specs.append(
                {
                    "id": spec_id,
                    "name": name,
                    "description": description,
                    "category": spec.category or "General",
                }
            )

        available_specs.sort(key=lambda item: (item["category"], item["name"].lower()))

        policy = PolicyService()
        layout_blocks = list(
            layout.layout_blocks.select_related("block").order_by("order", "pk")
        )
        rendered_items = [
            render_layout_grid_item(
                self.request,
                block,
                registry=registry,
                policy=policy,
            )
            for block in layout_blocks
        ]

        base_kwargs = {"username": layout.owner.username, "slug": layout.slug}
        return {
            "available_block_specs": available_specs,
            "layout_grid_items": rendered_items,
            "layout_block_add_url": reverse("blocks:layout_block_add", kwargs=base_kwargs),
            "layout_block_update_url": reverse(
                "blocks:layout_block_update", kwargs=base_kwargs
            ),
            "layout_grid_margin": 15,
            "layout_grid_empty_message": "No blocks have been added yet.",
            "layout_block_defaults": {
                "width": DEFAULT_GRID_WIDTH,
                "height": DEFAULT_GRID_HEIGHT,
            },
        }

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

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        context = super().get_context_data(**kwargs)
        layout: Layout = context.get("layout")
        request = self.request

        policy = PolicyService()
        configs = list(list_layout_filter_configs(layout, request.user))
        identifier = request.GET.get("layout_filter")
        active_config = choose_layout_filter_config(
            layout,
            request.user,
            identifier=identifier,
            configs=configs,
        )
        base_values = extract_layout_filter_values(active_config)
        overrides = parse_request_filter_overrides(request)
        merged_values = merge_layout_filter_values(base_values, overrides)

        filter_blocks = list(
            aggregate_layout_filter_metadata(
                layout,
                user=request.user,
                policy=policy,
                values=merged_values,
            )
        )
        block_value_lookup = {meta.slug: meta.initial_values for meta in filter_blocks}

        load_specs()
        registry = get_registry()

        rendered_blocks: List[Dict[str, Any]] = []
        for block in layout.layout_blocks.select_related("block").order_by("order", "pk"):
            rendered_blocks.append(
                {
                    "slug": block.slug,
                    "title": block.title or block.block.name,
                    "html": render_layout_display_block(
                        request,
                        block,
                        registry=registry,
                        policy=policy,
                        filters=block_value_lookup.get(block.slug, {}),
                    ),
                }
            )

        panel_url = reverse(
            "blocks:layout_filter_panel",
            kwargs={
                "username": layout.owner.username,
                "slug": layout.slug,
            },
        )
        panel_query = request.GET.urlencode()
        if panel_query:
            panel_hx_url = f"{panel_url}?{panel_query}"
        else:
            active_slug = getattr(active_config, "slug", "")
            panel_hx_url = (
                f"{panel_url}?layout_filter={active_slug}"
                if active_slug
                else panel_url
            )
        detail_url = reverse(
            "blocks:layout_detail",
            kwargs={
                "username": layout.owner.username,
                "slug": layout.slug,
            },
        )

        context.update(
            {
                "layout_filter_configs": configs,
                "active_layout_filter_config": active_config,
                "active_layout_filter_slug": getattr(active_config, "slug", ""),
                "layout_filter_blocks": filter_blocks,
                "layout_filter_panel_url": panel_url,
                "layout_filter_panel_hx_url": panel_hx_url,
                "layout_filter_form_action": detail_url,
                "filter_offcanvas_id": FILTER_OFFCANVAS_ID,
                "filter_panel_wrapper_id": FILTER_PANEL_WRAPPER_ID,
                "has_filter_blocks": any(meta.has_filters for meta in filter_blocks),
                "rendered_layout_blocks": rendered_blocks,
            }
        )
        return context


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


class LayoutFilterManageView(LayoutOwnerPermissionMixin, generic.DetailView):
    """Render the manage filters interface for a layout."""

    template_name = "blocks/layouts/manage_filters.html"
    context_object_name = "layout"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        context = super().get_context_data(**kwargs)
        layout: Layout = context.get("layout")
        request = self.request

        configs = list(list_layout_filter_configs(layout, request.user))
        identifier = (
            request.GET.get("config")
            or request.GET.get("layout_filter")
            or request.GET.get("filter_config_id")
        )
        active_config = choose_layout_filter_config(
            layout,
            request.user,
            identifier=identifier,
            configs=configs,
        )

        values = extract_layout_filter_values(active_config)
        filter_blocks = list(
            aggregate_layout_filter_metadata(
                layout,
                user=request.user,
                policy=PolicyService(),
                values=values,
            )
        )

        context.update(
            {
                "layout_filter_configs": configs,
                "layout_filter_blocks": filter_blocks,
                "active_layout_filter_config": active_config,
                "active_layout_filter_slug": getattr(active_config, "slug", ""),
                "active_layout_filter_name": getattr(active_config, "name", ""),
                "active_layout_filter_visibility": getattr(
                    active_config,
                    "visibility",
                    VisibilityChoices.PRIVATE,
                ),
                "active_layout_filter_is_default": bool(
                    getattr(active_config, "is_default", False)
                ),
            }
        )
        return context


class LayoutFilterConfigHTMXMixin(LayoutOwnerPermissionMixin, SingleObjectMixin):
    """Shared helpers for HTMX responses used by layout filter config views."""

    def _render_saved_filters(self, layout: Layout) -> HttpResponse:
        configs = list(list_layout_filter_configs(layout, self.request.user))
        html = render_to_string(
            "blocks/layouts/_saved_filters.html",
            {
                "layout": layout,
                "layout_filter_configs": configs,
                "request": self.request,
            },
            request=self.request,
        )
        return HttpResponse(html)


class LayoutFilterConfigSaveView(LayoutFilterConfigHTMXMixin, generic.View):
    """Persist filter configurations submitted from the manage filters page."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        layout = self.get_object()
        form = LayoutFilterConfigForm(
            data=request.POST,
            layout=layout,
            acting_user=request.user,
        )
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                return self._render_saved_filters(layout)
            return HttpResponse(status=204)
        return JsonResponse({"errors": form.errors}, status=400)


class LayoutFilterConfigRenameView(LayoutFilterConfigHTMXMixin, generic.View):
    """Rename an existing layout filter configuration."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        layout = self.get_object()
        config = get_object_or_404(
            LayoutFilterConfig,
            pk=kwargs.get("config_id"),
            layout=layout,
        )
        new_name = (request.POST.get("name") or "").strip()
        if not new_name:
            return HttpResponseBadRequest("Name is required")
        config.name = new_name
        try:
            config.save(update_fields=["name", "updated_at"])
        except IntegrityError:
            return HttpResponseBadRequest("A filter with this name already exists.")
        if request.headers.get("HX-Request"):
            return self._render_saved_filters(layout)
        return HttpResponse(status=204)


class LayoutFilterConfigDuplicateView(LayoutFilterConfigHTMXMixin, generic.View):
    """Duplicate a layout filter configuration as a new private entry."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        layout = self.get_object()
        config = get_object_or_404(
            LayoutFilterConfig,
            pk=kwargs.get("config_id"),
            layout=layout,
        )
        duplicate_layout_filter_config(config)
        if request.headers.get("HX-Request"):
            return self._render_saved_filters(layout)
        return HttpResponse(status=204)


class LayoutFilterConfigDeleteView(LayoutFilterConfigHTMXMixin, generic.View):
    """Delete a layout filter configuration."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        layout = self.get_object()
        config = get_object_or_404(
            LayoutFilterConfig,
            pk=kwargs.get("config_id"),
            layout=layout,
        )
        config.delete()
        if request.headers.get("HX-Request"):
            return self._render_saved_filters(layout)
        return HttpResponse(status=204)


class LayoutFilterConfigMakeDefaultView(LayoutFilterConfigHTMXMixin, generic.View):
    """Mark a layout filter configuration as the default for the owner."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        layout = self.get_object()
        config = get_object_or_404(
            LayoutFilterConfig,
            pk=kwargs.get("config_id"),
            layout=layout,
        )
        config.is_default = True
        config.save(update_fields=["is_default"])
        if request.headers.get("HX-Request"):
            return self._render_saved_filters(layout)
        return HttpResponse(status=204)


class LayoutFilterPanelView(LayoutUserSlugMixin, generic.DetailView):
    """HTMX endpoint rendering the filter offcanvas panel."""

    template_name = "blocks/layouts/_filter_sidebar.html"
    context_object_name = "layout"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        context = super().get_context_data(**kwargs)
        layout: Layout = context.get("layout")

        configs = list(list_layout_filter_configs(layout, self.request.user))
        identifier = self.request.GET.get("config") or self.request.GET.get("layout_filter")
        active_config = choose_layout_filter_config(
            layout,
            self.request.user,
            identifier=identifier,
            configs=configs,
        )

        base_values = extract_layout_filter_values(active_config)
        reset_requested = self.request.GET.get("reset") in {"1", "true", "True"}
        overrides = (
            {}
            if reset_requested
            else parse_request_filter_overrides(self.request)
        )
        merged_values = merge_layout_filter_values(base_values, overrides)

        filter_blocks = list(
            aggregate_layout_filter_metadata(
                layout,
                user=self.request.user,
                policy=PolicyService(),
                values=merged_values,
            )
        )

        panel_url = reverse(
            "blocks:layout_filter_panel",
            kwargs={
                "username": layout.owner.username,
                "slug": layout.slug,
            },
        )
        detail_url = reverse(
            "blocks:layout_detail",
            kwargs={
                "username": layout.owner.username,
                "slug": layout.slug,
            },
        )

        context.update(
            {
                "layout_filter_configs": configs,
                "active_layout_filter_config": active_config,
                "active_layout_filter_slug": getattr(active_config, "slug", ""),
                "layout_filter_blocks": filter_blocks,
                "layout_filter_panel_url": panel_url,
                "layout_filter_form_action": detail_url,
                "filter_offcanvas_id": FILTER_OFFCANVAS_ID,
                "filter_panel_wrapper_id": FILTER_PANEL_WRAPPER_ID,
                "has_filter_blocks": any(meta.has_filters for meta in filter_blocks),
                "is_htmx": self.request.headers.get("HX-Request", "").lower() == "true",
            }
        )
        return context


class LayoutBlockAddView(LayoutOwnerPermissionMixin, generic.View):
    """HTMX endpoint for instantiating new layout blocks."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        layout = self.get_object()
        try:
            payload = self._parse_payload(request)
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))

        spec_id = payload.get("spec_id")
        if not spec_id:
            return HttpResponseBadRequest("spec_id is required")

        load_specs()
        registry = get_registry()
        spec = registry.get(spec_id)
        if spec is None:
            return HttpResponseBadRequest("Unknown block specification")

        title = payload.get("title") or spec.name
        width = payload.get("width", DEFAULT_GRID_WIDTH)
        height = payload.get("height", DEFAULT_GRID_HEIGHT)

        serializer = LayoutGridstackSerializer(layout)
        try:
            blocks = serializer.save(
                [
                    {
                        "spec_id": spec_id,
                        "title": title,
                        "configuration": payload.get("configuration"),
                        "settings": payload.get("settings"),
                        "x": payload.get("x", 0),
                        "y": payload.get("y", layout.layout_blocks.count()),
                        "width": width,
                        "height": height,
                        "order": layout.layout_blocks.count(),
                    }
                ]
            )
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))

        rendered = render_layout_grid_item(
            request,
            blocks[0],
            registry=registry,
            policy=PolicyService(),
        )
        return HttpResponse(rendered)

    def _parse_payload(self, request) -> Dict[str, Any]:
        if request.content_type and "application/json" in request.content_type:
            try:
                data = json.loads(request.body.decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ValueError("Invalid JSON payload") from exc
            if not isinstance(data, dict):
                raise ValueError("JSON payload must be an object")
            return data

        data = request.POST.dict()
        configuration = data.get("configuration")
        if configuration:
            try:
                data["configuration"] = json.loads(configuration)
            except json.JSONDecodeError:
                data["configuration"] = {}
        return data


class LayoutBlockUpdateView(LayoutOwnerPermissionMixin, generic.View):
    """Persist block position/size updates from the Gridstack UI."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        layout = self.get_object()
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")

        nodes = data.get("blocks") or data.get("nodes")
        if not isinstance(nodes, list):
            return HttpResponseBadRequest("blocks must be a list")

        serializer = LayoutGridstackSerializer(layout)
        try:
            serializer.save(nodes)
        except ValueError as exc:
            return HttpResponseBadRequest(str(exc))

        return JsonResponse({"status": "ok"})


class LayoutBlockRemoveView(LayoutOwnerPermissionMixin, generic.View):
    """Remove a layout block instance."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        layout = self.get_object()
        block_slug = kwargs.get("block_slug")
        block = get_object_or_404(
            LayoutBlock.objects.select_related("block"),
            layout=layout,
            slug=block_slug,
        )
        block.delete()
        return HttpResponse("")
