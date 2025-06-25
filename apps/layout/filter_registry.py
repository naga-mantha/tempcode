from apps.workflow.views.permissions import can_read_field
from apps.layout.helpers.get_model_from_table import get_model_from_table

FILTER_REGISTRY = {}

def register(table_name):
    """
    Decorator to register a filter‐schema loader for a given table_name.
    Usage:
      @register("newemployee")
      def load_newemployee_filters(): …
    """
    def decorator(schema_loader):
        FILTER_REGISTRY[table_name] = schema_loader
        return schema_loader
    return decorator

def get_filter_schema(table_name, user):
    """
    Returns the filter‐schema for `table_name`.
    If `user` is provided, drops any filters on fields the user
    cannot view.
    """
    schema = FILTER_REGISTRY.get(table_name, lambda: {})()
    if user:
        # figure out the model for this table
        model = get_model_from_table(table_name)
        instance = model()

        # only keep keys the user can read
        schema = {
            name: cfg
            for name, cfg in schema.items()
            if can_read_field(user, instance, name)
        }
    return schema