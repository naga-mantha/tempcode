from django.shortcuts import render
from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.helpers.column_config import get_user_column_config
from apps.blocks.helpers.filter_config import get_user_filter_config
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
        """
        Should be overridden in subclass to return the model class.
        """
        raise NotImplementedError("You must override get_model()")

    def get_queryset(self, user, filters):
        """
        Should be overridden in subclass to return filtered queryset.
        """
        raise NotImplementedError("You must override get_queryset(user, filters)")

    def get_field_labels(self, user):
        """
        Optional override: return a dict of field → label.
        """
        return {}

    def get_tabulator_options(self, user):
        """
        Optional override: return Tabulator options dict.
        """
        return {}

    def get_column_config_queryset(self, user):
        return BlockColumnConfig.objects.filter(user=user, block=self.block)

    def get_filter_config_queryset(self, user):
        return BlockFilterConfig.objects.filter(user=user, block=self.block)

    def get_context(self, request):
        model = self.get_model()
        user = request.user

        # Load saved configs
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

        # Get filtered data
        queryset = self.get_queryset(user, filter_values)
        sample_obj = queryset.first()

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

        # Labels and field metadata
        label_map = self.get_field_labels(user)
        fields = []
        for f in visible_fields:
            fields.append({
                "name": f,
                "label": label_map.get(f, f.replace("_", " ").title()),
                "mandatory": display_rules.get(f, {}).get("is_mandatory", False),
                "editable": f in editable_fields,
            })

        return {
            "block_name": self.block_name,
            "fields": fields,
            "rows": list(queryset.values(*visible_fields)),
            "tabulator_options": self.get_tabulator_options(user),
            "column_configs": column_configs,
            "filter_configs": filter_configs,
            "active_column_config_id": active_column_config.id if active_column_config else None,
            "active_filter_config_id": active_filter_config.id if active_filter_config else None,
        }

    def render(self, request):
        return render(request, self.template_name, self.get_context(request))
