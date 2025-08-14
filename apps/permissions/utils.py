from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


def generate_field_permissions_for_model(model):
    """Ensure view/change permissions exist for each editable field of ``model``.

    Iterates over both concrete fields and explicit many-to-many relations while
    skipping auto-created or non-editable fields. Returns the number of
    permissions created.
    """

    created_count = 0
    ct = ContentType.objects.get_for_model(model)
    model_name = model._meta.model_name
    verbose_name = model._meta.verbose_name.title()

    for field in list(model._meta.fields) + list(model._meta.many_to_many):
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

    return created_count

