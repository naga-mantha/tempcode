from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from apps.blocks.models.block import Block
from apps.blocks.models.repeater_config import RepeaterConfig
from apps.blocks.registry import block_registry
from apps.blocks.models.config_templates import RepeaterConfigTemplate


class RepeaterConfigForm(forms.Form):
    ACTIONS = (
        ("create", "create"),
        ("delete", "delete"),
        ("set_default", "set_default"),
    )
    action = forms.ChoiceField(choices=ACTIONS)
    config_id = forms.IntegerField(required=False)
    name = forms.CharField(required=False)

    group_by = forms.ChoiceField(required=False)
    label_field = forms.ChoiceField(required=False)
    include_null = forms.BooleanField(required=False)
    cols = forms.ChoiceField(required=False, choices=[(str(c), str(c)) for c in (12, 6, 4, 3, 2, 1)])
    # Ordering for label-based mode (legacy). New fields below supersede this.
    sort = forms.ChoiceField(required=False, choices=[("none", "None"), ("asc", "Ascending"), ("desc", "Descending")])
    # New ordering options
    order_by = forms.ChoiceField(required=False, choices=[("label", "Label"), ("metric", "Metric")])
    order = forms.ChoiceField(required=False, choices=[("asc", "Ascending / Bottom"), ("desc", "Descending / Top")])
    limit = forms.IntegerField(required=False, min_value=1)
    title_template = forms.CharField(required=False)
    child_filters_map = forms.CharField(required=False, widget=forms.Textarea, help_text="JSON mapping of child filter keys to 'value'|'label' or literal.")
    null_sentinel = forms.CharField(required=False)
    child_filter_config_name = forms.CharField(required=False)
    child_column_config_name = forms.CharField(required=False)
    # Metric configuration
    metric_mode = forms.ChoiceField(required=False, choices=[("aggregate", "Aggregate (DB)"), ("child", "Child (custom)")])
    metric_agg = forms.ChoiceField(required=False, choices=[("count", "Count"), ("sum", "Sum"), ("avg", "Average"), ("min", "Minimum"), ("max", "Maximum")])
    metric_field = forms.CharField(required=False, help_text="Django field path for aggregate modes, e.g., 'received_quantity'. Not required for count.")
    metric_filters = forms.CharField(required=False, widget=forms.Textarea, help_text="JSON of filters passed to child metrics (e.g., date range).")

    def __init__(self, *args, **kwargs):
        dim_choices = kwargs.pop("dimension_choices", [])
        super().__init__(*args, **kwargs)
        self.fields["group_by"].choices = [("", "-- Select --")] + dim_choices
        self.fields["label_field"].choices = [("", "-- Auto (same as group_by) --")] + dim_choices


