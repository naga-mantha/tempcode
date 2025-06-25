from django.apps import apps
from apps.layout.models import TableViewConfig

def get_model_from_table(table_name: str):
    """
    Given the string table_name (as stored in TableViewConfig.table_name),
    look up the corresponding TableViewConfig, parse its `model_label`
    (e.g. "org.NewEmployee"), and return the actual model class.
    """
    # 1) Find the config row
    config = TableViewConfig.objects.get(table_name=table_name)
    # 2) Split out "app_label.ModelName"
    app_label, model_name = config.model_label.split(".")
    # 3) Fetch the model class
    model = apps.get_model(app_label, model_name)
    if model is None:
        raise LookupError(f"Model '{config.model_label}' not found for table '{table_name}'")
    return model
