from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.models.block import Block as DbBlock
from apps.blocks.models.block_filter_config import BlockFilterConfig


@receiver(post_save, sender=CustomUser)
def create_default_block_filters_for_new_user(sender, instance: CustomUser, created: bool, **kwargs):
    """On new user creation, ensure a default 'None' filter exists for all blocks.

    For each existing block, create a BlockFilterConfig named 'None' with empty
    values for this user if one does not exist. If it's the user's first filter
    for that block, mark it as default.
    """
    if not created:
        return
    try:
        for db_block in DbBlock.objects.all():
            qs = BlockFilterConfig.objects.filter(block=db_block, user=instance)
            if not qs.filter(name="None").exists():
                BlockFilterConfig.objects.create(
                    block=db_block,
                    user=instance,
                    name="None",
                    values={},
                    is_default=(not qs.exists()),
                )
    except Exception:
        # Avoid breaking user creation during migrations/startup
        pass

@receiver(post_save, sender=DbBlock)
def create_default_block_filters_for_new_block(sender, instance: DbBlock, created: bool, **kwargs):
    """On new block creation, ensure a 'None' filter exists for all users."""
    if not created:
        return
    try:
        for user in CustomUser.objects.all():
            qs = BlockFilterConfig.objects.filter(block=instance, user=user)
            if not qs.filter(name="None").exists():
                BlockFilterConfig.objects.create(
                    block=instance,
                    user=user,
                    name="None",
                    values={},
                    is_default=(not qs.exists()),
                )
    except Exception:
        pass
