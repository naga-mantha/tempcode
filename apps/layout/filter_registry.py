# apps/layout/filter_registry.py

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

def get_filter_schema(table_name):
    return FILTER_REGISTRY.get(table_name, lambda: {})()
