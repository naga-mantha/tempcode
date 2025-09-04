from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from apps.blocks.models.block import Block
from apps.blocks.models.pivot_config import PivotConfig
from apps.blocks.registry import block_registry


class PivotConfigForm(forms.Form):
    ACTIONS = (
        ("create", "create"),
        ("delete", "delete"),
        ("set_default", "set_default"),
    )
    action = forms.ChoiceField(choices=ACTIONS)
    config_id = forms.IntegerField(required=False)
    name = forms.CharField(required=False)
    rows = forms.MultipleChoiceField(required=False)
    col = forms.ChoiceField(required=False)
    measure_field = forms.ChoiceField(required=False)
    measure_label = forms.CharField(required=False)
    measure_agg = forms.ChoiceField(required=False, choices=[
        ("sum", "Sum"), ("count", "Count"), ("avg", "Average"), ("min", "Min"), ("max", "Max")
    ])

    def __init__(self, *args, **kwargs):
        dim_choices = kwargs.pop("dimension_choices", [])
        measure_choices = kwargs.pop("measure_choices", [])
        super().__init__(*args, **kwargs)
        self.fields["rows"].choices = dim_choices
        self.fields["col"].choices = [("", "-- None --")] + dim_choices
        self.fields["measure_field"].choices = [("", "-- Select --")] + measure_choices


class PivotConfigView(LoginRequiredMixin, FormView):
    template_name = "blocks/pivot/pivot_config_view.html"
    form_class = PivotConfigForm

    def dispatch(self, request, block_name, *args, **kwargs):
        self.block = get_object_or_404(Block, code=block_name)
        self.block_instance = block_registry.get(block_name)
        if not self.block_instance:
            raise Http404(f"Block '{block_name}' not found.")
        self.user = request.user
        # Determine active config (for editing)
        cfg_id = request.GET.get("config_id") or request.POST.get("config_id")
        self.active_config = None
        if cfg_id:
            try:
                self.active_config = PivotConfig.objects.get(id=cfg_id, user=self.user, block=self.block)
            except PivotConfig.DoesNotExist:
                self.active_config = None
        # Build choices from this block's single source model
        model = None
        try:
            model = self.block_instance.get_model()
        except Exception:
            model = None
        dim_choices, measure_choices = [], []
        from apps.blocks.helpers.column_config import get_model_fields_for_column_config
        meta = get_model_fields_for_column_config(model, self.user) if model else []
        labels = {f["name"]: f"{f['label']} ({f['model']})" for f in meta}
        dim_choices = [(f["name"], labels[f["name"]]) for f in meta]
        from django.db import models as djm
        def is_numeric(model, path):
            parts = path.split("__"); m = model
            for i,p in enumerate(parts):
                try:
                    fld = m._meta.get_field(p)
                except Exception:
                    return False
                if i < len(parts)-1:
                    if getattr(fld, "is_relation", False):
                        m = fld.related_model
                    else:
                        return False
                else:
                    return isinstance(fld, (djm.IntegerField, djm.FloatField, djm.DecimalField, djm.PositiveIntegerField, djm.SmallIntegerField, djm.BigIntegerField))
            return False
        measure_choices = [(n, labels.get(n, n)) for n,_ in dim_choices if model and is_numeric(model, n)]
        self.dimension_choices = dim_choices
        self.measure_choices = measure_choices
        return super().dispatch(request, block_name, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        configs = PivotConfig.objects.filter(block=self.block, user=self.user)
        ctx.update({
            "block": self.block,
            "block_title": getattr(self.block, "name", ""),
            "configs": configs,
            "active_config": self.active_config,
            "block_name": getattr(self.block_instance, "block_name", None) or getattr(self.block, "code", None),
        })
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            "dimension_choices": self.dimension_choices,
            "measure_choices": self.measure_choices,
        })
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        cfg = self.active_config
        if not cfg:
            return initial
        schema = cfg.schema or {}
        measures = schema.get("measures") or []
        m = measures[0] if measures else {}
        initial.update({
            "config_id": cfg.id,
            "name": cfg.name,
            "rows": schema.get("rows") or [],
            "col": (schema.get("cols") or [""])[0] or "",
            "measure_field": m.get("source") or "",
            "measure_label": m.get("label") or "",
            "measure_agg": (m.get("agg") or "sum").lower(),
        })
        return initial

    def form_valid(self, form):
        action = form.cleaned_data["action"]
        config_id = form.cleaned_data.get("config_id")
        name = form.cleaned_data.get("name")
        if action == "create":
            rows = form.cleaned_data.get("rows") or []
            col = form.cleaned_data.get("col") or ""
            m_field = form.cleaned_data.get("measure_field") or ""
            m_agg = (form.cleaned_data.get("measure_agg") or "sum").lower()
            m_label = form.cleaned_data.get("measure_label") or None
            measures = []
            if m_field:
                entry = {"source": m_field, "agg": m_agg}
                if m_label:
                    entry["label"] = m_label
                measures.append(entry)
            schema = {"rows": rows, "cols": [col] if col else [], "measures": measures}
            # If a config_id is provided, update that specific row
            target_id = form.cleaned_data.get("config_id") or self.request.POST.get("config_id")
            if target_id:
                cfg = get_object_or_404(PivotConfig, id=target_id, user=self.user, block=self.block)
                cfg.name = name or cfg.name
                cfg.schema = schema
                cfg.save()
            else:
                existing = PivotConfig.objects.filter(block=self.block, user=self.user, name=name).first()
                if existing:
                    existing.schema = schema
                    existing.save()
                else:
                    PivotConfig.objects.create(block=self.block, user=self.user, name=name, schema=schema)
        elif action == "delete" and config_id:
            PivotConfig.objects.get(id=config_id, user=self.user, block=self.block).delete()
        elif action == "set_default" and config_id:
            cfg = PivotConfig.objects.get(id=config_id, user=self.user, block=self.block)
            cfg.is_default = True
            cfg.save()
        code = getattr(self.block_instance, "block_name", None) or self.block.code
        return redirect("pivot_config_view", block_name=code)
