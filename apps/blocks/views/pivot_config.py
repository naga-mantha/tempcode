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
    visibility = forms.ChoiceField(required=False, choices=[
        ("private", "Private"), ("public", "Public")
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
            from django.db.models import Q
            try:
                self.active_config = (
                    PivotConfig.objects
                    .filter(id=cfg_id, block=self.block)
                    .filter(Q(user=self.user) | Q(visibility=PivotConfig.VISIBILITY_PUBLIC))
                    .first()
                )
            except Exception:
                self.active_config = None
        # Build choices from this block's single source model
        model = None
        try:
            model = self.block_instance.get_model()
        except Exception:
            model = None
        dim_choices, measure_choices = [], []
        from apps.blocks.services.column_config import get_model_fields_for_column_config
        meta = get_model_fields_for_column_config(model, self.user) if model else []
        # Fallback: if nothing is visible under strict permissions, build using unrestricted meta
        if not meta and model is not None:
            try:
                meta = get_model_fields_for_column_config(model, None)
            except Exception:
                meta = []
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
        def is_temporal(model, path):
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
                    return isinstance(fld, (djm.DateField, djm.DateTimeField))
            return False
        measure_choices = [(n, labels.get(n, n)) for n,_ in dim_choices if model and is_numeric(model, n)]
        self.dimension_choices = dim_choices
        self.measure_choices = measure_choices
        self.temporal_fields = set([n for n,_ in dim_choices if model and is_temporal(model, n)])
        return super().dispatch(request, block_name, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.db.models import Q, Case, When, IntegerField
        q = PivotConfig.objects.filter(block=self.block).filter(
            Q(user=self.user) | Q(visibility=PivotConfig.VISIBILITY_PUBLIC)
        )
        configs = q.annotate(
            _vis_order=Case(
                When(visibility=PivotConfig.VISIBILITY_PRIVATE, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_vis_order", "name")
        ctx.update({
            "block": self.block,
            "block_title": getattr(self.block, "name", ""),
            "configs": configs,
            "active_config": self.active_config,
            "block_name": getattr(self.block_instance, "block_name", None) or getattr(self.block, "code", None),
            "temporal_fields": sorted(list(getattr(self, "temporal_fields", set()))),
        })
        # Add initial bucket mappings for rows/col when editing
        if self.active_config:
            schema = self.active_config.schema or {}
            row_bucket_map = {}
            rows = schema.get("rows") or []
            for r in rows:
                if isinstance(r, dict):
                    src = r.get("source") or r.get("field")
                    b = r.get("bucket") or r.get("date_bucket")
                    if src and b:
                        row_bucket_map[src] = b
            col_bucket = None
            col_entry = (schema.get("cols") or [None])
            col_entry = col_entry[0] if col_entry else None
            if isinstance(col_entry, dict):
                col_bucket = col_entry.get("bucket") or col_entry.get("date_bucket")
            ctx.update({
                "row_bucket_map": row_bucket_map,
                "col_bucket": col_bucket,
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
        # Normalize rows/cols to primitive values for UI selections
        norm_rows = []
        for r in (schema.get("rows") or []):
            if isinstance(r, dict):
                src = r.get("source") or r.get("field")
                if src:
                    norm_rows.append(src)
            else:
                norm_rows.append(r)
        col_entry = (schema.get("cols") or [""])
        col_entry = col_entry[0] if col_entry else ""
        norm_col = col_entry.get("source") if isinstance(col_entry, dict) else (col_entry or "")
        initial.update({
            "config_id": cfg.id,
            "name": cfg.name,
            "rows": norm_rows,
            "col": norm_col,
            "measure_field": m.get("source") or "",
            "measure_label": m.get("label") or "",
            "measure_agg": (m.get("agg") or "sum").lower(),
            "visibility": getattr(cfg, "visibility", "private"),
        })
        return initial

    def form_valid(self, form):
        # Determine redirect code early for permission redirects
        code = getattr(self.block_instance, "block_name", None) or self.block.code
        action = form.cleaned_data["action"]
        config_id = form.cleaned_data.get("config_id")
        name = form.cleaned_data.get("name")
        if action == "create":
            rows = form.cleaned_data.get("rows") or []
            col = form.cleaned_data.get("col") or ""
            m_field = form.cleaned_data.get("measure_field") or ""
            m_agg = (form.cleaned_data.get("measure_agg") or "sum").lower()
            m_label = form.cleaned_data.get("measure_label") or None
            visibility = (form.cleaned_data.get("visibility") or "private").lower()
            if not self.request.user.is_staff:
                visibility = "private"
            measures = []
            if m_field:
                entry = {"source": m_field, "agg": m_agg}
                if m_label:
                    entry["label"] = m_label
                measures.append(entry)
            # Collect row buckets from POST; preserve row order from POST
            request_rows = self.request.POST.getlist("rows")
            row_buckets = {}
            for key, val in self.request.POST.items():
                if key.startswith("row_bucket__"):
                    src = key[len("row_bucket__"):]
                    if val:
                        row_buckets[src] = val
            schema_rows = []
            for r in request_rows:
                b = row_buckets.get(r)
                if b:
                    schema_rows.append({"source": r, "bucket": b})
                else:
                    schema_rows.append(r)

            # Column bucket
            col_bucket = self.request.POST.get("col_bucket") or None
            if col:
                if col_bucket:
                    schema_cols = [{"source": col, "bucket": col_bucket}]
                else:
                    schema_cols = [col]
            else:
                schema_cols = []

            schema = {"rows": schema_rows, "cols": schema_cols, "measures": measures}
            # If a config_id is provided, update that specific row
            target_id = form.cleaned_data.get("config_id") or self.request.POST.get("config_id")
            if target_id:
                cfg = get_object_or_404(PivotConfig, id=target_id, block=self.block)
                # Non-admins can only edit their own private configs
                if (not self.request.user.is_staff) and (cfg.user_id != self.user.id or cfg.visibility != PivotConfig.VISIBILITY_PRIVATE):
                    return redirect("pivot_config_view", block_name=code)
                cfg.name = name or cfg.name
                cfg.schema = schema
                if self.request.user.is_staff and visibility in dict(PivotConfig.VISIBILITY_CHOICES):
                    cfg.visibility = visibility
                cfg.save()
            else:
                existing = PivotConfig.objects.filter(block=self.block, user=self.user, name=name).first()
                if existing:
                    existing.schema = schema
                    existing.visibility = visibility if self.request.user.is_staff else existing.visibility
                    existing.save()
                else:
                    PivotConfig.objects.create(block=self.block, user=self.user, name=name, schema=schema, visibility=visibility)
        elif action == "delete" and config_id:
            qs = PivotConfig.objects.filter(id=config_id, block=self.block)
            if not self.request.user.is_staff:
                qs = qs.filter(user=self.user, visibility=PivotConfig.VISIBILITY_PRIVATE)
            obj = qs.first()
            if obj:
                obj.delete()
        elif action == "set_default" and config_id:
            qs = PivotConfig.objects.filter(id=config_id, block=self.block)
            if not self.request.user.is_staff:
                qs = qs.filter(user=self.user, visibility=PivotConfig.VISIBILITY_PRIVATE)
            cfg = qs.first()
            if cfg:
                cfg.is_default = True
                cfg.save()
        return redirect("pivot_config_view", block_name=code)
