from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, JsonResponse
import json
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, FormView, DeleteView
from django import forms
from django.views import View
from django.template.loader import render_to_string

from apps.django_bi.blocks.registry import block_registry
from apps.django_bi.layout.models import Layout, LayoutBlock, LayoutFilterConfig
from apps.django_bi.blocks.models.block_filter_config import BlockFilterConfig
from apps.django_bi.blocks.models.block_column_config import BlockColumnConfig

from apps.django_bi.layout.forms import (
    LayoutForm,
    AddBlockForm,
    LayoutFilterConfigForm,
)

from apps.django_bi.layout.mixins import LayoutFilterSchemaMixin, LayoutAccessMixin
from apps.django_bi.layout.helpers.json import parse_json_body
from apps.django_bi.layout.helpers.formsets import get_layoutblock_formset
from apps.django_bi.layout.helpers.filters import build_namespaced_get
from apps.django_bi.blocks.block_types.table.table_block import TableBlock
from apps.django_bi.blocks.block_types.chart.chart_block import ChartBlock




class LayoutDeleteView(LoginRequiredMixin, DeleteView):
    model = Layout
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("layout_list")
    template_name = "layout/layout_confirm_delete.html"

    def get_queryset(self):
        username = self.kwargs.get("username")
        base = Layout.objects.filter(user__username=username)
        if self.request.user.is_staff:
            return base
        return base.filter(user=self.request.user, visibility=Layout.VISIBILITY_PRIVATE)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        layout: Layout = self.object
        is_public = layout.visibility == Layout.VISIBILITY_PUBLIC
        impacted_qs = LayoutFilterConfig.objects.filter(layout=layout).values_list("user__username", flat=True).distinct()
        impacted = list(impacted_qs)
        ctx.update(
            {
                "is_public": is_public,
                "impacted_users_count": len(impacted),
                "impacted_users": impacted[:10],  # show a sample
            }
        )
        return ctx


class LayoutListView(LoginRequiredMixin, TemplateView):
    template_name = "layout/layout_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Layout.objects.filter(
            Q(visibility=Layout.VISIBILITY_PUBLIC)
            | Q(user=self.request.user, visibility=Layout.VISIBILITY_PRIVATE)
        )
        context["public_layouts"] = qs.filter(visibility=Layout.VISIBILITY_PUBLIC).order_by("category", "name")
        context["private_layouts"] = qs.filter(
            visibility=Layout.VISIBILITY_PRIVATE, user=self.request.user
        ).order_by("category", "name")
        # Provide create form inline on this page
        context["form"] = LayoutForm(user=self.request.user)
        return context

    # Creation moved to LayoutCreateView


class LayoutCreateView(LoginRequiredMixin, TemplateView):
    template_name = "layout/layout_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = LayoutForm(user=self.request.user)
        # Provide lists for sidebar
        qs = Layout.objects.filter(
            Q(visibility=Layout.VISIBILITY_PUBLIC)
            | Q(user=self.request.user, visibility=Layout.VISIBILITY_PRIVATE)
        )
        context["public_layouts"] = qs.filter(visibility=Layout.VISIBILITY_PUBLIC).order_by("category", "name")
        context["private_layouts"] = qs.filter(
            visibility=Layout.VISIBILITY_PRIVATE, user=self.request.user
        ).order_by("category", "name")
        return context

    def post(self, request, *args, **kwargs):
        form = LayoutForm(request.POST, user=request.user)
        if form.is_valid():
            layout = form.save(commit=False)
            layout.user = request.user
            if not request.user.is_staff:
                layout.visibility = Layout.VISIBILITY_PRIVATE
            try:
                layout.save()
            except IntegrityError:
                form.add_error("name", "You already have a layout with this name.")
                ctx = self.get_context_data()
                ctx["form"] = form
                return self.render_to_response(ctx)
            return redirect("layout_detail", username=layout.user.username, slug=layout.slug)
        ctx = self.get_context_data()
        ctx["form"] = form
        return self.render_to_response(ctx)


