from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.layout.models import UserColumnConfig, TableViewConfig

User = get_user_model()

# Create default table column configuration for new users
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_column_configs(sender, instance, created, **kwargs):
    if not created:
        return

    for tvc in TableViewConfig.objects.all():
        cols = tvc.default_columns or []
        UserColumnConfig.objects.create(user=instance, table_config=tvc, name=f"Default ({tvc.table_name})", fields=cols, is_default=True)


# Create default table column configuration for existing users (new tables)
@receiver(post_save, sender=TableViewConfig)
def create_default_for_existing_users(sender, instance, created, **kwargs):
    if not created:
        return

    default_cols = instance.default_columns or []
    configs = []
    for user in User.objects.all():
        # don't overwrite if they somehow already have one
        if not UserColumnConfig.objects.filter(user=user, table_config=instance).exists():
            configs.append(
                UserColumnConfig(
                    user=user,
                    table_config=instance,
                    name=f"Default ({instance.table_name})",
                    fields=default_cols,
                    is_default=True
                )
            )
    UserColumnConfig.objects.bulk_create(configs)