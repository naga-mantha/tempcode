from django.core.management.base import BaseCommand, CommandError
from django.apps import apps as django_apps
from apps.permissions.utils import generate_field_permissions_for_model


class Command(BaseCommand):
    help = "Rebuild field-level permissions for all models."

    def handle(self, *args, **options):
        created_count = 0
        try:
            for model in django_apps.get_models():
                created_count += generate_field_permissions_for_model(model)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Field permissions rebuilt. Created {created_count} permissions."
                )
            )
        except Exception as exc:
            raise CommandError(f"Error rebuilding field permissions: {exc}")
