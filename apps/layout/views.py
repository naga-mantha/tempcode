from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, FormView, DeleteView

from apps.blocks.registry import block_registry
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
from apps.blocks.models.block import Block
from apps.layout.models import Layout, LayoutBlock, LayoutFilterConfig
from apps.layout.forms import LayoutForm, AddBlockForm, LayoutFilterConfigForm


class LayoutCreateView(LoginRequiredMixin, FormView):
    template_name = "layout/layout_form.html"
    form_class = LayoutForm

    def form_valid(self, form):
        layout = form.save(commit=False)
        layout.user = self.request.user
        layout.save()
        return redirect("layout_detail", slug=layout.slug)


class LayoutDeleteView(LoginRequiredMixin, DeleteView):
    model = Layout
    slug_field = "slug"
    slug_url_kwarg = "slug"
    success_url = reverse_lazy("layout_list")
    template_name = "layout/layout_confirm_delete.html"

    def get_queryset(self):
        return Layout.objects.filter(user=self.request.user)


class LayoutListView(LoginRequiredMixin, TemplateView):
    template_name = "layout/layout_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["layouts"] = Layout.objects.filter(user=self.request.user)
        return context


class LayoutDetailView(LoginRequiredMixin, FilterResolutionMixin, TemplateView):
    template_name = "layout/layout_detail.html"

    def dispatch(self, request, slug, *args, **kwargs):
        self.layout = get_object_or_404(Layout, slug=slug)
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
            block_impl = block_registry.get(lb.block.name)
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
        rendered_blocks = []
        for lb in self.layout.blocks.select_related("block"):
            block_impl = block_registry.get(lb.block.name)
            if block_impl:
                rendered_blocks.append(block_impl.render(self.request))
        context.update(
            {
                "layout": self.layout,
                "rendered_blocks": rendered_blocks,
                "filter_schema": filter_schema,
                "selected_filter_values": selected_filter_values,
                "filter_configs": self.filter_configs,
                "active_filter_config_id": self.active_filter_config.id if self.active_filter_config else None,
            }
        )
        return context


class AddBlockView(LoginRequiredMixin, FormView):
    template_name = "layout/add_block.html"
    form_class = AddBlockForm

    def dispatch(self, request, slug, *args, **kwargs):
        self.layout = get_object_or_404(Layout, slug=slug, user=request.user)
        return super().dispatch(request, slug, *args, **kwargs)

    def form_valid(self, form):
        block_name = form.cleaned_data["block"]
        block_obj = get_object_or_404(Block, name=block_name)
        LayoutBlock.objects.create(
            layout=self.layout,
            block=block_obj,
            row=form.cleaned_data["row"],
            col=form.cleaned_data["col"],
            width=form.cleaned_data["width"],
            height=form.cleaned_data["height"],
        )
        return redirect("layout_detail", slug=self.layout.slug)


class LayoutFilterConfigView(LoginRequiredMixin, FilterResolutionMixin, FormView):
    template_name = "layout/layout_filter_config.html"
    form_class = LayoutFilterConfigForm

    def dispatch(self, request, slug, *args, **kwargs):
        self.layout = get_object_or_404(Layout, slug=slug)
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
        return super().dispatch(request, slug, *args, **kwargs)

    def _build_filter_schema(self, request):
        raw_schema = {}
        for lb in self.layout.blocks.select_related("block"):
            block_impl = block_registry.get(lb.block.name)
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
                    "id": self.editing.id,
                    "name": self.editing.name,
                    "is_default": self.editing.is_default,
                }
            )
        return initial

    def form_valid(self, form):
        edit_id = form.cleaned_data.get("id")
        name = form.cleaned_data["name"].strip()
        is_default = form.cleaned_data.get("is_default", False)
        if not name:
            messages.error(self.request, "Please provide a name.")
            return redirect("layout_filter_config", slug=self.layout.slug)
        if "delete" in self.request.POST and edit_id:
            cfg = get_object_or_404(
                LayoutFilterConfig, id=edit_id, layout=self.layout, user=self.request.user
            )
            cfg.delete()
            messages.success(self.request, "Filter deleted.")
            return redirect("layout_filter_config", slug=self.layout.slug)
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
            return redirect("layout_filter_config", slug=self.layout.slug)
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
