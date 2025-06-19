from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from apps.workflow.models import FieldPermLevel, FieldPermission

def get_field_permlevel(instance, field_name):
    """
    Return permlevel integer for model instance + field.
    """
    ct = ContentType.objects.get_for_model(instance.__class__)
    fpl = FieldPermLevel.objects.filter(
        content_type=ct,
        field_name=field_name
    ).first()
    return fpl.permlevel if fpl else None

def has_field_permission(user, instance, field_name, action):
    """
    Check whether `user` is allowed `action` on `field_name` of `instance`.
    - Superusers bypass all checks.
    - Unauthenticated users are denied.
    - If no permlevel is defined for that field, deny by default.
    - If no FieldPermission row exists for (permlevel + any of user’s groups), deny.
    - Otherwise, allow only if `action` is in that row’s JSON `actions` list.
    """
    # Superusers bypass all rules
    if user.is_superuser:
        return True

    if not user.is_authenticated:
        return False

    lvl = get_field_permlevel(instance, field_name)
    if lvl is None:
        return False

    # 3. Look for a matching FieldPermission for this permlevel and any of the user’s groups
    ct = ContentType.objects.get_for_model(instance.__class__)
    fp = FieldPermission.objects.filter(
        content_type=ct,
        permlevel=lvl,
        group__in=user.groups.all()
    ).first()
    if not fp:
        # no role mapping → deny
        return False

    # 4. Finally, check that the desired action is in the JSONField
    return action in fp.actions

def has_model_permission(user, model, action):
    """
     Treat model-level perms as field_name='__model__'.
     """
    if user.is_superuser:
        return True
    if not user.is_authenticated:
        return False

    ct = ContentType.objects.get_for_model(model)
    lvl = FieldPermLevel.objects.filter(
        content_type=ct,
        field_name="__model__"
    ).values_list('permlevel', flat=True).first()
    if lvl is None:
        return False

    return FieldPermission.objects.filter(
        content_type=ct,
        permlevel=lvl,
        group__in=user.groups.all(),
        actions__contains=[action]
    ).exists()

class FieldLevelFormMixin:
    """
    Hides fields the user can’t read and disables fields they can’t write.
    """

    def __init__(self, *args, user=None, **kwargs):
        # 0) Always store the user & (later) the instance
        self._user = user

        # bind the ModelForm (so instance & initial data are set)
        super().__init__(*args, **kwargs)
        self._instance = getattr(self, 'instance', None)

        # 1) Superusers skip pruning, but still have _user/_instance set
        if user and user.is_superuser:
            return

        # Now prune fields
        for fname in list(self.fields):
            # never prune the 'workflow' FK in your forms
            if fname == 'workflow':
                continue
            # If no read permission, drop it
            if not has_field_permission(user, self._instance, fname, 'read'):
                self.fields.pop(fname)
            # Else if no write permission, disable it
            elif not has_field_permission(user, self._instance, fname, 'write'):
                self.fields[fname].disabled = True

    def clean(self):
        cleaned = super().clean()
        for fname in list(cleaned):
            # never drop the workflow FK
            if fname == 'workflow':
                continue
            if not has_field_permission(self._user, self._instance, fname, 'write'):
                cleaned.pop(fname)
        return cleaned