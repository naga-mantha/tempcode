from django.apps import apps as django_apps
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

@receiver(post_migrate)
def generate_field_permissions(sender, **kwargs):
    """
    After every migrate, ensure each concrete model field has a
    view_ and change_ permission (i.e. read/write) in Django's auth system.
    """
    for model in django_apps.get_models():
        ct = ContentType.objects.get_for_model(model)
        model_name = model._meta.model_name
        verbose_name = model._meta.verbose_name.title()

        for field in model._meta.fields:
            field_name = field.name

            # READ permission
            codename_r = f"view_{model_name}_{field_name}"
            name_r = f'Can view field "{field_name}" on Model "{verbose_name}"'
            Permission.objects.get_or_create(codename=codename_r, content_type=ct, defaults={"name": name_r})

            # WRITE permission
            codename_w = f"change_{model_name}_{field_name}"
            name_w = f'Can change field "{field_name}" on Model "{verbose_name}"'
            Permission.objects.get_or_create(codename=codename_w, content_type=ct, defaults={"name": name_w})
