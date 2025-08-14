from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.text import capfirst


def generate_field_permissions_for_model(model):
    """Ensure view/change permissions exist for each editable field of ``model``.

    Iterates over both concrete fields and explicit many-to-many relations while
    skipping auto-created or non-editable fields. Returns a tuple of the number
    of permissions created and deleted, respectively.
    """

    ct = ContentType.objects.get_for_model(model)
    model_name = model._meta.model_name
    verbose_name = capfirst(model._meta.verbose_name)

    # Determine expected permissions for each editable field
    expected_perms = {}
    for field in list(model._meta.fields) + list(model._meta.many_to_many):
        if field.auto_created or not field.editable:
            continue
        field_name = field.name
        expected_perms[f"view_{model_name}_{field_name}"] = (
            f'Can view field "{field_name}" on Model "{verbose_name}"'
        )
        expected_perms[f"change_{model_name}_{field_name}"] = (
            f'Can change field "{field_name}" on Model "{verbose_name}"'
        )

    # Collect existing field-level permissions for this model
    existing_qs = Permission.objects.filter(content_type=ct).filter(
        Q(codename__startswith=f"view_{model_name}_")
        | Q(codename__startswith=f"change_{model_name}_")
    )
    existing_codenames = set(existing_qs.values_list("codename", flat=True))

    # Delete permissions for fields no longer present
    to_delete = existing_codenames - expected_perms.keys()
    deleted_count = 0
    if to_delete:
        deleted_count, _ = Permission.objects.filter(
            content_type=ct, codename__in=to_delete
        ).delete()

    # Bulk-create any missing permissions
    to_create = [
        Permission(codename=codename, name=name, content_type=ct)
        for codename, name in expected_perms.items()
        if codename not in existing_codenames
    ]
    created_objs = Permission.objects.bulk_create(to_create)
    created_count = len(created_objs)

    return created_count, deleted_count

