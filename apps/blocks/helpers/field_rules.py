from django.apps import apps

def get_field_display_rules(model_label):
    try:
        app_label = model_label.split(".")[0]
        model = apps.get_model(app_label, "FieldDisplayRule")
        return model.objects.filter(model_label=model_label)
    except Exception:
        return []
