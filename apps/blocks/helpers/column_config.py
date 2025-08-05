from apps.blocks.models.block_column_config import BlockColumnConfig

def get_user_column_config(user, block):
    config = BlockColumnConfig.objects.filter(block=block, user=user, is_default=True).first()
    return config.fields if config else []
