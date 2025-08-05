from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.registry import get_block

def get_user_filter_config(user, block):
    config = BlockFilterConfig.objects.filter(block=block, user=user, is_default=True).first()
    return config.values if config else {}

def apply_filter_registry(table_name, queryset, filters, user):
    block = get_block(table_name)

    # ✅ dynamic per-instance filter schema
    if block and hasattr(block, "get_filter_schema"):
        schema = block.get_filter_schema(user)
    else:
        schema = {}

    for key, config in schema.items():
        if key in filters and filters[key] is not None:
            queryset = config["handler"](queryset, filters[key])
    return queryset