class RepeaterConfigView(LoginRequiredMixin, FormView):
    template_name = "blocks/repeater/repeater_config_view.html"
    form_class = RepeaterConfigForm

    def dispatch(self, request, block_name, *args, **kwargs):
        self.block = get_object_or_404(Block, code=block_name)
        self.block_instance = block_registry.get(block_name)
        if not self.block_instance:
            raise Http404(f"Block '{block_name}' not found.")
        self.user = request.user
        # Lazy seed from admin-defined template when user has no repeater configs
        try:
            existing = RepeaterConfig.objects.filter(block=self.block, user=self.user)
            if not existing.exists():
                tpl = (
                    RepeaterConfigTemplate.objects.filter(block=self.block, is_default=True).first()
                    or RepeaterConfigTemplate.objects.filter(block=self.block).first()
                )
                if tpl:
                    RepeaterConfig.objects.create(
                        block=self.block,
                        user=self.user,
                        name=tpl.name or "Default",
                        schema=dict(tpl.schema or {}),
                        is_default=True,
                    )
        except Exception:
            pass
        cfg_id = request.GET.get("config_id") or request.POST.get("config_id")
        self.active_config = None
        if cfg_id:
            try:
                self.active_config = RepeaterConfig.objects.get(id=cfg_id, user=self.user, block=self.block)
            except RepeaterConfig.DoesNotExist:
                self.active_config = None
        # Determine fixed child block (do not expose in UI)
        selected_block_code = None
        try:
            selected_block_code = getattr(self.block_instance, "get_fixed_child_block_code", lambda: None)() or None
        except Exception:
            selected_block_code = None
        dim_choices = []
        if selected_block_code:
            child = block_registry.get(selected_block_code)
            model = None
            try:
                model = child.get_model()
            except Exception:
                model = None
            if model is not None:
                from apps.blocks.helpers.column_config import get_model_fields_for_column_config
                meta = get_model_fields_for_column_config(model, self.user)
                labels = {f["name"]: f"{f['label']} ({f['model']})" for f in meta}
                dim_choices = [(f["name"], labels[f["name"]]) for f in meta]

        self.dimension_choices = dim_choices
        return super().dispatch(request, block_name, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        configs = RepeaterConfig.objects.filter(block=self.block, user=self.user)
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
        kwargs.update({"dimension_choices": self.dimension_choices})
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        cfg = self.active_config
        if not cfg:
            return initial
        s = cfg.schema or {}
        initial.update({
            "config_id": cfg.id,
            "name": cfg.name,
            "group_by": s.get("group_by") or "",
            "label_field": s.get("label_field") or "",
            "include_null": bool(s.get("include_null")),
            "cols": str(s.get("cols") or ""),
            "sort": s.get("sort") or "none",
            "order_by": s.get("order_by") or "label",
            "order": s.get("order") or (s.get("sort") if s.get("sort") in ("asc","desc") else "asc"),
            "limit": s.get("limit") or None,
            "title_template": s.get("title_template") or "{label}",
            "child_filters_map": json_dumps_compact(s.get("child_filters_map") or {}),
            "null_sentinel": s.get("null_sentinel") or "",
            "child_filter_config_name": s.get("child_filter_config_name") or "",
            "child_column_config_name": s.get("child_column_config_name") or "",
            "metric_mode": s.get("metric_mode") or "aggregate",
            "metric_agg": s.get("metric_agg") or "count",
            "metric_field": s.get("metric_field") or "",
            "metric_filters": json_dumps_compact(s.get("metric_filters") or {}),
        })
        return initial

    def form_valid(self, form):
        action = form.cleaned_data["action"]
        config_id = form.cleaned_data.get("config_id")
        name = form.cleaned_data.get("name") or ""
        if action == "create":
            # Build schema from form
            s = {}
            for key in ("group_by", "label_field", "cols", "sort", "order_by", "order", "title_template", "null_sentinel", "child_filter_config_name", "child_column_config_name", "metric_mode", "metric_agg", "metric_field"):
                v = form.cleaned_data.get(key)
                if v not in (None, ""):
                    s[key] = v if key != "cols" else int(v)
            # Inject fixed child block code from the repeater instance
            try:
                child_code = getattr(self.block_instance, "get_fixed_child_block_code", lambda: None)()
            except Exception:
                child_code = None
            if child_code:
                s["block_code"] = child_code
            if form.cleaned_data.get("include_null"):
                s["include_null"] = True
            if form.cleaned_data.get("limit"):
                s["limit"] = int(form.cleaned_data.get("limit"))
            # child_filters_map as JSON
            fmap_raw = form.cleaned_data.get("child_filters_map") or "{}"
            try:
                import json
                fmap = json.loads(fmap_raw)
                if not isinstance(fmap, dict):
                    fmap = {}
            except Exception:
                fmap = {}
            s["child_filters_map"] = fmap
            # metric_filters as JSON
            mfilters_raw = form.cleaned_data.get("metric_filters") or "{}"
            try:
                import json
                mfilters = json.loads(mfilters_raw)
                if not isinstance(mfilters, dict):
                    mfilters = {}
            except Exception:
                mfilters = {}
            s["metric_filters"] = mfilters

            target_id = form.cleaned_data.get("config_id") or self.request.POST.get("config_id")
            if target_id:
                cfg = get_object_or_404(RepeaterConfig, id=target_id, user=self.user, block=self.block)
                cfg.name = name or cfg.name
                cfg.schema = s
                cfg.save()
            else:
                existing = RepeaterConfig.objects.filter(block=self.block, user=self.user, name=name).first()
                if existing:
                    existing.schema = s
                    existing.save()
                else:
                    RepeaterConfig.objects.create(block=self.block, user=self.user, name=name or "Default", schema=s)
        elif action == "delete" and config_id:
            RepeaterConfig.objects.get(id=config_id, user=self.user, block=self.block).delete()
        elif action == "set_default" and config_id:
            cfg = RepeaterConfig.objects.get(id=config_id, user=self.user, block=self.block)
            cfg.is_default = True
            cfg.save()
        code = getattr(self.block_instance, "block_name", None) or self.block.code
        return redirect("repeater_config_view", block_name=code)


def json_dumps_compact(obj):
    import json
    return json.dumps(obj, separators=(",", ":"))
