# apps/layout/helpers/label_helpers.py

from django.utils.text import capfirst

def get_verbose_label(model, field_path):
    """
    Given a Django model class and a field path like "workflow__name",
    traverse into related models and return the final field's verbose_name,
    capitalized.
    """
    parts = field_path.split("__")
    for part in parts:
        field = model._meta.get_field(part)
        if hasattr(field, "related_model") and field.related_model:
            model = field.related_model
        else:
            break
    return capfirst(str(field.verbose_name))


def get_column_labels(model, field_paths):
    """
    Given a model class and a list of field_paths (e.g. ["id", "workflow__name", ...]),
    returns a dict mapping each path to its verbose_name—no disambiguation prefixes.
    """
    return { fp: get_verbose_label(model, fp) for fp in field_paths }
