from django import forms
import json
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin


class FilterConfigForm(forms.Form):
    ACTIONS = (
        ("create", "create"),
        ("delete", "delete"),
        ("set_default", "set_default"),
    )
    action = forms.ChoiceField(choices=ACTIONS)
    config_id = forms.IntegerField(required=False)
    name = forms.CharField(required=False)

    def __init__(self, *args, filter_schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_schema = filter_schema


class FilterConfigView(LoginRequiredMixin, FilterResolutionMixin, FormView):
    template_name = "blocks/table/filter_config_view.html"
    form_class = FilterConfigForm
    filter_config_url_name = "table_filter_config"

    def dispatch(self, request, block_name, *args, **kwargs):
        self.block_name = block_name
        self.block_impl = block_registry.get(block_name)
        if not self.block_impl:
            raise Http404("Invalid block")
        self.db_block = get_object_or_404(Block, code=block_name)
        self.user_filters = BlockFilterConfig.objects.filter(
            block=self.db_block, user=request.user
        ).order_by("-is_default", "name")
        self.raw_schema = self.block_impl.get_filter_schema(request)
        self.filter_schema = self._resolve_filter_schema(self.raw_schema, request.user)
        return super().dispatch(request, block_name, *args, **kwargs)

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
                return redirect(self.filter_config_url_name, block_name=self.block_name)
            # Only collect namespaced inputs to avoid collisions with form fields like 'name'
            values = self._collect_filters(
                self.request.POST, self.filter_schema, base={}, prefix="filters.", allow_flat=False
            )
            existing = BlockFilterConfig.objects.filter(
                block=self.db_block, user=self.request.user, name=name
            ).first()
            try:
                if existing:
                    existing.values = values
                    existing.save()
                else:
                    BlockFilterConfig.objects.create(
                        block=self.db_block,
                        user=self.request.user,
                        name=name,
                        values=values,
                    )
            except IntegrityError:
                messages.error(self.request, "Filter name already taken. Please choose a different name.")
        elif action == "delete" and config_id:
            cfg = get_object_or_404(
                BlockFilterConfig, id=config_id, block=self.db_block, user=self.request.user
            )
            try:
                cfg.delete()
                messages.success(self.request, "Filter deleted.")
            except Exception as exc:
                messages.error(self.request, str(exc))
        elif action == "set_default" and config_id:
            cfg = get_object_or_404(
                BlockFilterConfig, id=config_id, block=self.db_block, user=self.request.user
            )
            cfg.is_default = True
            cfg.save()
        return redirect(self.filter_config_url_name, block_name=self.block_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        route_block_name = getattr(self.block_impl, "block_name", self.block_name)
        # Build display strings for saved filter values (map choice values to labels)
        def _fmt_with_schema(key, value):
            cfg = self.filter_schema.get(key, {}) or {}
            ftype = cfg.get("type")
            if isinstance(value, bool):
                return "Yes" if value else "No"
            # Map via choices list if available (for select/multiselect)
            if ftype in {"select", "multiselect"} and isinstance(cfg.get("choices"), (list, tuple)):
                choice_map = {str(v): str(lbl) for (v, lbl) in cfg.get("choices")}
                if isinstance(value, (list, tuple)):
                    return ", ".join([choice_map.get(str(v), str(v)) for v in value])
                return choice_map.get(str(value), str(value))
            # Fallback: stringify (handles numbers, strings, etc.)
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

        # Provide choice-label maps by key for client-side display of selected values
        labels_by_key = {}
        try:
            for key, cfg in (self.filter_schema or {}).items():
                choices = cfg.get("choices")
                if isinstance(choices, (list, tuple)):
                    labels_by_key[str(key)] = {str(v): str(lbl) for (v, lbl) in choices}
        except Exception:
            pass

        context.update(
            {
                "block": self.block_impl,
                "block_title": getattr(self.db_block, "name", route_block_name),
                "route_block_name": route_block_name,
                "configs": self.user_filters,
                "filter_schema": self.filter_schema,
                # initial values empty for new form; JS will populate when selecting an existing config
                "initial_values": {},
                "configs_values_json": json.dumps({cfg.id: cfg.values for cfg in self.user_filters}),
                "configs_values_by_id": values_by_id,
                "schema_choice_labels_json": json.dumps(labels_by_key),
            }
        )
        return context


class ChartFilterConfigView(FilterConfigView):
    template_name = "blocks/chart/filter_config_view.html"
    filter_config_url_name = "chart_filter_config"