class LayoutRenameView(LoginRequiredMixin, LayoutAccessMixin, View):
    def post(self, request, username, slug, *args, **kwargs):
        layout = self.get_layout(username=username, slug=slug)
        self.ensure_edit_access(request, layout)
        from apps.django_bi.layout.helpers.json import parse_json_body
        payload = parse_json_body(request)
        def _get(h, key, default=""):
            if isinstance(h, dict) and h.get(key) is not None:
                return str(h.get(key)).strip()
            v = request.POST.get(key)
            return (v or default).strip()
        new_name = _get(payload, "name")
        new_desc = _get(payload, "description")
        new_cat = _get(payload, "category")
        # Detect if client expects JSON
        accept = getattr(request, "headers", {}).get("Accept") if hasattr(request, "headers") else request.META.get("HTTP_ACCEPT", "")
        is_ajax = (
            (request.content_type and "application/json" in request.content_type)
            or (accept and "application/json" in accept)
            or request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
        )
        if not new_name:
            if is_ajax:
                return JsonResponse({"ok": False, "error": "Please provide a name."}, status=400)
            messages.error(request, "Please provide a name.")
            return redirect("layout_detail", username=layout.user.username, slug=layout.slug)
        layout.name = new_name
        layout.description = new_desc
        layout.category = new_cat
        layout.save(update_fields=["name", "slug", "description", "category"])  # slug auto-derives on save
        # If JSON/AJAX, return structured response instead of redirect
        if is_ajax:
            return JsonResponse({
                "ok": True,
                "name": layout.name,
                "slug": layout.slug,
                "edit_url": reverse("layout_edit", kwargs={"username": layout.user.username, "slug": layout.slug}),
                "detail_url": reverse("layout_detail", kwargs={"username": layout.user.username, "slug": layout.slug}),
            })
        messages.success(request, "Layout renamed.")
        return redirect("layout_edit", username=layout.user.username, slug=layout.slug)


