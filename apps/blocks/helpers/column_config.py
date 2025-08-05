from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.permissions.checks import can_read_field
from apps.workflow.permissions import can_read_field_state
from apps.blocks.helpers.field_rules import get_field_display_rules, get_flat_fields
def get_user_column_config(user, block):
    config = BlockColumnConfig.objects.filter(block=block, user=user, is_default=True).first()
    return config.fields if config else []

def get_model_fields_for_column_config(model, user, instance=None):
    from django.db.models import ForeignKey
    from django.contrib.admin.utils import label_for_field

    base_fields = [f.name for f in model._meta.fields]
    related_fields = [
        f"{field.name}__{subfield.name}"
        for field in model._meta.fields
        if isinstance(field, ForeignKey)
        for subfield in field.related_model._meta.fields
        if subfield.name != "id"
    ]

    fields = base_fields + related_fields
    rules = {r.field_name: r.rule_type for r in get_field_display_rules(model._meta.label_lower)}

    visible_fields = []
    for field_name in fields:
        label = label_for_field(field_name, model, return_attr=False)
        is_mandatory = rules.get(field_name) == "mandatory"
        is_excluded = rules.get(field_name) == "hidden"

        if is_excluded:
            continue
        if not can_read_field(user, model, field_name):
            continue
        if instance and not can_read_field_state(user, field_name, instance.workflow_state):
            continue

        visible_fields.append({
            "name": field_name,
            "label": label,
            "mandatory": is_mandatory,
            "excluded": is_excluded,
        })

    return get_flat_fields(model, user)