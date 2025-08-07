from apps.blocks.models.field_display_rule import FieldDisplayRule
def get_field_display_rules(model_label):
    try:
        rules = FieldDisplayRule.objects.filter(model_label=model_label)
        return rules

    except Exception:
        return []

#
# def merge_column_config_with_rules(config_fields, model):
#     rules = get_field_display_rules(model)
#     mandatory = set(rules.get("mandatory", []))
#     excluded = set(rules.get("excluded", []))
#
#     final_fields = [f for f in config_fields if f not in excluded]
#     for f in mandatory:
#         if f not in final_fields:
#             final_fields.append(f)
#
#     return final_fields