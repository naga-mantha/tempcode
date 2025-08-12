from apps.blocks.base import BaseBlock
from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.workflow.permissions import (
    get_readable_fields_state,
    get_editable_fields_state,
)
from apps.blocks.helpers.field_rules import get_field_display_rules
from django.db import models
import json
from .filter_utils import FilterResolutionMixin


class TableBlock(BaseBlock, FilterResolutionMixin):
    template_name = "blocks/table/table_block.html"
    supported_features = ["filters", "column_config"]

    def __init__(self, block_name):
        self.block_name = block_name
        self._block = None
        self._context_cache = None

    @property
    def block(self):
        if self._block is None:
            try:
                self._block = Block.objects.get(name=self.block_name)
            except Block.DoesNotExist:
                raise Exception(f"Block '{self.block_name}' not registered in admin.")
        return self._block

    def get_model(self):
        raise NotImplementedError("You must override get_model()")

    def get_queryset(self, user, filters, active_column_config):
        raise NotImplementedError("You must override get_queryset(user, filters, active_column_config)")

    def get_tabulator_options(self, user):
        return {}

    def get_column_config_queryset(self, user):
        return BlockColumnConfig.objects.filter(user=user, block=self.block)

    def get_filter_config_queryset(self, user):
        return BlockFilterConfig.objects.filter(user=user, block=self.block)

    def _build_context(self, request):
        user = request.user
        (
            column_configs,
            filter_configs,
            active_column_config,
            active_filter_config,
            selected_fields,
        ) = self._select_configs(request)
        filter_schema, selected_filter_values = self._resolve_filters(
            request, active_filter_config
        )
        queryset, sample_obj = self._build_queryset(
            user, selected_filter_values, active_column_config
        )
        fields, columns = self._compute_fields(
            user, selected_fields, active_column_config, sample_obj
        )
        data = self._serialize_rows(queryset, selected_fields)
        return {
            "block_name": self.block_name,
            "fields": fields,
            "tabulator_options": self.get_tabulator_options(user),
            "column_configs": column_configs,
            "filter_configs": filter_configs,
            "active_column_config_id": active_column_config.id if active_column_config else None,
            "active_filter_config_id": active_filter_config.id if active_filter_config else None,
            "columns": columns,
            "data": data,
            "filter_schema": filter_schema,
            "selected_filter_values": selected_filter_values,
        }

    def _get_context(self, request):
        if self._context_cache is None:
            self._context_cache = self._build_context(request)
        return self._context_cache

    def get_config(self, request):
        context = dict(self._get_context(request))
        context.pop("data", None)
        return context

    def get_data(self, request):
        context = self._get_context(request)
        return {"data": context.get("data")}

    def _select_configs(self, request):
        user = request.user
        column_config_id = request.GET.get("column_config_id")
        filter_config_id = request.GET.get("filter_config_id")
        column_configs = self.get_column_config_queryset(user)
        filter_configs = self.get_filter_config_queryset(user)
        active_column_config = None
        if column_config_id:
            try:
                active_column_config = column_configs.get(pk=column_config_id)
            except BlockColumnConfig.DoesNotExist:
                pass
        if not active_column_config:
            active_column_config = column_configs.filter(is_default=True).first()
        active_filter_config = None
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                pass
        if not active_filter_config:
            active_filter_config = filter_configs.filter(is_default=True).first()
        selected_fields = active_column_config.fields if active_column_config else []
        return (
            column_configs,
            filter_configs,
            active_column_config,
            active_filter_config,
            selected_fields,
        )

    def _resolve_filters(self, request, active_filter_config):
        user = request.user
        try:
            raw_schema = self.get_filter_schema(request)
        except TypeError:
            raw_schema = self.get_filter_schema(user)
        filter_schema = self._resolve_filter_schema(raw_schema, user)
        base_values = active_filter_config.values if active_filter_config else {}
        selected_filter_values = self._collect_filters(
            request.GET, filter_schema, base=base_values
        )
        return filter_schema, selected_filter_values

    def _build_queryset(self, user, filter_values, active_column_config):
        queryset = self.get_queryset(user, filter_values, active_column_config)
        sample_obj = queryset.first() if queryset else None
        return queryset, sample_obj

    def _compute_fields(self, user, selected_fields, active_column_config, sample_obj):
        model = self.get_model()
        model_list = [model]
        for field in model._meta.fields:
            if isinstance(field, models.ForeignKey):
                model_list.append(field.remote_field.model)
        readable_fields = []
        editable_fields = []
        for m in model_list:
            readable_fields.extend(get_readable_fields_state(user, m, sample_obj))
            editable_fields.extend(get_editable_fields_state(user, m, sample_obj))
        model_label = f"{model._meta.app_label}.{model.__name__}"
        display_rules = {
            r.field_name: r for r in get_field_display_rules(model_label)
        }
        visible_fields = [
            f
            for f in selected_fields
            if f in readable_fields
            and not (display_rules.get(f) and display_rules[f].is_excluded)
        ]
        column_defs = self.get_column_defs(user, active_column_config)
        column_label_map = {col["field"]: col["title"] for col in column_defs}
        fields = []
        for f in visible_fields:
            fields.append(
                {
                    "name": f,
                    "label": column_label_map.get(f, f.replace("_", " ").title()),
                    "mandatory": display_rules[f].is_mandatory if f in display_rules else False,
                    "editable": f in editable_fields,
                }
            )
        from django.contrib.admin.utils import label_for_field
        columns = [
            {
                "title": label_for_field(defn.get("field"), self.get_model(), return_attr=False),
                "field": defn.get("field"),
            }
            for defn in column_defs
        ]
        return fields, columns

    def _serialize_rows(self, queryset, selected_fields):
        data = []
        for obj in queryset:
            row = {}
            for field in selected_fields:
                if "__" in field:
                    related_field, sub_field = field.split("__", 1)
                    related_obj = getattr(obj, related_field, None)
                    value = getattr(related_obj, sub_field, None) if related_obj else None
                else:
                    value = getattr(obj, field, None)
                if value is None:
                    row[field] = ""
                elif isinstance(value, models.Model):
                    row[field] = str(value)
                else:
                    try:
                        json.dumps(value)
                        row[field] = value
                    except TypeError:
                        row[field] = str(value)
            data.append(row)
        return json.dumps(data)