class LayoutDetailView(LoginRequiredMixin, LayoutAccessMixin, LayoutFilterSchemaMixin, TemplateView):
    template_name = "layout/layout_detail.html"

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = self.get_layout(username=username, slug=slug)
        self.ensure_detail_access(request, self.layout)
        from django.db.models import Q, Case, When, IntegerField
        q = LayoutFilterConfig.objects.filter(layout=self.layout).filter(
            Q(user=request.user) | Q(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC)
        )
        self.filter_configs = q.annotate(
            _vis_order=Case(
                When(visibility=LayoutFilterConfig.VISIBILITY_PRIVATE, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_vis_order", "name")
        self.active_filter_config = None
        cfg_id = request.GET.get("filter_config_id")
        if cfg_id:
            try:
                self.active_filter_config = self.filter_configs.get(pk=cfg_id)
            except LayoutFilterConfig.DoesNotExist:
                pass
        if not self.active_filter_config:
            try:
                self.active_filter_config = (
                    self.filter_configs.filter(user=request.user, is_default=True).first()
                    or self.filter_configs.filter(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC, is_default=True).first()
                    or self.filter_configs.filter(user=request.user).first()
                    or self.filter_configs.filter(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC).first()
                )
            except Exception:
                self.active_filter_config = None
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_schema = self._build_filter_schema(self.request)
        base_values = self.active_filter_config.values if self.active_filter_config else {}
        selected_filter_values = self._collect_filters(
            self.request.GET, filter_schema, base=base_values
        )
        # Render blocks; positions come from saved Gridstack x/y/w/h
        blocks_list = []
        for lb in self.layout.blocks.select_related("block").order_by("position", "id"):
            block_impl = block_registry.get(lb.block.code)
            if not block_impl:
                # If the block is unregistered, show a compact warning card
                blocks_list.append({
                    "x": getattr(lb, "x", 0) or 0,
                    "y": getattr(lb, "y", 0) or 0,
                    "w": getattr(lb, "w", 4) or 4,
                    "h": getattr(lb, "h", 2) or 2,
                    "html": f"<div class='alert alert-warning p-2 m-0'>Block '{lb.block.code}' not available.</div>",
                    "block_name": lb.block.name,
                    "id": lb.id,
                    "wrapper_class": "card p-2",
                    "is_spacer": False,
                })
                continue
            # Build a per-block namespaced GET overlay from selected layout filters
            ns = f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__filters."
            qd = build_namespaced_get(self.request, ns=ns, values=selected_filter_values or {})
            # If this block instance declares a preferred Block filter config name,
            # try to resolve it for the current user and inject it as the per-instance
            # filter_config_id so duplicate blocks can default differently.
            pref_name = (lb.preferred_filter_name or "").strip()
            if pref_name:
                cfg = (
                    BlockFilterConfig.objects.filter(
                        block=lb.block, user=self.request.user, name=pref_name
                    ).only("id").first()
                )
                # Respect explicit user selection in the querystring; only inject
                # the instance default if no selection was provided.
                key = f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__filter_config_id"
                if cfg and key not in self.request.GET:
                    qd[key] = str(cfg.id)
            # If this block instance declares a preferred Block column config name,
            # inject the column_config_id similarly for per-instance default view.
            pref_col = (lb.preferred_column_config_name or "").strip()
            if pref_col:
                col = (
                    BlockColumnConfig.objects.filter(
                        block=lb.block, user=self.request.user, name=pref_col
                    ).only("id").first()
                )
                key_col = f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__column_config_id"
                if col and key_col not in self.request.GET:
                    qd[key_col] = str(col.id)
            # Signal to block templates that they are embedded within a layout
            # so they can suppress standalone page headers/footers.
            qd["embedded"] = "1"
            # Provide per-instance display metadata to block templates so they
            # can render title/notes just below Filter Conditions.
            qd["embedded_title"] = getattr(lb, "title", "") or ""
            qd["embedded_note"] = getattr(lb, "note", "") or ""

            class _ReqProxy:
                def __init__(self, req, get):
                    self._req = req
                    self.GET = get
                def __getattr__(self, item):
                    return getattr(self._req, item)

            proxy_request = _ReqProxy(self.request, qd)
            # Pass a stable per-instance id based on the LayoutBlock id
            try:
                response = block_impl.render(proxy_request, instance_id=str(lb.id))
                try:
                    html = response.content.decode(response.charset or "utf-8")
                except Exception:
                    html = response.content.decode("utf-8", errors="ignore")
            except Exception as exc:
                html = (
                    "<div class='alert alert-danger p-2 m-0'>"
                    f"Error rendering block '{lb.block.name}': {str(exc)}"
                    "</div>"
                )
            blocks_list.append({
                "x": getattr(lb, "x", 0) or 0,
                "y": getattr(lb, "y", 0) or 0,
                "w": getattr(lb, "w", 4) or 4,
                "h": getattr(lb, "h", 2) or 2,
                "html": html,
                "block_name": lb.block.name,
                "id": lb.id,
                "title": getattr(lb, "title", ""),
                "note": getattr(lb, "note", ""),
                "wrapper_class": ("card p-2"),
                "is_spacer": (lb.block.code == "spacer"),
            })
        can_manage = self.can_manage(self.request.user, self.layout)
        # Sidebar lists: private (current user) and all public, ascending by name
        private_qs = Layout.objects.filter(user=self.request.user, visibility=Layout.VISIBILITY_PRIVATE).order_by("category", "name")
        public_qs = Layout.objects.filter(visibility=Layout.VISIBILITY_PUBLIC).order_by("category", "name")
        context.update(
            {
                "layout": self.layout,
                "blocks": blocks_list,
                "filter_schema": filter_schema,
                "selected_filter_values": selected_filter_values,
                "filter_configs": self.filter_configs,
                "active_filter_config_id": self.active_filter_config.id if self.active_filter_config else None,
                "can_edit": can_manage,
                "can_delete": can_manage,
                "private_layouts": private_qs,
                "public_layouts": public_qs,
            }
        )
        return context

class LayoutEditView(LoginRequiredMixin, LayoutAccessMixin, LayoutFilterSchemaMixin, TemplateView):
    template_name = "layout/layout_edit.html"

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = self.get_layout(username=username, slug=slug)
        self.ensure_edit_access(request, self.layout)
        # Limit queryset to this layout's blocks
        self.qs = self.layout.blocks.select_related("block").order_by("position", "id")
        # Formset for editing cols; allow deletion and ordering
        self.FormSet = get_layoutblock_formset()
        return super().dispatch(request, *args, **kwargs)

    def _decorate_formset_filter_dropdowns(self, formset, user):
        for form in formset.forms:
            try:
                block_obj = form.instance.block
            except Exception:
                block_obj = None
            names = []
            if block_obj:
                names = list(
                    BlockFilterConfig.objects.filter(user=user, block=block_obj)
                    .order_by("name")
                    .values_list("name", flat=True)
                )
            choices = [("", "— inherit block default —")] + [(n, n) for n in names]
            fld = form.fields.get("preferred_filter_name")
            if not fld:
                pass
            else:
                # Force Select widget and assign choices to the widget
                widget = forms.Select(attrs={"class": "form-select form-select-sm w-100"})
                widget.choices = choices
                fld.widget = widget
                form.initial["preferred_filter_name"] = getattr(form.instance, "preferred_filter_name", "")
            # Column config choices
            col_names = []
            if block_obj:
                col_names = list(
                    BlockColumnConfig.objects.filter(user=user, block=block_obj)
                    .order_by("name")
                    .values_list("name", flat=True)
                )
            col_choices = [("", "— inherit block default —")] + [(n, n) for n in col_names]
            col_fld = form.fields.get("preferred_column_config_name")
            if col_fld:
                col_widget = forms.Select(attrs={"class": "form-select form-select-sm w-100"})
                col_widget.choices = col_choices
                col_fld.widget = col_widget
                form.initial["preferred_column_config_name"] = getattr(form.instance, "preferred_column_config_name", "")
            # Compute Manage Filters URL for this block type (table/chart)
            manage_url = None
            try:
                impl = block_registry.get(block_obj.code) if block_obj else None
                if isinstance(impl, TableBlock):
                    manage_url = reverse("table_filter_config", kwargs={"block_name": block_obj.code})
                elif isinstance(impl, ChartBlock):
                    manage_url = reverse("chart_filter_config", kwargs={"block_name": block_obj.code})
            except Exception:
                manage_url = None
            # Attach for template usage
            setattr(form, "manage_filters_url", manage_url)
            # Compute Manage Columns URL (only for table blocks)
            manage_cols_url = None
            try:
                if isinstance(impl, TableBlock):
                    manage_cols_url = reverse("column_config_view", kwargs={"block_name": block_obj.code})
            except Exception:
                manage_cols_url = None
            setattr(form, "manage_columns_url", manage_cols_url)

    def get(self, request, *args, **kwargs):
        # Build block render HTML similar to detail view for preview while editing
        filter_schema = self._build_filter_schema(request)
        selected_filter_values = self._collect_filters(request.GET, filter_schema, base={})
        blocks_list = []
        for lb in self.qs:
            block_impl = block_registry.get(lb.block.code)
            if not block_impl:
                blocks_list.append({
                    "id": lb.id,
                    "x": lb.x or 0,
                    "y": lb.y or 0,
                    "w": lb.w or 4,
                    "h": lb.h or 2,
                    "html": f"<div class='alert alert-warning p-2 m-0'>Block '{lb.block.code}' not available.</div>",
                    "title": getattr(lb, "title", ""),
                    "note": getattr(lb, "note", ""),
                })
                continue
            ns = f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__filters."
            qd = build_namespaced_get(request, ns=ns, values=selected_filter_values or {})
            qd["embedded"] = "1"
            qd["embedded_edit"] = "1"
            qd["embedded_title"] = getattr(lb, "title", "") or ""
            qd["embedded_note"] = getattr(lb, "note", "") or ""
            class _ReqProxy:
                def __init__(self, req, get):
                    self._req = req
                    self.GET = get
                def __getattr__(self, item):
                    return getattr(self._req, item)
            proxy_request = _ReqProxy(request, qd)
            try:
                response = block_impl.render(proxy_request, instance_id=str(lb.id))
                try:
                    html = response.content.decode(response.charset or "utf-8")
                except Exception:
                    html = response.content.decode("utf-8", errors="ignore")
            except Exception as exc:
                html = (
                    "<div class='alert alert-danger p-2 m-0'>"
                    f"Error rendering block '{lb.block.name}': {str(exc)}"
                    "</div>"
                )
            blocks_list.append({
                "id": lb.id,
                "x": lb.x or 0,
                "y": lb.y or 0,
                "w": lb.w or 4,
                "h": lb.h or 2,
                "html": html,
                "title": getattr(lb, "title", ""),
                "note": getattr(lb, "note", ""),
                "wrapper_class": ("card p-2"),
                "is_spacer": (lb.block.code == "spacer"),
            })
        add_form = AddBlockForm()
        return self.render_to_response({
            "layout": self.layout,
            "blocks": blocks_list,
            "add_form": add_form
        })



class LayoutFilterConfigView(LoginRequiredMixin, LayoutFilterSchemaMixin, FormView):
    template_name = "layout/layout_filter_config.html"
    form_class = LayoutFilterConfigForm

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = LayoutAccessMixin.get_layout(username=username, slug=slug)
        LayoutAccessMixin.ensure_access(request, self.layout, action="view")
        from django.db.models import Q, Case, When, IntegerField
        qs = LayoutFilterConfig.objects.filter(layout=self.layout).filter(
            Q(user=request.user) | Q(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC)
        )
        self.user_filters = qs.annotate(
            _vis_order=Case(
                When(visibility=LayoutFilterConfig.VISIBILITY_PRIVATE, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_vis_order", "name")
        self.filter_schema = self._build_filter_schema(request)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["filter_schema"] = self.filter_schema
        return kwargs

    def form_valid(self, form):
        action = form.cleaned_data.get("action")
        config_id = form.cleaned_data.get("config_id")
        name = (form.cleaned_data.get("name") or "").strip()

        if action == "create":
            if not name:
                messages.error(self.request, "Please provide a name.")
                return redirect("layout_filter_config", username=self.layout.user.username, slug=self.layout.slug)
            values = self._collect_filters(self.request.POST, self.filter_schema, base={}, prefix="filters.", allow_flat=False)
            existing = LayoutFilterConfig.objects.filter(
                layout=self.layout, user=self.request.user, name=name
            ).first()
            try:
                if existing:
                    existing.values = values
                    # Admins may change visibility
                    vis = (self.request.POST.get("visibility") or "private").lower()
                    if self.request.user.is_staff and vis in dict(LayoutFilterConfig.VISIBILITY_CHOICES):
                        existing.visibility = vis
                    existing.save()
                else:
                    vis = (self.request.POST.get("visibility") or "private").lower()
                    if not self.request.user.is_staff:
                        vis = "private"
                    LayoutFilterConfig.objects.create(
                        layout=self.layout,
                        user=self.request.user,
                        name=name,
                        values=values,
                        visibility=vis,
                    )
            except IntegrityError:
                messages.error(self.request, "Filter name already taken. Please choose a different name.")
        elif action == "delete" and config_id:
            cfg = get_object_or_404(
                LayoutFilterConfig, id=config_id, layout=self.layout, user=self.request.user, visibility=LayoutFilterConfig.VISIBILITY_PRIVATE
            )
            try:
                cfg.delete()
                messages.success(self.request, "Filter deleted.")
            except Exception as exc:
                messages.error(self.request, str(exc))
        elif action == "set_default" and config_id:
            cfg = get_object_or_404(LayoutFilterConfig, id=config_id, layout=self.layout)
            if self.request.user.is_staff and cfg.visibility == LayoutFilterConfig.VISIBILITY_PUBLIC:
                LayoutFilterConfig.objects.filter(layout=self.layout, visibility=LayoutFilterConfig.VISIBILITY_PUBLIC).exclude(id=cfg.id).update(is_default=False)
                cfg.is_default = True
                cfg.save()
            elif cfg.user_id == self.request.user.id and cfg.visibility == LayoutFilterConfig.VISIBILITY_PRIVATE:
                cfg.is_default = True
                cfg.save()
        return redirect("layout_filter_config", username=self.layout.user.username, slug=self.layout.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Build choice-label maps for select-like fields
        labels_by_key = {}
        try:
            for key, cfg in (self.filter_schema or {}).items():
                choices = cfg.get("choices")
                if isinstance(choices, (list, tuple)):
                    labels_by_key[str(key)] = {str(v): str(lbl) for (v, lbl) in choices}
        except Exception:
            pass

        # Build display of saved filter values
        def _fmt_with_schema(key, value):
            cfg = self.filter_schema.get(key, {}) or {}
            ftype = cfg.get("type")
            if isinstance(value, bool):
                return "Yes" if value else "No"
            if ftype in {"select", "multiselect"} and isinstance(cfg.get("choices"), (list, tuple)):
                choice_map = {str(v): str(lbl) for (v, lbl) in cfg.get("choices")}
                if isinstance(value, (list, tuple)):
                    return ", ".join([choice_map.get(str(v), str(v)) for v in value])
                return choice_map.get(str(value), str(value))
            if isinstance(value, (list, tuple)):
                return ", ".join([str(v) for v in value])
            return str(value)

        values_by_id = {}
        for cfg in self.user_filters:
            items = []
            try:
                for k, v in (cfg.values or {}).items():
                    label = str(self.filter_schema.get(k, {}).get("label", k))
                    items.append(f"{label}: {_fmt_with_schema(k, v)}")
            except Exception:
                pass
            values_by_id[cfg.id] = items

        context.update(
            {
                "layout": self.layout,
                "configs": self.user_filters,
                "filter_schema": self.filter_schema,
                "initial_values": {},
                "configs_values_json": json.dumps({cfg.id: cfg.values for cfg in self.user_filters}),
                "configs_values_by_id": values_by_id,
                "schema_choice_labels_json": json.dumps(labels_by_key),
            }
        )
        return context


class LayoutReorderView(LoginRequiredMixin, LayoutAccessMixin, View):
    def post(self, request, username, slug, *args, **kwargs):
        layout = self.get_layout(username=username, slug=slug)
        self.ensure_edit_access(request, layout)
        # Accept JSON payload: {"ordered_ids": [id1, id2, ...]}
        payload = parse_json_body(request)
        ordered_ids = payload.get("ordered_ids") or request.POST.getlist("ordered_ids[]")
        if not ordered_ids:
            return JsonResponse({"ok": False, "error": "No ordering provided."}, status=400)
        # Coerce to ints and validate all belong to this layout
        try:
            ordered_ids = [int(x) for x in ordered_ids]
        except ValueError:
            return JsonResponse({"ok": False, "error": "Invalid id in list."}, status=400)
        qs = list(layout.blocks.filter(id__in=ordered_ids).only("id", "position"))
        if len(qs) != len(ordered_ids):
            return JsonResponse({"ok": False, "error": "One or more blocks not found."}, status=404)
        # Assign positions in the provided order
        from django.db import transaction
        with transaction.atomic():
            for idx, bid in enumerate(ordered_ids):
                # Use update to avoid race when many rows
                LayoutBlock.objects.filter(layout=layout, id=bid).update(position=idx)
        return JsonResponse({"ok": True})


class LayoutBlockUpdateView(LoginRequiredMixin, LayoutAccessMixin, View):
    def post(self, request, username, slug, id, *args, **kwargs):
        layout = self.get_layout(username=username, slug=slug)
        self.ensure_edit_access(request, layout)
        lb = get_object_or_404(LayoutBlock, layout=layout, id=id)
        data = parse_json_body(request)
        updates = {}
        # Accept col_span and row_span as integers within 1..4
        def _norm_span(key):
            if key not in data:
                return None
            try:
                val = int(data.get(key))
            except (TypeError, ValueError):
                return JsonResponse({"ok": False, "error": f"Invalid value for {key}."}, status=400)
            if val < 1 or val > 4:
                return JsonResponse({"ok": False, "error": f"{key} out of range."}, status=400)
            updates[key] = val
            return None
        resp = _norm_span("col_span") or _norm_span("row_span")
        if isinstance(resp, JsonResponse):
            return resp
        # Allow optional title/note and preferred filter name updates
        if "title" in data:
            updates["title"] = (data.get("title") or "").strip()
        if "note" in data:
            updates["note"] = (data.get("note") or "").strip()
        if "preferred_filter_name" in data:
            updates["preferred_filter_name"] = (data.get("preferred_filter_name") or "").strip()
        if "preferred_column_config_name" in data:
            updates["preferred_column_config_name"] = (data.get("preferred_column_config_name") or "").strip()
        if not updates:
            return JsonResponse({"ok": False, "error": "No updatable fields provided."}, status=400)
        for k, v in updates.items():
            setattr(lb, k, v)
        lb.save(update_fields=list(updates.keys()))
        return JsonResponse({"ok": True})


class LayoutGridUpdateView(LoginRequiredMixin, LayoutAccessMixin, View):
    def post(self, request, username, slug, *args, **kwargs):
        layout = self.get_layout(username=username, slug=slug)
        self.ensure_edit_access(request, layout)
        payload = parse_json_body(request)
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            return JsonResponse({"ok": False, "error": "Invalid payload."}, status=400)
        items = payload["items"]
        # Validate and collect updates
        updates = []
        for it in items:
            try:
                bid = int(it.get("id"))
                x = int(it.get("x"))
                y = int(it.get("y"))
                w = int(it.get("w"))
                h = int(it.get("h"))
            except (TypeError, ValueError):
                return JsonResponse({"ok": False, "error": "Invalid item values."}, status=400)
            if w < 1 or w > 12 or h < 1 or h > 12 or x < 0 or y < 0:
                return JsonResponse({"ok": False, "error": "Values out of range."}, status=400)
            updates.append((bid, x, y, w, h))
        # Ensure all ids belong to layout
        valid_ids = set(layout.blocks.filter(id__in=[bid for bid, *_ in updates]).values_list("id", flat=True))
        if len(valid_ids) != len(updates):
            return JsonResponse({"ok": False, "error": "One or more items not found."}, status=404)
        # Apply updates
        for bid, x, y, w, h in updates:
            LayoutBlock.objects.filter(layout=layout, id=bid).update(x=x, y=y, w=w, h=h)
        return JsonResponse({"ok": True})


class LayoutBlockDeleteView(LoginRequiredMixin, LayoutAccessMixin, View):
    def post(self, request, username, slug, id, *args, **kwargs):
        layout = self.get_layout(username=username, slug=slug)
        self.ensure_edit_access(request, layout)
        lb = get_object_or_404(LayoutBlock, layout=layout, id=id)
        lb.delete()
        return JsonResponse({"ok": True})


class LayoutBlockAddView(LoginRequiredMixin, LayoutAccessMixin, View):
    def post(self, request, username, slug, *args, **kwargs):
        layout = self.get_layout(username=username, slug=slug)
        self.ensure_edit_access(request, layout)
        # Accept JSON or form POST; expect 'block' by code or id
        payload = parse_json_body(request)
        block_code = payload.get("block") or request.POST.get("block")
        if not block_code:
            return JsonResponse({"ok": False, "error": "Missing block."}, status=400)
        from apps.django_bi.blocks.models.block import Block
        try:
            block_obj = Block.objects.get(code=block_code)
        except Block.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Invalid block."}, status=400)
        # Ensure the block is registered/available
        if not block_registry.get(block_obj.code):
            return JsonResponse({"ok": False, "error": "Block not available."}, status=400)
        # Append at the visual bottom based on current y+h
        from django.db.models import F, IntegerField, Value, ExpressionWrapper
        qs = LayoutBlock.objects.filter(layout=layout).annotate(
            bottom=ExpressionWrapper((F("y") + F("h")), output_field=IntegerField())
        ).order_by("-bottom")
        max_bottom = qs.first().bottom if qs.exists() else 0
        # Maintain sequence position as well (append at end)
        last = LayoutBlock.objects.filter(layout=layout).order_by("-position").first()
        next_pos = (last.position + 1) if last else 0
        LayoutBlock.objects.create(
            layout=layout,
            block=block_obj,
            position=next_pos,
            # place new widget on the first column, at bottom row
            x=0,
            y=max(0, int(max_bottom) if isinstance(max_bottom, int) else 0),
            w=4,
            h=2,
        )
        # Rebuild formset for updated tbody
        qs = layout.blocks.select_related("block").order_by("position", "id")
        FormSet = get_layoutblock_formset()
        formset = FormSet(queryset=qs)
        # Populate per-row dropdowns for preferred filter
        try:
            # Reuse helper from the edit view class
            LayoutEditView._decorate_formset_filter_dropdowns(self, formset, request.user)
        except Exception:
            pass
        tbody_html = render_to_string(
            "layout/_layout_rows.html",
            {"formset": formset},
            request=request,
        )
        return JsonResponse({"ok": True, "tbody_html": tbody_html})


class LayoutBlockRenderView(LoginRequiredMixin, LayoutAccessMixin, LayoutFilterSchemaMixin, View):
    """AJAX: Render a single block instance within a layout using current query params.

    Returns JSON { html: "..." } with the full block HTML (including scripts),
    so the client can replace the existing block without reloading the page.
    """

    def get(self, request, username, slug, id, *args, **kwargs):
        layout = self.get_layout(username=username, slug=slug)
        # Expose layout on self for LayoutFilterSchemaMixin helpers
        self.layout = layout
        self.ensure_detail_access(request, layout)
        lb = get_object_or_404(LayoutBlock, layout=layout, id=id)
        block_impl = block_registry.get(lb.block.code)
        if not block_impl:
            return JsonResponse(
                {
                    "html": (
                        "<div id='layout-block-%s' class='js-layout-block-root'>"
                        "<div class='alert alert-warning p-2 m-0'>Block '%s' not available.</div>"
                        "</div>" % (id, lb.block.code)
                    )
                }
            )
        # Rebuild layout sidebar filter schema and selected values based on current URL
        from django.db.models import Q, Case, When, IntegerField
        q = LayoutFilterConfig.objects.filter(layout=layout).filter(
            Q(user=request.user) | Q(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC)
        )
        filter_configs = q.annotate(
            _vis_order=Case(
                When(visibility=LayoutFilterConfig.VISIBILITY_PRIVATE, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_vis_order", "name")
        active_cfg = None
        cfg_id = request.GET.get("filter_config_id")
        if cfg_id:
            try:
                active_cfg = filter_configs.get(pk=cfg_id)
            except LayoutFilterConfig.DoesNotExist:
                active_cfg = None
        if not active_cfg:
            try:
                active_cfg = (
                    filter_configs.filter(user=request.user, is_default=True).first()
                    or filter_configs.filter(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC, is_default=True).first()
                    or filter_configs.filter(user=request.user).first()
                    or filter_configs.filter(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC).first()
                )
            except Exception:
                active_cfg = None
        filter_schema = self._build_filter_schema(request)
        base_values = active_cfg.values if active_cfg else {}
        selected_filter_values = self._collect_filters(request.GET, filter_schema, base=base_values)
        # Build namespaced GET params for this block
        ns = f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__filters."
        qd = build_namespaced_get(request, ns=ns, values=selected_filter_values or {})
        # Inject preferred per-instance defaults if not explicitly provided in URL
        pref_name = (lb.preferred_filter_name or "").strip()
        if pref_name:
            from apps.django_bi.blocks.models.block_filter_config import BlockFilterConfig as BFC
            cfg = BFC.objects.filter(block=lb.block, user=request.user, name=pref_name).only("id").first()
            key = f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__filter_config_id"
            if cfg and key not in request.GET:
                qd[key] = str(cfg.id)
        pref_col = (lb.preferred_column_config_name or "").strip()
        if pref_col:
            from apps.django_bi.blocks.models.block_column_config import BlockColumnConfig as BCC
            col = BCC.objects.filter(block=lb.block, user=request.user, name=pref_col).only("id").first()
            key_col = f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__column_config_id"
            if col and key_col not in request.GET:
                qd[key_col] = str(col.id)
        # Embedded marker and display metadata
        qd["embedded"] = "1"
        qd["embedded_title"] = getattr(lb, "title", "") or ""
        qd["embedded_note"] = getattr(lb, "note", "") or ""

        class _ReqProxy:
            def __init__(self, req, get):
                self._req = req
                self.GET = get

            def __getattr__(self, item):
                return getattr(self._req, item)

        proxy_request = _ReqProxy(request, qd)
        try:
            response = block_impl.render(proxy_request, instance_id=str(lb.id))
            try:
                html = response.content.decode(response.charset or "utf-8")
            except Exception:
                html = response.content.decode("utf-8", errors="ignore")
        except Exception as exc:
            html = (
                f"<div id='layout-block-{id}' class='js-layout-block-root'>"
                "<div class='alert alert-danger p-2 m-0'>"
                f"Error rendering block '{lb.block.name}': {str(exc)}"
                "</div></div>"
            )
        return JsonResponse({"html": html})
