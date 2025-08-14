from django.core.management.base import BaseCommand, CommandError
from django.apps import apps as django_apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = "Rebuild field-level permissions for all models."

    def handle(self, *args, **options):
        created_count = 0
        try:
            for model in django_apps.get_models():
                ct = ContentType.objects.get_for_model(model)
                model_name = model._meta.model_name
                verbose_name = model._meta.verbose_name.title()

                for field in model._meta.fields:
                    if field.auto_created or not field.editable:
                        continue
                    field_name = field.name

                    # READ permission
                    codename_r = f"view_{model_name}_{field_name}"
                    name_r = f'Can view field "{field_name}" on Model "{verbose_name}"'
                    _, created = Permission.objects.get_or_create(
                        codename=codename_r,
                        content_type=ct,
                        defaults={"name": name_r},
                    )
                    if created:
                        created_count += 1

                    # WRITE permission
                    codename_w = f"change_{model_name}_{field_name}"
                    name_w = f'Can change field "{field_name}" on Model "{verbose_name}"'
                    _, created = Permission.objects.get_or_create(
                        codename=codename_w,
                        content_type=ct,
                        defaults={"name": name_w},
                    )
                    if created:
                        created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Field permissions rebuilt. Created {created_count} permissions."
                )
            )
        except Exception as exc:
            raise CommandError(f"Error rebuilding field permissions: {exc}")
