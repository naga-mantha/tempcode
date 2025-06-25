from django.db.models.signals import post_save
from django.dispatch       import receiver
from django.conf           import settings
from django.apps           import apps as django_apps
from apps.layout.models               import UserColumnConfig, TableViewConfig

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_column_configs(sender, instance, created, **kwargs):
    if not created:
        return

    for tvc in TableViewConfig.objects.all():
        # read the list the admin filled in
        cols = tvc.default_columns or []

        UserColumnConfig.objects.create(
            user=instance,
            table_config=tvc,
            name=f"Default ({tvc.table_name})",
            fields=cols,
            is_default=True,
        )
