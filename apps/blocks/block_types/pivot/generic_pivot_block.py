from django.apps import apps as django_apps
from django.db.models import Count, Sum, Avg, Min, Max

from apps.blocks.block_types.pivot.pivot_block import PivotBlock
from apps.blocks.models.pivot_config import PivotConfig
from apps.blocks.services.filtering import apply_filter_registry


class GenericPivotBlock(PivotBlock):
    """User-configurable pivot with saved schemas (PivotConfig)."""

    def get_allowed_sources(self, user):
        raise NotImplementedError

    def _select_pivot_config(self, request, instance_id=None):
        user = request.user
        ns = f"{self.block_name}__{instance_id}__" if instance_id else f"{self.block_name}__"
        config_id = (
            request.GET.get(f"{ns}pivot_config_id")
            or request.GET.get("pivot_config_id")
        )
        qs = PivotConfig.objects.filter(block=self.block, user=user)
        active = None
        if config_id:
            try:
                active = qs.get(pk=config_id)
            except PivotConfig.DoesNotExist:
                pass
        if not active:
            active = qs.filter(is_default=True).first()
        return qs, active

    def build_columns_and_rows(self, user, filter_values):
        # Resolve active pivot config (prefer selection injected by base)
        active = getattr(self, "_active_pivot_config", None)
        configs = PivotConfig.objects.filter(block=self.block, user=user)
        if not active:
            active = configs.filter(is_default=True).first()
        if not active:
            return [], []
        allowed = self.get_allowed_sources(user) or {}
        src = allowed.get(active.source_model) or {}
        model_label = src.get("model") if isinstance(src, dict) else (src if isinstance(src, str) else None)
        if not model_label:
            return [], []
        try:
            app_label, model_name = model_label.split(".")
            model = django_apps.get_model(app_label, model_name)
        except Exception:
            return [], []

        schema = active.schema or {}
        rows = schema.get("rows", [])
        cols = schema.get("cols", [])
        measures = schema.get("measures", [])
        if not measures:
            return [], []

        qs = model.objects.all()
        qs = apply_filter_registry(self.block_name, qs, filter_values or {}, user)
        group_fields = [*rows, *cols]
        if not group_fields:
            group_fields = rows or cols or [measures[0].get("source")]
        qs = qs.values(*group_fields)

        import re
        agg_map = {}
        alias_to_title = {}
        used_aliases = set()
        for idx, m in enumerate(measures):
            src_field = m.get("source")
            agg = (m.get("agg") or "sum").lower()
            title = m.get("label") or f"{agg.upper()} {src_field}"
            base_alias = re.sub(r"[^0-9a-zA-Z_]", "_", (m.get("label") or f"{agg}_{src_field}"))
            if re.match(r"^[0-9]", base_alias or ""):
                base_alias = f"m_{base_alias}"
            alias = base_alias or f"m_{idx}"
            suffix = 1
            while alias in used_aliases:
                alias = f"{base_alias}_{suffix}"
                suffix += 1
            used_aliases.add(alias)
            alias_to_title[alias] = title
            if agg == "sum":
                agg_map[alias] = Sum(src_field)
            elif agg == "count":
                agg_map[alias] = Count(src_field)
            elif agg == "avg":
                agg_map[alias] = Avg(src_field)
            elif agg == "min":
                agg_map[alias] = Min(src_field)
            elif agg == "max":
                agg_map[alias] = Max(src_field)
            else:
                agg_map[alias] = Sum(src_field)
        qs = qs.annotate(**agg_map)
        records = list(qs)
        if not records:
            return [], []

        col_values = []
        if cols:
            col_key = cols[0]
            seen = set()
            for r in records:
                v = r.get(col_key)
                if v not in seen:
                    seen.add(v)
                    col_values.append(v)

        from collections import defaultdict
        grouped = defaultdict(list)
        row_keys = rows or []
        for r in records:
            k = tuple(r.get(x) for x in row_keys) if row_keys else ("All",)
            grouped[k].append(r)

        data = []
        for key, items in grouped.items():
            out = {}
            for i, rk in enumerate(row_keys):
                out[rk] = key[i]
            if not cols:
                first = items[0]
                for alias, title in alias_to_title.items():
                    out[title] = first.get(alias)
            else:
                col_key = cols[0]
                by_col = {it.get(col_key): it for it in items}
                for col_val in col_values:
                    rec = by_col.get(col_val)
                    for alias, title in alias_to_title.items():
                        col_name = f"{col_val} {title}"
                        out[col_name] = rec.get(alias) if rec else 0
            data.append(out)

        # Columns
        columns = []
        for rk in row_keys:
            columns.append({"title": rk.replace("__", " ").title(), "field": rk})
        if not cols:
            for alias, title in alias_to_title.items():
                columns.append({"title": title, "field": title})
        else:
            for col_val in col_values:
                for alias, title in alias_to_title.items():
                    col_name = f"{col_val} {title}"
                    columns.append({"title": col_name, "field": col_name})
        return columns, data
