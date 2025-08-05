from django.shortcuts import render
from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.helpers.permissions import get_readable_fields_state, get_editable_fields_state
from apps.blocks.helpers.field_rules import get_field_display_rules

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

        active_filter_config = None
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                pass
        if not active_filter_config:
            active_filter_config = filter_configs.filter(is_default=True).first()

        selected_fields = active_column_config.fields if active_column_config else []
        filter_values = active_filter_config.values if active_filter_config else {}

        queryset = self.get_queryset(user, filter_values, active_column_config)
        sample_obj = queryset.first() if queryset else None

        if not sample_obj:
            return {
                "block_name": self.block_name,
                "fields": [],
                "rows": [],
                "tabulator_options": {},
                "column_configs": column_configs,
                "filter_configs": filter_configs,
                "active_column_config_id": active_column_config.id if active_column_config else None,
                "active_filter_config_id": active_filter_config.id if active_filter_config else None,
            }

        # Permissions
        readable_fields = get_readable_fields_state(user, model, sample_obj)
        editable_fields = get_editable_fields_state(user, model, sample_obj)

        # Display Rules
        model_label = f"{model._meta.app_label}.{model.__name__}"
        display_rules = {
            r.field_name: r for r in get_field_display_rules(model_label)
        }

        # Final visible fields
        visible_fields = [
            f for f in selected_fields
            if f in readable_fields and not display_rules.get(f, {}).get("is_excluded", False)
        ]

        # Column definitions
        column_defs = {col["field"]: col["title"] for col in self.get_column_defs(user, active_column_config)}

        fields = []
        for f in visible_fields:
            fields.append({
                "name": f,
                "label": column_defs.get(f, f.replace("_", " ").title()),
                "mandatory": display_rules.get(f, {}).get("is_mandatory", False),
                "editable": f in editable_fields,
            })

        # Since queryset is already .values(), rows are flat dicts
        rows = []
        for obj in queryset:
            row = {}
            for field in visible_fields:
                parts = field.split("__")
                value = obj
                try:
                    for part in parts:
                        value = getattr(value, part)
                except Exception:
                    value = None
                current = row
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = value
            rows.append(row)

        return {
            "block_name": self.block_name,
            "fields": fields,
            "rows": rows,
            "tabulator_options": self.get_tabulator_options(user),
            "column_configs": column_configs,
            "filter_configs": filter_configs,
            "active_column_config_id": active_column_config.id if active_column_config else None,
            "active_filter_config_id": active_filter_config.id if active_filter_config else None,
        }

    def render(self, request):
        return render(request, self.template_name, self.get_context(request))
