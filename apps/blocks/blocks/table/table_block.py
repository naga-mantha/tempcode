from django.shortcuts import render
from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.helpers.permissions import get_readable_fields_state, get_editable_fields_state
from apps.blocks.helpers.field_rules import get_field_display_rules
from django.db import models
import json
from apps.blocks.blocks.table.views import _resolve_filter_schema, _collect_filters

class TableBlock:
    template_name = "blocks/table/table_block.html"

    def __init__(self, block_name):
        self.block_name = block_name
        self._block = None

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

    def get_context(self, request):
        model = self.get_model()
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

        # --- filters: choose active saved filter (default if none in GET) ---
        active_filter_config = None
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                pass
        if not active_filter_config:
            active_filter_config = filter_configs.filter(is_default=True).first()

        # --- resolve schema (reuses your helper) ---
        try:
            raw_schema = self.get_filter_schema(request)  # if your block takes request
        except TypeError:
            raw_schema = self.get_filter_schema(user)  # backward-compat
        filter_schema = _resolve_filter_schema(raw_schema, user)

        # --- live (non-persistent) overrides from GET (no helper, inline for clarity) ---
        base_values = active_filter_config.values if active_filter_config else {}

        # merged values used to pre-populate fields and to filter queryset
        selected_filter_values = _collect_filters(request.GET, filter_schema, base=base_values)
        filter_values = selected_filter_values

        selected_fields = active_column_config.fields if active_column_config else []

        queryset = self.get_queryset(user, filter_values, active_column_config)
        sample_obj = queryset.first() if queryset else None

        # if not sample_obj:
        #     return {
        #         "block_name": self.block_name,
        #         "fields": [],
        #         "rows": [],
        #         "tabulator_options": {},
        #         "column_configs": column_configs,
        #         "filter_configs": filter_configs,
        #         "active_column_config_id": active_column_config.id if active_column_config else None,
        #         "active_filter_config_id": active_filter_config.id if active_filter_config else None,
        #     }

        # Model introspection
        model_list = []
        model_list.append(model)
        for field in model._meta.fields:
            if isinstance(field, models.ForeignKey):
                model_list.append(field.remote_field.model)


        # Permissions
        readable_fields = []
        editable_fields = []
        for m in model_list:
            readable_fields.extend(get_readable_fields_state(user, m, sample_obj))
            editable_fields.extend(get_editable_fields_state(user, m, sample_obj))

        # Display Rules
        model_label = f"{model._meta.app_label}.{model.__name__}"

    #TODO: Later fix the issue where if a field is made mandatory/excluded, it should be reflected in final table. Since the configs wont be saved automaticallt until users saves it
        # rules = get_field_display_rules(model_label)
        # mandatory_fields = set(rules.get("mandatory", []))
        # excluded_fields = set(rules.get("excluded", []))
        # effective_fields = [f for f in selected_fields if f not in excluded_fields]
        #
        # for field in mandatory_fields:
        #     if field not in effective_fields:
        #         effective_fields.append(field)

        display_rules = {
            r.field_name: r for r in get_field_display_rules(model_label)
        }

        print("Display Rules:", display_rules)

        # Final visible fields
        visible_fields = [
            f for f in selected_fields
            if f in readable_fields and not (display_rules.get(f) and display_rules[f].is_excluded)
        ]

        # Column definitions
        column_defs = {col["field"]: col["title"] for col in self.get_column_defs(user, active_column_config)}

        fields = []
        for f in visible_fields:
            fields.append({
                "name": f,
                "label": column_defs.get(f, f.replace("_", " ").title()),
                "mandatory": display_rules[f].is_mandatory if f in display_rules else False,
                "editable": f in editable_fields,
            })

        # Construct data
        data = []
        for obj in queryset:
            row = {}
            for field in selected_fields:
                if "__" in field:
                    # Handle related fields
                    related_field, sub_field = field.split("__", 1)
                    related_obj = getattr(obj, related_field, None)
                    value = getattr(related_obj, sub_field, None) if related_obj else None
                else:
                    # Handle regular fields
                    value = getattr(obj, field, None)

                # Replace None with an empty string and convert objects to strings
                row[field] = value if value is not None else ""
                if isinstance(value, (object, models.Model)):
                    row[field] = str(value)

            data.append(row)
        from django.contrib.admin.utils import label_for_field
        # Construct columns
        columns = [
            {
                "title": label_for_field(field.get("field"), self.get_model(), return_attr=False),
                "field": field.get("field"),
            }
            for field in self.get_column_defs(user, active_column_config)
        ]
        return {
            "block_name": self.block_name,
            "fields": fields,
            "tabulator_options": self.get_tabulator_options(user),
            "column_configs": column_configs,
            "filter_configs": filter_configs,
            "active_column_config_id": active_column_config.id if active_column_config else None,
            "active_filter_config_id": active_filter_config.id if active_filter_config else None,
            "columns": columns,
            "data": json.dumps(data),
            "filter_schema": filter_schema,                       # ← added
            "selected_filter_values": selected_filter_values,     # ← added
        }

    def render(self, request):
        return render(request, self.template_name, self.get_context(request))
