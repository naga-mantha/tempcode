from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView, DeleteView
from django.views import View
from django.template.loader import render_to_string

from apps.blocks.registry import block_registry
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
from apps.layout.models import Layout, LayoutBlock, LayoutFilterConfig
from django.forms import modelformset_factory

from apps.layout.forms import (
    LayoutForm,
    AddBlockForm,
    LayoutFilterConfigForm,
    LayoutBlockForm,
)

from apps.layout.mixins import LayoutFilterSchemaMixin, LayoutAccessMixin




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


class LayoutDetailView(LoginRequiredMixin, LayoutAccessMixin, LayoutFilterSchemaMixin, TemplateView):
    template_name = "layout/layout_detail.html"

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = get_object_or_404(Layout, slug=slug, user__username=username)
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
                continue
            # Build a per-block namespaced GET overlay from selected layout filters
            ns = f"{getattr(block_impl, 'block_name', lb.block.code)}__{lb.id}__filters."
            qd = self.request.GET.copy()
            for k, v in (selected_filter_values or {}).items():
                name = f"{ns}{k}"
                if isinstance(v, (list, tuple)):
                    qd.setlist(name, [str(x) for x in v])
                elif isinstance(v, bool):
                    qd[name] = "1" if v else "0"
                elif v is not None:
                    qd[name] = str(v)

            class _ReqProxy:
                def __init__(self, req, get):
                    self._req = req
                    self.GET = get
                def __getattr__(self, item):
                    return getattr(self._req, item)

            proxy_request = _ReqProxy(self.request, qd)
            # Pass a stable per-instance id based on the LayoutBlock id
            response = block_impl.render(proxy_request, instance_id=str(lb.id))
            try:
                html = response.content.decode(response.charset or "utf-8")
            except Exception:
                html = response.content.decode("utf-8", errors="ignore")
            blocks_list.append({
                "col_classes": lb.bootstrap_col_classes(),
                "html": html,
                "block_name": lb.block.name,
                "id": lb.id,
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
        self.layout = get_object_or_404(Layout, slug=slug, user__username=username)
        self.ensure_edit_access(request, self.layout)
        # Limit queryset to this layout's blocks
        self.qs = self.layout.blocks.select_related("block").order_by("position", "id")
        # Formset for editing cols; allow deletion and ordering
        self.FormSet = modelformset_factory(
            LayoutBlock,
            form=LayoutBlockForm,
            fields=("col_sm", "col_md", "col_lg", "col_xl", "col_xxl"),
            extra=0,
            can_delete=True,
            can_order=True,
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        formset = self.FormSet(queryset=self.qs)
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
        self.layout = get_object_or_404(Layout, slug=slug, user__username=username)
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
        if "delete" in self.request.POST and edit_id:
            cfg = get_object_or_404(
                LayoutFilterConfig, id=edit_id, layout=self.layout, user=self.request.user
            )
            cfg.delete()
            messages.success(self.request, "Filter deleted.")
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
        layout = get_object_or_404(Layout, slug=slug, user__username=username)
        self.ensure_edit_access(request, layout)
        # Accept JSON payload: {"ordered_ids": [id1, id2, ...]}
        try:
            import json
            payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            payload = {}
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
        layout = get_object_or_404(Layout, slug=slug, user__username=username)
        self.ensure_edit_access(request, layout)
        lb = get_object_or_404(LayoutBlock, layout=layout, id=id)
        try:
            import json
            data = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            data = {}
        # Only allow known fields; normalize to None or int in ALLOWED_COLS
        from apps.layout.constants import ALLOWED_COLS
        def _norm(v):
            if v in (None, "", "null"): return None
            try:
                iv = int(v)
            except (TypeError, ValueError):
                return object()  # invalid sentinel
            return iv if iv in ALLOWED_COLS else object()
        updates = {}
        for key in ("col_sm", "col_md", "col_lg", "col_xl", "col_xxl"):
            if key in data:
                norm = _norm(data.get(key))
                if norm is object():
                    return JsonResponse({"ok": False, "error": f"Invalid value for {key}."}, status=400)
                updates[key] = norm
        if not updates:
            return JsonResponse({"ok": False, "error": "No updatable fields provided."}, status=400)
        for k, v in updates.items():
            setattr(lb, k, v)
        lb.save(update_fields=list(updates.keys()))
        return JsonResponse({"ok": True})


class LayoutBlockDeleteView(LoginRequiredMixin, LayoutAccessMixin, View):
    def post(self, request, username, slug, id, *args, **kwargs):
        layout = get_object_or_404(Layout, slug=slug, user__username=username)
        self.ensure_edit_access(request, layout)
        lb = get_object_or_404(LayoutBlock, layout=layout, id=id)
        lb.delete()
        return JsonResponse({"ok": True})


class LayoutBlockAddView(LoginRequiredMixin, LayoutAccessMixin, View):
    def post(self, request, username, slug, *args, **kwargs):
        layout = get_object_or_404(Layout, slug=slug, user__username=username)
        self.ensure_edit_access(request, layout)
        # Accept JSON or form POST; expect 'block' by code or id
        try:
            import json
            payload = json.loads(request.body.decode("utf-8")) if request.body and request.content_type == 'application/json' else {}
        except Exception:
            payload = {}
        block_code = payload.get("block") or request.POST.get("block")
        if not block_code:
            return JsonResponse({"ok": False, "error": "Missing block."}, status=400)
        from apps.blocks.models.block import Block
        try:
            block_obj = Block.objects.get(code=block_code)
        except Block.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Invalid block."}, status=400)
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
        FormSet = modelformset_factory(
            LayoutBlock,
            form=LayoutBlockForm,
            fields=("col_sm", "col_md", "col_lg", "col_xl", "col_xxl"),
            extra=0,
            can_delete=True,
            can_order=True,
        )
        formset = FormSet(queryset=qs)
        tbody_html = render_to_string(
            "layout/_layout_rows.html",
            {"formset": formset},
            request=request,
        )
        return JsonResponse({"ok": True, "tbody_html": tbody_html})
