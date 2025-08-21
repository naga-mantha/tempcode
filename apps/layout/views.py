from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, FormView, DeleteView
from django import forms
from django.views import View
from django.template.loader import render_to_string

from apps.blocks.registry import block_registry
from apps.layout.models import Layout, LayoutBlock, LayoutFilterConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig

from apps.layout.forms import (
    LayoutForm,
    AddBlockForm,
    LayoutFilterConfigForm,
)

from apps.layout.mixins import LayoutFilterSchemaMixin, LayoutAccessMixin
from apps.layout.helpers.json import parse_json_body
from apps.layout.helpers.formsets import get_layoutblock_formset
from apps.layout.helpers.filters import build_namespaced_get
from apps.layout.constants import RESPONSIVE_COL_FIELDS
from apps.blocks.block_types.table.table_block import TableBlock
from apps.blocks.block_types.chart.chart_block import ChartBlock




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
        context["public_layouts"] = qs.filter(visibility=Layout.VISIBILITY_PUBLIC)
        context["private_layouts"] = qs.filter(
            visibility=Layout.VISIBILITY_PRIVATE, user=self.request.user
        )
        # Provide create form inline on this page
        context["form"] = LayoutForm(user=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        # Handle create layout inline
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
        from apps.layout.helpers.json import parse_json_body
        payload = parse_json_body(request)
        def _get(h, key, default=""):
            if isinstance(h, dict) and h.get(key) is not None:
                return str(h.get(key)).strip()
            v = request.POST.get(key)
            return (v or default).strip()
        new_name = _get(payload, "name")
        new_desc = _get(payload, "description")
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
        layout.save(update_fields=["name", "slug", "description"])  # slug auto-derives on save
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
        self.filter_configs = LayoutFilterConfig.objects.filter(
            layout=self.layout, user=request.user
        ).order_by("-is_default", "name")
        self.active_filter_config = None
        cfg_id = request.GET.get("filter_config_id")
        if cfg_id:
            try:
                self.active_filter_config = self.filter_configs.get(pk=cfg_id)
            except LayoutFilterConfig.DoesNotExist:
                pass
        if not self.active_filter_config:
            self.active_filter_config = self.filter_configs.filter(is_default=True).first()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_schema = self._build_filter_schema(self.request)
        base_values = self.active_filter_config.values if self.active_filter_config else {}
        selected_filter_values = self._collect_filters(
            self.request.GET, filter_schema, base=base_values
        )
        # Render blocks sequentially; Bootstrap will wrap columns
        blocks_list = []
        for lb in self.layout.blocks.select_related("block").order_by("position", "id"):
            block_impl = block_registry.get(lb.block.code)
            if not block_impl:
                # If the block is unregistered, show a compact warning card
                blocks_list.append({
                    "col_classes": lb.bootstrap_col_classes(),
                    "html": f"<div class='alert alert-warning p-2 m-0'>Block '{lb.block.code}' not available.</div>",
                    "block_name": lb.block.name,
                    "id": lb.id,
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
                if cfg:
                    qd[f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__filter_config_id"] = str(cfg.id)
            # Signal to block templates that they are embedded within a layout
            # so they can suppress standalone page headers/footers.
            qd["embedded"] = "1"

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
                "col_classes": lb.bootstrap_col_classes(),
                "html": html,
                "block_name": lb.block.name,
                "id": lb.id,
                "title": getattr(lb, "title", ""),
                "note": getattr(lb, "note", ""),
            })
        can_manage = self.can_manage(self.request.user, self.layout)
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
            }
        )
        return context

class LayoutEditView(LoginRequiredMixin, LayoutAccessMixin, TemplateView):
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
                continue
            # Force Select widget and assign choices to the widget
            widget = forms.Select(attrs={"class": "form-select form-select-sm w-100"})
            widget.choices = choices
            fld.widget = widget
            # Ensure the initial reflects the instance value
            form.initial["preferred_filter_name"] = getattr(form.instance, "preferred_filter_name", "")
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

    def get(self, request, *args, **kwargs):
        formset = self.FormSet(queryset=self.qs)
        self._decorate_formset_filter_dropdowns(formset, request.user)
        add_form = AddBlockForm()
        return self.render_to_response({
            "layout": self.layout,
            "formset": formset,
            "add_form": add_form,
        })



