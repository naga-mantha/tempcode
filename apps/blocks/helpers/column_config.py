from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.permissions.checks import can_read_field
from apps.workflow.permissions import can_read_field_state
from django.db import models
from apps.blocks.helpers.field_rules import get_field_display_rules

def get_user_column_config(user, block):
    config = BlockColumnConfig.objects.filter(block=block, user=user, is_default=True).first()
    return config.fields if config else []

def get_model_fields_for_column_config(model, user):
    """
        Returns a list of dicts describing DB fields on `model`,
        expanding ForeignKey subfields (like 'workflow__status').

        Applies field display rules and user read permissions.
        """
    model_label = f"{model._meta.app_label}.{model.__name__}"
    rules = get_field_display_rules(model_label=model_label)
    rule_map = {r.field_name: r for r in rules}

    # dummy_instance = model()
    fields = []
    for field in model._meta.fields:
        rule = rule_map.get(field.name)
        if rule and rule.is_excluded:
            continue

        if user and not can_read_field(user, model, field.name):
            continue

        if isinstance(field, models.ForeignKey):
            rel_model = field.remote_field.model
            rel_label = f"{rel_model._meta.app_label}.{rel_model.__name__}"
            rel_rules = get_field_display_rules(model_label=rel_label)
            rel_rmap = {r.field_name: r for r in rel_rules}
            rel_instance = rel_model()

            for sub in rel_model._meta.fields:
                if sub.name == "id":
                    continue

                rel_rule = rel_rmap.get(sub.name)
                if rel_rule and rel_rule.is_excluded:
                    continue

                if user and not can_read_field(user, rel_instance, sub.name):
                    continue

                fields.append({
                    "name": f"{field.name}__{sub.name}",
                    "label": f"{sub.verbose_name}",
                    "model": f"{rel_model._meta.label}",
                    "mandatory": rel_rule.is_mandatory if rel_rule else False,
                    "editable": False,
                })
        else:
            fields.append({
                "name": field.name,
                "label": field.verbose_name,
                "model": f"{model._meta.label}",
                "mandatory": rule.is_mandatory if rule else False,
                "editable": True,
            })

    return fields

