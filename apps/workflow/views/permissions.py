def can_read_field(user, instance, field_name):
    """
    Returns True if `user` may view (read) this single field.
    Uses Django's permission codename: view_<model>_<field>.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    app_label = instance._meta.app_label
    model_name = instance._meta.model_name
    codename = f"view_{model_name}_{field_name}"
    perm_string = f"{app_label}.{codename}"

    return user.has_perm(perm_string)

def can_write_field(user, instance, field_name):
    """
    Returns True if `user` may change (write) this single field.
    Uses Django's permission codename: change_<model>_<field>.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    app_label = instance._meta.app_label
    model_name = instance._meta.model_name
    codename = f"change_{model_name}_{field_name}"
    perm_string = f"{app_label}.{codename}"

    return user.has_perm(perm_string)

def get_allowed_fields(user, model, action):
    """
    Returns list of field names on the model the user is allowed to perform `action` on.
    Uses Django's built-in per-field perms.
    """
    instance = model()
    # pick appropriate checker
    if action == 'view':
        checker = can_read_field
    elif action == 'change' or action == 'write':
        checker = can_write_field
    else:
        raise ValueError(f"Unknown action: {action}")

    allowed = []
    for field in model._meta.get_fields():
        # skip relations
        if not hasattr(field, 'attname'):
            continue
        if checker(user, instance, field.name):
            allowed.append(field.name)

    return allowed

class FieldLevelFormMixin:
    """
    Hides form fields the user can’t read, and disables those they can’t write.
    """

    def __init__(self, *args, user=None, **kwargs):
        self._user = user
        super().__init__(*args, **kwargs)
        self._instance = getattr(self, 'instance', None)

        if user and user.is_superuser:
            return

        # Prune or disable fields
        for fname in list(self.fields):
            if fname == 'workflow':
                continue

            # If no read-perm, remove the field entirely
            if not can_read_field(user, self._instance, fname):
                self.fields.pop(fname)
            # Else if no write-perm, disable it
            elif not can_write_field(user, self._instance, fname):
                self.fields[fname].disabled = True

    def clean(self):
        cleaned = super().clean()

        for fname in list(cleaned):
            if fname == 'workflow':
                continue
            # If user lacks write-perm, drop the cleaned data
            if not can_write_field(self._user, self._instance, fname):
                cleaned.pop(fname)

        return cleaned