class LayoutFilterConfigView(LoginRequiredMixin, LayoutFilterSchemaMixin, FormView):
    template_name = "layout/layout_filter_config.html"
    form_class = LayoutFilterConfigForm

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = LayoutAccessMixin.get_layout(username=username, slug=slug)
        # Use unified access check for view authorization
        LayoutAccessMixin.ensure_access(request, self.layout, action="view")
        self.user_filters = LayoutFilterConfig.objects.filter(
            layout=self.layout, user=request.user
        ).order_by("-is_default", "name")
        self.editing = None
        if request.method == "GET":
            edit_id = request.GET.get("id")
            if edit_id:
                self.editing = get_object_or_404(
                    LayoutFilterConfig, id=edit_id, layout=self.layout, user=request.user
                )
        self.filter_schema = self._build_filter_schema(request)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Handle deletes before validating the form (since 'name' isn't posted on delete)
        if "delete" in request.POST:
            edit_id = request.POST.get("id")
            if edit_id:
                cfg = get_object_or_404(
                    LayoutFilterConfig,
                    id=edit_id,
                    layout=self.layout,
                    user=request.user,
                )
                try:
                    cfg.delete()
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, "Filter deleted.")
            return redirect(
                "layout_filter_config",
                username=self.layout.user.username,
                slug=self.layout.slug,
            )
        return super().post(request, username, slug, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["filter_schema"] = self.filter_schema
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.editing:
            initial.update(
                {
                    "name": self.editing.name,
                    "is_default": self.editing.is_default,
                }
            )
        return initial

    def form_valid(self, form):
        # We no longer include 'id' in the form; read from POST if present
        edit_id = self.request.POST.get("id")
        name = form.cleaned_data["name"].strip()
        is_default = form.cleaned_data.get("is_default", False)
        if not name:
            messages.error(self.request, "Please provide a name.")
            return redirect("layout_filter_config", username=self.layout.user.username, slug=self.layout.slug)
        values = self._collect_filters(self.request.POST, self.filter_schema, base={})
        if edit_id:
            cfg = get_object_or_404(
                LayoutFilterConfig, id=edit_id, layout=self.layout, user=self.request.user
            )
        else:
            cfg = LayoutFilterConfig(layout=self.layout, user=self.request.user)
        cfg.name = name
        cfg.values = values
        cfg.is_default = is_default
        try:
            cfg.save()
        except IntegrityError:
            messages.error(
                self.request,
                "Filter name already taken. Please choose a different name.",
            )
            if cfg.id:
                return redirect(f"{self.request.path}?id={cfg.id}")
            return redirect("layout_filter_config", username=self.layout.user.username, slug=self.layout.slug)
        messages.success(self.request, "Filter saved.")
        return redirect(f"{self.request.path}?id={cfg.id}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial_values = self.editing.values if self.editing else {}
        context.update(
            {
                "layout": self.layout,
                "user_filters": self.user_filters,
                "editing": self.editing,
                "filter_schema": self.filter_schema,
                "initial_values": initial_values,
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
        # Only allow known fields; normalize to None or int in ALLOWED_COLS
        from apps.layout.constants import ALLOWED_COLS
        INVALID = object()
        def _norm(v):
            if v in (None, "", "null"):
                return None
            try:
                iv = int(v)
            except (TypeError, ValueError):
                return INVALID  # invalid sentinel
            return iv if iv in ALLOWED_COLS else INVALID
        updates = {}
        for key in RESPONSIVE_COL_FIELDS:
            if key in data:
                norm = _norm(data.get(key))
                if norm is INVALID:
                    return JsonResponse({"ok": False, "error": f"Invalid value for {key}."}, status=400)
                updates[key] = norm
        # Allow optional title/note and preferred filter name updates
        if "title" in data:
            updates["title"] = (data.get("title") or "").strip()
        if "note" in data:
            updates["note"] = (data.get("note") or "").strip()
        if "preferred_filter_name" in data:
            updates["preferred_filter_name"] = (data.get("preferred_filter_name") or "").strip()
        if not updates:
            return JsonResponse({"ok": False, "error": "No updatable fields provided."}, status=400)
        for k, v in updates.items():
            setattr(lb, k, v)
        lb.save(update_fields=list(updates.keys()))
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
        from apps.blocks.models.block import Block
        try:
            block_obj = Block.objects.get(code=block_code)
        except Block.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Invalid block."}, status=400)
        # Ensure the block is registered/available
        if not block_registry.get(block_obj.code):
            return JsonResponse({"ok": False, "error": "Block not available."}, status=400)
        # Append at the end
        last = (
            LayoutBlock.objects.filter(layout=layout)
            .order_by("-position")
            .first()
        )
        next_pos = (last.position + 1) if last else 0
        LayoutBlock.objects.create(
            layout=layout,
            block=block_obj,
            position=next_pos,
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
