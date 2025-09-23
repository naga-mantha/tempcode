from django import forms
import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.registry import block_registry
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin
from apps.blocks.models.config_templates import BlockFilterLayoutTemplate


class PivotFilterConfigForm(forms.Form, FilterResolutionMixin):
    ACTIONS = (("create", "create"), ("delete", "delete"), ("set_default", "set_default"))
    action = forms.ChoiceField(choices=ACTIONS)
    config_id = forms.IntegerField(required=False)
    name = forms.CharField(required=False)


class PivotFilterConfigView(LoginRequiredMixin, FormView, FilterResolutionMixin):
    template_name = "blocks/pivot/pivot_filter_config_view.html"
    form_class = PivotFilterConfigForm

    def dispatch(self, request, block_name, *args, **kwargs):
        self.block = get_object_or_404(Block, code=block_name)
        self.block_instance = block_registry.get(block_name)
        if not self.block_instance:
            raise Http404(f"Block '{block_name}' not found.")
        self.user = request.user
        try:
            raw_schema = self.block_instance.get_filter_schema(request)
        except TypeError:
            raw_schema = self.block_instance.get_filter_schema(self.user)
        self.filter_schema = self._resolve_filter_schema(raw_schema, self.user)
        return super().dispatch(request, block_name, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        configs = BlockFilterConfig.objects.filter(block=self.block, user=self.user).order_by("-is_default", "name")
        # Build values display and labels like table view
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
        allowed_keys = set((self.filter_schema or {}).keys())
        values_by_id = {}
        for f in configs:
            items = []
            try:
                for k, v in (f.values or {}).items():
                    if k not in allowed_keys:
                        continue
                    label = str(self.filter_schema.get(k, {}).get("label", k))
                    items.append(f"{label}: {_fmt_with_schema(k, v)}")
            except Exception:
                pass
            values_by_id[f.id] = items
        labels_by_key = {}
        try:
            for key, cfg in (self.filter_schema or {}).items():
                choices = cfg.get("choices")
                if isinstance(choices, (list, tuple)):
                    labels_by_key[str(key)] = {str(v): str(lbl) for (v, lbl) in choices}
        except Exception:
            pass
        ctx.update({
            "block": self.block,
            "block_title": getattr(self.block, "name", ""),
            "configs": configs,
            "filter_schema": self.filter_schema,
            "filter_layout": self._get_filter_layout(),
            "empty_values": {},
            "block_name": getattr(self.block_instance, "block_name", None) or getattr(self.block, "code", None),
            # Dropdown + client hydration
            "initial_values": {},
            "configs_values_json": json.dumps({
                cfg.id: {k: v for k, v in (cfg.values or {}).items() if k in allowed_keys}
                for cfg in configs
            }),
            "configs_values_by_id": values_by_id,
            "schema_choice_labels_json": json.dumps(labels_by_key),
        })
        return ctx

    def _get_filter_layout(self):
        try:
            from apps.blocks.models.block_filter_layout import BlockFilterLayout
            user_layout = BlockFilterLayout.objects.filter(block=self.block, user=self.user).first()
            if user_layout and isinstance(user_layout.layout, dict):
                return dict(user_layout.layout)
            tpl = BlockFilterLayoutTemplate.objects.filter(block=self.block).first()
            return dict(tpl.layout or {}) if tpl and isinstance(tpl.layout, dict) else None
        except Exception:
            return None

    # Removed 'other keys' support

    def form_valid(self, form):
        action = form.cleaned_data["action"]
        config_id = form.cleaned_data.get("config_id")
        name = form.cleaned_data.get("name")
        if action == "create":
            # Collect values with the expected prefix 'filters.' to match the template inputs
            values = self._collect_filters(
                self.request.POST,
                self.filter_schema,
                base={},
                prefix="filters.",
                allow_flat=False,
            )
            existing = BlockFilterConfig.objects.filter(block=self.block, user=self.user, name=name).first()
            if existing:
                existing.values = values
                existing.save()
            else:
                BlockFilterConfig.objects.create(block=self.block, user=self.user, name=name, values=values)
        elif action == "delete" and config_id:
            BlockFilterConfig.objects.get(id=config_id, user=self.user, block=self.block).delete()
        elif action == "set_default" and config_id:
            cfg = BlockFilterConfig.objects.get(id=config_id, user=self.user, block=self.block)
            cfg.is_default = True
            cfg.save()
        code = getattr(self.block_instance, "block_name", None) or self.block.code
        return redirect("pivot_filter_config", block_name=code)
