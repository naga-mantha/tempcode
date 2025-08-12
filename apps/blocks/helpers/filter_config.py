from apps.blocks.models.block_filter_config import BlockFilterConfig


def get_user_filter_config(user, block):
    """Return the default filter configuration for a user and block."""
    config = BlockFilterConfig.objects.filter(
        block=block, user=user, is_default=True
    ).first()
    return config.values if config else {}

