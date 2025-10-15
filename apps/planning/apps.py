from django.apps import AppConfig


class PlanningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.planning'
    verbose_name = 'Planning'

    def ready(self):
        # Legacy v1 block registry disabled (migrated to specs)
        return

