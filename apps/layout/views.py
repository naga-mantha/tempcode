from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, FormView, DeleteView

from apps.blocks.registry import block_registry
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
from apps.blocks.models.block import Block
from apps.layout.models import Layout, LayoutBlock, LayoutFilterConfig
from django.forms import modelformset_factory

from apps.layout.forms import (
    LayoutForm,
    AddBlockForm,
    LayoutFilterConfigForm,
    LayoutBlockForm,
)


class LayoutCreateView(LoginRequiredMixin, FormView):
    template_name = "layout/layout_form.html"
    form_class = LayoutForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        layout = form.save(commit=False)
        layout.user = self.request.user
        if not self.request.user.is_staff:
            layout.visibility = Layout.VISIBILITY_PRIVATE
        try:
            layout.save()
        except IntegrityError:
            form.add_error("name", "You already have a layout with this name.")
            return self.form_invalid(form)
        return redirect("layout_detail", username=layout.user.username, slug=layout.slug)


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
        return context


class LayoutDetailView(LoginRequiredMixin, FilterResolutionMixin, TemplateView):
    template_name = "layout/layout_detail.html"

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = get_object_or_404(Layout, slug=slug, user__username=username)
        if self.layout.visibility == Layout.VISIBILITY_PRIVATE and self.layout.user != request.user:
            raise Http404()
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
        return super().dispatch(request, slug, *args, **kwargs)

    def _build_filter_schema(self, request):
        raw_schema = {}
        for lb in self.layout.blocks.select_related("block"):
            block_impl = block_registry.get(lb.block.code)
            if block_impl and hasattr(block_impl, "get_filter_schema"):
                try:
                    schema = block_impl.get_filter_schema(request)
                except TypeError:
                    schema = block_impl.get_filter_schema(request.user)
                raw_schema.update(schema or {})
        return self._resolve_filter_schema(raw_schema, request.user)

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
            # Pass a stable per-instance id based on the LayoutBlock id
            response = block_impl.render(self.request, instance_id=str(lb.id))
            try:
                html = response.content.decode(response.charset or "utf-8")
            except Exception:
                html = response.content.decode("utf-8", errors="ignore")
            blocks_list.append({
                "col": lb.col,
                "html": html,
                "block_name": lb.block.name,
                "id": lb.id,
            })
        context.update(
            {
                "layout": self.layout,
                "blocks": blocks_list,
                "filter_schema": filter_schema,
                "selected_filter_values": selected_filter_values,
                "filter_configs": self.filter_configs,
                "active_filter_config_id": self.active_filter_config.id if self.active_filter_config else None,
                "can_edit": (
                    self.request.user.is_staff
                    or (
                        self.layout.visibility == Layout.VISIBILITY_PRIVATE
                        and self.layout.user == self.request.user
                    )
                ),
                "can_delete": (
                    self.request.user.is_staff
                    or (
                        self.layout.visibility == Layout.VISIBILITY_PRIVATE
                        and self.layout.user == self.request.user
                    )
                ),
            }
        )
        return context


class AddBlockView(LoginRequiredMixin, FormView):
    template_name = "layout/add_block.html"
    form_class = AddBlockForm

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = get_object_or_404(Layout, slug=slug, user__username=username)
        if self.layout.visibility == Layout.VISIBILITY_PUBLIC and not request.user.is_staff:
            raise Http404()
        if not request.user.is_staff and self.layout.user != request.user:
            raise Http404()
        return super().dispatch(request, username, slug, *args, **kwargs)

    def form_valid(self, form):
        # 'block' is a Block instance thanks to ModelChoiceField in the form
        block_obj = form.cleaned_data["block"]
        # Position new block at the end
        last = (
            LayoutBlock.objects.filter(layout=self.layout)
            .order_by("-position")
            .first()
        )
        next_pos = (last.position + 1) if last else 0
        LayoutBlock.objects.create(
            layout=self.layout,
            block=block_obj,
            col=form.cleaned_data["col"],
            position=next_pos,
        )
        return redirect("layout_detail", username=self.layout.user.username, slug=self.layout.slug)


class LayoutEditView(LoginRequiredMixin, TemplateView):
    template_name = "layout/layout_edit.html"

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = get_object_or_404(Layout, slug=slug, user__username=username)
        if self.layout.visibility == Layout.VISIBILITY_PUBLIC and not request.user.is_staff:
            raise Http404()
        if not request.user.is_staff and self.layout.user != request.user:
            raise Http404()
        # Limit queryset to this layout's blocks
        self.qs = self.layout.blocks.select_related("block").order_by("position", "id")
        # Formset for editing col; allow deletion and ordering
        self.FormSet = modelformset_factory(
            LayoutBlock,
            form=LayoutBlockForm,
            fields=("col",),
            extra=0,
            can_delete=True,
            can_order=True,
        )
        return super().dispatch(request, username, slug, *args, **kwargs)

    def get(self, request, username, slug):
        formset = self.FormSet(queryset=self.qs)
        return self.render_to_response({"layout": self.layout, "formset": formset})

    def post(self, request, username, slug):
        # Handle single-row delete actions triggered by per-row buttons
        delete_id = request.POST.get("delete")
        if delete_id:
            try:
                lb = self.qs.get(pk=delete_id)
                lb.delete()
                messages.success(request, "Block removed from layout.")
            except LayoutBlock.DoesNotExist:
                messages.error(request, "Block not found or already deleted.")
            return redirect("layout_edit", username=self.layout.user.username, slug=self.layout.slug)

        formset = self.FormSet(request.POST, queryset=self.qs)
        if formset.is_valid():
            # Update ordering from ORDER field (provided by can_order)
            order_counter = 0
            for form in formset.ordered_forms:
                inst = form.instance
                inst.position = order_counter
                inst.save(update_fields=["position"])
                order_counter += 1
            # Append any forms not in ordered_forms preserving current order
            for form in formset.forms:
                if form not in formset.ordered_forms and not form.cleaned_data.get("DELETE"):
                    inst = form.instance
                    inst.position = order_counter
                    inst.save(update_fields=["position"])
                    order_counter += 1
            # Save column width changes and process deletions
            formset.save()
            messages.success(request, "Layout updated.")
            return redirect("layout_detail", username=self.layout.user.username, slug=self.layout.slug)
        messages.error(request, "Please correct the errors below.")
        return self.render_to_response({"layout": self.layout, "formset": formset})


class LayoutFilterConfigView(LoginRequiredMixin, FilterResolutionMixin, FormView):
    template_name = "layout/layout_filter_config.html"
    form_class = LayoutFilterConfigForm

    def dispatch(self, request, username, slug, *args, **kwargs):
        self.layout = get_object_or_404(Layout, slug=slug, user__username=username)
        if self.layout.user != request.user and self.layout.visibility == Layout.VISIBILITY_PRIVATE:
            raise Http404()
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
        return super().dispatch(request, username, slug, *args, **kwargs)

    def post(self, request, username, slug, *args, **kwargs):
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

    def _build_filter_schema(self, request):
        raw_schema = {}
        for lb in self.layout.blocks.select_related("block"):
            block_impl = block_registry.get(lb.block.code)
            if block_impl and hasattr(block_impl, "get_filter_schema"):
                try:
                    schema = block_impl.get_filter_schema(request)
                except TypeError:
                    schema = block_impl.get_filter_schema(request.user)
                raw_schema.update(schema or {})
        return self._resolve_filter_schema(raw_schema, request.user)

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
