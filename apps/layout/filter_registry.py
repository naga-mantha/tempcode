# apps/layout/filter_registry.py

FILTER_REGISTRY = {}

def register(table_name, schema_loader):
    FILTER_REGISTRY[table_name] = schema_loader

def get_filter_schema(table_name):
    return FILTER_REGISTRY.get(table_name, lambda: {})()
