from django.apps import apps
from django.db import models
from apps.permissions.checks import can_read_field
from apps.common.models.field_display_rule import FieldDisplayRule
def get_field_display_rules(model_label):
    try:
        app_label = model_label.split(".")[0]
        model = apps.get_model(app_label, "FieldDisplayRule")
        return model.objects.filter(model_label=model_label)
    except Exception:
        return []



def get_flat_fields(model, user=None):
    """
    Returns a list of dicts describing DB fields on `model`,
    expanding ForeignKey subfields (like 'workflow__status').

    Applies field display rules and user read permissions.
    """
    model_label = f"{model._meta.app_label}.{model.__name__}"
    rules = FieldDisplayRule.objects.filter(model_label=model_label)
    rule_map = {r.field_name: r for r in rules}

    dummy_instance = model()
    fields = []
    print("IIIIIIIIIIIIIIIIIIIIIIIIIIIII")

    for field in model._meta.fields:
        rule = rule_map.get(field.name)
        if rule and rule.is_excluded:
            continue

        if user and not can_read_field(user, dummy_instance, field.name):
            continue

        if isinstance(field, models.ForeignKey):
            rel_model = field.remote_field.model
            rel_label = f"{rel_model._meta.app_label}.{rel_model.__name__}"
            rel_rules = FieldDisplayRule.objects.filter(model_label=rel_label)
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
                    "label": f"{field.verbose_name} → {sub.verbose_name}",
                    "mandatory": rel_rule.is_mandatory if rel_rule else False,
                    "editable": False,
                })
        else:
            fields.append({
                "name": field.name,
                "label": field.verbose_name.title(),
                "mandatory": rule.is_mandatory if rule else False,
                "editable": True,
            })

    return fields
