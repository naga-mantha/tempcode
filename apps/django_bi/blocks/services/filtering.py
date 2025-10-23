"""Utilities for applying block filter registries."""

import logging
from apps.django_bi.blocks.registry import block_registry

logger = logging.getLogger(__name__)


def apply_filter_registry(table_name, queryset, filters, user):
    """Apply registered filter handlers to a queryset.

    Args:
        table_name (str): Name of the table block registered in ``block_registry``.
        queryset (QuerySet): Initial queryset to filter.
        filters (dict): Mapping of filter keys to values provided by the user.
        user (User): Current user used for resolving dynamic filter schema.

    Returns:
        QuerySet: The queryset after all matching filters have been applied.
    """
    block = block_registry.get(table_name)

    # Dynamic per-instance filter schema
    if block and hasattr(block, "get_filter_schema"):
        schema = block.get_filter_schema(user)
    else:
        schema = {}

    logger.debug("Resolved filter schema for %s: %s", table_name, schema)

    for key, config in schema.items():
        if key in filters and filters[key] is not None:
            logger.debug("Applying filter '%s' with value '%s'", key, filters[key])
            queryset = config["handler"](queryset, filters[key])
    return queryset
