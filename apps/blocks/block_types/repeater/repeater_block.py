from __future__ import annotations

from apps.blocks.base import BaseBlock
from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.repeater_config import RepeaterConfig
from apps.blocks.models.config_templates import RepeaterConfigTemplate
from django.http import QueryDict
from django.utils.text import slugify
from django.db.models import Model
from django.db.models import Count, Sum, Avg, Min, Max
import json
import uuid


class RepeaterBlock(BaseBlock):
    """Generic repeater that renders a child block per distinct group value."""

    template_name = "blocks/repeater/repeater_block.html"

    def __init__(self, block_name: str):
        self.block_name = block_name
        self._block = None
        self._context_cache = {}

    @property
    def block(self) -> Block:
        if self._block is None:
            try:
                self._block = Block.objects.get(code=self.block_name)
            except Block.DoesNotExist:
                raise Exception(f"Block '{self.block_name}' not registered in admin.")
        return self._block

    # --------------- Config selection ---------------
    def _select_repeater_config(self, request, instance_id=None):
        user = request.user
        ns = f"{self.block_name}__{instance_id}__" if instance_id else f"{self.block_name}__"
        config_id = (
            request.GET.get(f"{ns}repeater_config_id")
            or request.GET.get("repeater_config_id")
        )
        qs = RepeaterConfig.objects.filter(block=self.block, user=user)
        # Lazy seed from admin-defined template when user has no repeater configs
        if not qs.exists():
            try:
                tpl = (
                    RepeaterConfigTemplate.objects.filter(block=self.block, is_default=True).first()
                    or RepeaterConfigTemplate.objects.filter(block=self.block).first()
                )
                if tpl:
                    RepeaterConfig.objects.create(
                        block=self.block,
                        user=user,
                        name=tpl.name or "Default",
                        schema=dict(tpl.schema or {}),
                        is_default=True,
                    )
                    qs = RepeaterConfig.objects.filter(block=self.block, user=user)
            except Exception:
                pass
        active = None
        if config_id:
            try:
                active = qs.get(pk=config_id)
            except RepeaterConfig.DoesNotExist:
                pass
        if not active:
            active = qs.filter(is_default=True).first()
        return qs, active

    # --------------- Rendering ---------------
    def render(self, request, instance_id=None):
        self._context_cache.clear()
        return super().render(request, instance_id=instance_id)

    def _get_context(self, request, instance_id):
        effective_instance_id = instance_id or self._detect_instance_id_from_query(request)
        cache_key = (id(request), effective_instance_id)
        if cache_key not in self._context_cache:
            self._context_cache[cache_key] = self._build_context(request, effective_instance_id)
        return self._context_cache[cache_key]

    def _detect_instance_id_from_query(self, request):
        try:
            keys = request.GET.keys()
        except Exception:
            return None
        prefix = f"{self.block_name}__"
        for key in keys:
            if not key.startswith(prefix):
                continue
            rest = key[len(prefix):]
            if "__" not in rest:
                continue
            candidate, tail = rest.split("__", 1)
            if (
                tail.startswith("repeater_config_id")
                or tail.startswith("filters.")
            ):
                return candidate
        return None

    def get_config(self, request, instance_id=None):
        context = dict(self._get_context(request, instance_id))
        context.pop("data", None)
        return context

    def get_data(self, request, instance_id=None):
        context = self._get_context(request, instance_id)
        return {"data": context.get("data")}

    # ---------------- Fixed child hook ----------------
    def get_fixed_child_block_code(self) -> str | None:
        """Return a fixed child block code if this repeater is specialized.

        Concrete repeaters should override this to prevent users from swapping
        the child block via settings. Return None to allow schema to provide it.
        """
        return None

    def _build_context(self, request, instance_id):
        user = request.user
        configs, active = self._select_repeater_config(request, instance_id)
        instance_id = instance_id or uuid.uuid4().hex[:8]
        panels, cols, title = self._build_panels(request, user, active)
        return {
            "block_name": self.block_name,
            "instance_id": instance_id,
            "block_title": getattr(self.block, "name", self.block_name),
            "block": self.block,
            "repeater_configs": configs,
            "active_repeater_config_id": getattr(active, "id", None) if active else None,
            "title": title,
            "cols": cols,
            "panels": panels,
            "data": json.dumps({"count": len(panels)}),
        }

    # --------------- Helpers ---------------
    def _build_panels(self, request, user, active_config: RepeaterConfig | None):
        if not active_config:
            return [], 12, ""
        schema = active_config.schema or {}
        # Resolve child block code: fixed child takes precedence over schema
        block_code = self.get_fixed_child_block_code() or schema.get("block_code")
        group_by = schema.get("group_by")
        label_field = schema.get("label_field") or group_by
        include_null = bool(schema.get("include_null"))
        cols = int(schema.get("cols") or 12)
        child_filters_map = schema.get("child_filters_map") or {}
        # Optional: separate filters for metric evaluation (child mode)
        metric_filters_map = schema.get("metric_filters") or {}
        null_sentinel = schema.get("null_sentinel")
        child_filter_name = (schema.get("child_filter_config_name") or "").strip()
        child_column_name = (schema.get("child_column_config_name") or "").strip()
        # Ordering and limit
        order_by = (schema.get("order_by") or "label").lower()  # 'label' | 'metric'
        order = (schema.get("order") or schema.get("sort") or "none").lower()  # 'asc' | 'desc' | 'none'
        limit = schema.get("limit")
        title_template = (schema.get("title_template") or "{label}").strip()
        # Metric config
        metric_mode = (schema.get("metric_mode") or "aggregate").lower()  # 'aggregate' | 'child'
        metric_agg = (schema.get("metric_agg") or "count").lower()  # 'count'|'sum'|'avg'|'min'|'max'
        metric_field = schema.get("metric_field")  # required for sum/avg/min/max

        if not block_code:
            return [], cols, ""
        child = block_registry.get(block_code)
        if not child:
            return ([{"title": "Error", "html": f"<div class='alert alert-danger p-2 m-0'>Child block '{block_code}' not available.</div>"}], cols, "")

        # Enumeration queryset: prefer child hook; else introspect model
        values = []
        try:
            if hasattr(child, "get_enumeration_queryset"):
                base_qs = child.get_enumeration_queryset(user)  # type: ignore[attr-defined]
            elif hasattr(child, "get_model"):
                model = child.get_model()
                base_qs = model.objects.all()
            else:
                base_qs = None
        except Exception:
            base_qs = None

        # Build aggregation function mapping
        agg_map = {
            "count": lambda f: Count(f or "id"),
            "sum": lambda f: Sum(f),
            "avg": lambda f: Avg(f),
            "min": lambda f: Min(f),
            "max": lambda f: Max(f),
        }

        if base_qs is not None and group_by:
            # Two modes: label-ordered vs metric-ordered
            if order_by == "metric":
                if metric_mode == "aggregate":
                    fields = [group_by]
                    if label_field and label_field != group_by:
                        fields.append(label_field)
                    qs = base_qs.values(*fields)
                    if not include_null:
                        qs = qs.exclude(**{f"{group_by}__isnull": True})
                    try:
                        agg_fn_builder = agg_map.get(metric_agg or "count") or agg_map["count"]
                        if metric_agg == "count":
                            # count does not require a concrete field
                            metric_ann = agg_fn_builder("id")
                        else:
                            if not metric_field:
                                raise ValueError("metric_field is required for aggregate metric mode (sum/avg/min/max)")
                            metric_ann = agg_fn_builder(metric_field)
                        qs = qs.annotate(metric=metric_ann)
                        # Order and limit
                        if order in ("asc", "desc"):
                            order_field = "metric" if order == "asc" else "-metric"
                            qs = qs.order_by(order_field)
                        if isinstance(limit, int) and limit > 0:
                            qs = qs[:limit]
                        for r in qs:
                            values.append({
                                "value": r.get(group_by),
                                "label": r.get(label_field) if label_field else r.get(group_by),
                                "metric": r.get("metric"),
                            })
                    except Exception as exc:
                        # Fall back to label ordering if aggregation fails
                        values = []
                        order_by = "label"
                else:  # metric_mode == 'child'
                    # First enumerate distinct values+labels (unsorted)
                    fields = [group_by]
                    if label_field and label_field != group_by:
                        fields.append(label_field)
                    qs = base_qs.values(*fields).distinct()
                    if not include_null:
                        qs = qs.exclude(**{f"{group_by}__isnull": True})
                    for r in qs:
                        values.append({
                            "value": r.get(group_by),
                            "label": r.get(label_field) if label_field else r.get(group_by),
                        })
                    # Resolve metric_filters by mapping schema entries
                    metric_filters = {}
                    for key, source in (metric_filters_map.items() if isinstance(metric_filters_map, dict) else []):
                        # In this context we pass literal values; 'value'/'label' placeholders are not meaningful globally
                        metric_filters[key] = source
                    # Ask child to compute per-group metrics
                    metrics = {}
                    try:
                        if hasattr(child, "get_repeater_metrics"):
                            metrics = child.get_repeater_metrics(user, group_by, base_qs, metric_filters)  # type: ignore[attr-defined]
                    except Exception:
                        metrics = {}
                    # Attach metrics and sort
                    for it in values:
                        it["metric"] = metrics.get(it["value"], 0)
                    if order in ("asc", "desc"):
                        rev = order == "desc"
                        values.sort(key=lambda x: (x.get("metric") is None, x.get("metric", 0)), reverse=rev)
                    if isinstance(limit, int) and limit > 0:
                        values = values[:limit]
            # Fallback: label ordering or when order_by degraded to 'label'
            if order_by != "metric":
                fields = [group_by]
                if label_field and label_field != group_by:
                    fields.append(label_field)
                qs = base_qs.values(*fields).distinct()
                if not include_null:
                    qs = qs.exclude(**{f"{group_by}__isnull": True})
                if order in ("asc", "desc"):
                    order_field = label_field or group_by
                    if order == "desc":
                        order_field = f"-{order_field}"
                    qs = qs.order_by(order_field)
                if isinstance(limit, int) and limit > 0:
                    qs = qs[:limit]
                values = [{
                    "value": r.get(group_by),
                    "label": r.get(label_field) if label_field else r.get(group_by),
                } for r in qs]

        # Construct each panel by rendering the child with namespaced filters
        panels = []

        class _ReqProxy:
            def __init__(self, req, get):
                self._req = req
                self.GET = get
            def __getattr__(self, item):
                return getattr(self._req, item)

        # Resolve child saved configs by name for this user
        child_block_obj = getattr(child, "block", None)
        child_block = None
        try:
            child_block = child_block_obj if child_block_obj else Block.objects.get(code=getattr(child, "block_name", block_code))
        except Exception:
            child_block = None
        child_filter_cfg_id = None
        child_column_cfg_id = None
        if child_block and child_filter_name:
            cfg = BlockFilterConfig.objects.filter(block=child_block, user=user, name=child_filter_name).only("id").first()
            if cfg:
                child_filter_cfg_id = str(cfg.id)
        if child_block and child_column_name:
            from django.db.models import Q, Case, When, IntegerField
            qcol = BlockColumnConfig.objects.filter(block=child_block, name=child_column_name).filter(
                Q(user=user) | Q(visibility=BlockColumnConfig.VISIBILITY_PUBLIC)
            ).annotate(
                _vis_order=Case(
                    When(visibility=BlockColumnConfig.VISIBILITY_PRIVATE, then=0),
                    default=1,
                    output_field=IntegerField(),
                )
            ).order_by("_vis_order")
            col = qcol.only("id").first()
            if col:
                child_column_cfg_id = str(col.id)

        for item in values:
            raw_value = item.get("value")
            label = item.get("label")
            inst_slug = slugify(str(label if label is not None else raw_value)) or uuid.uuid4().hex[:6]
            instance = f"rep_{inst_slug}"
            qd: QueryDict = request.GET.copy()
            # Map filters into child
            for key, source in (child_filters_map.items() if isinstance(child_filters_map, dict) else []):
                sval = None
                if source == "value":
                    sval = raw_value
                elif source == "label":
                    sval = label
                else:
                    # treat as literal
                    sval = source
                if sval is None and null_sentinel is not None:
                    qd[f"{getattr(child, 'block_name', block_code)}__{instance}__filters.{key}"] = str(null_sentinel)
                else:
                    qd[f"{getattr(child, 'block_name', block_code)}__{instance}__filters.{key}"] = "" if sval is None else str(sval)
            # Inject saved configs (unless already present in GET)
            if child_filter_cfg_id:
                key = f"{getattr(child, 'block_name', block_code)}__{instance}__filter_config_id"
                if key not in qd:
                    qd[key] = child_filter_cfg_id
            if child_column_cfg_id:
                key = f"{getattr(child, 'block_name', block_code)}__{instance}__column_config_id"
                if key not in qd:
                    qd[key] = child_column_cfg_id
            qd["embedded"] = "1"
            proxy = _ReqProxy(request, qd)
            try:
                resp = child.render(proxy, instance_id=instance)
                html = resp.content.decode(getattr(resp, "charset", "utf-8") or "utf-8")
            except Exception as exc:
                html = (
                    "<div class='alert alert-danger p-2 m-0'>"
                    f"Error rendering child '{block_code}': {str(exc)}"
                    "</div>"
                )
            title = title_template.format(label=label, value=raw_value)
            panels.append({"title": title, "html": html})

        return panels, cols, schema.get("title", "")


class GenericRepeaterBlock(RepeaterBlock):
    """Default, user-configurable repeater block."""

    def __init__(self):
        super().__init__(block_name="generic_repeater")
