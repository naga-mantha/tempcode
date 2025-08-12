from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.blocks.table.filter_utils import FilterResolutionMixin


class FilterConfigForm(forms.Form):
    id = forms.IntegerField(required=False)
    name = forms.CharField()
    is_default = forms.BooleanField(required=False)

    def __init__(self, *args, filter_schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_schema = filter_schema


class FilterConfigView(LoginRequiredMixin, FilterResolutionMixin, FormView):
    template_name = "blocks/table/filter_config_view.html"
    form_class = FilterConfigForm

    def dispatch(self, request, block_name, *args, **kwargs):
        self.block_name = block_name
        self.block_impl = block_registry.get(block_name)
        if not self.block_impl:
            raise Http404("Invalid block")
        self.db_block = get_object_or_404(Block, name=block_name)
        self.user_filters = BlockFilterConfig.objects.filter(
            block=self.db_block, user=request.user
        ).order_by("-is_default", "name")
        self.editing = None
        if request.method == "GET":
            edit_id = request.GET.get("id")
            if edit_id:
                self.editing = get_object_or_404(
                    BlockFilterConfig, id=edit_id, block=self.db_block, user=request.user
                )
        self.raw_schema = self.block_impl.get_filter_schema(request)
        self.filter_schema = self._resolve_filter_schema(self.raw_schema, request.user)
        return super().dispatch(request, block_name, *args, **kwargs)

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
            return redirect("table_filter_config", block_name=self.block_name)

        values = self._collect_filters(self.request.POST, self.filter_schema, base={})

        if edit_id:
            cfg = get_object_or_404(
                BlockFilterConfig, id=edit_id, block=self.db_block, user=self.request.user
            )
        else:
            cfg = BlockFilterConfig(block=self.db_block, user=self.request.user)
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
            return redirect("table_filter_config", block_name=self.block_name)
        messages.success(self.request, "Filter saved.")
        return redirect(f"{self.request.path}?id={cfg.id}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        route_block_name = getattr(self.block_impl, "block_name", self.block_name)
        initial_values = self.editing.values if self.editing else {}
        context.update(
            {
                "block": self.block_impl,
                "route_block_name": route_block_name,
                "user_filters": self.user_filters,
                "editing": self.editing,
                "filter_schema": self.filter_schema,
                "initial_values": initial_values,
            }
        )
        return context
