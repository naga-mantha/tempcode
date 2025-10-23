from django_bi.blocks.models.field_display_rule import FieldDisplayRule


def get_field_display_rules(model_label):
    try:
        return FieldDisplayRule.objects.for_model(model_label)
    except Exception:
        return []
