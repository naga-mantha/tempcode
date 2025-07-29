def _get_perm_codename(model, field_name, mode):
    """
    Returns: app_label.view_model_field or app_label.change_model_field
    """
    model_name = model._meta.model_name
    app_label = model._meta.app_label
    return f"{app_label}.{mode}_{model_name}_{field_name}"

# -------------------------------------------------------- FIELD LEVEL PERMISSIONS
def can_read_field(user, model, field_name, instance=None):
    """
    Checks if the user can read a specific field.
    Requires both:
    - model-level 'view' permission
    - field-level 'view' permission
    """
    if user.is_superuser or user.is_staff:
        return True

    # Step 1: check model-level view permission
    if not can_view_model(user, model):
        return False

    # Step 2: check field-level view permission
    perm = _get_perm_codename(model, field_name, "view")
    return user.has_perm(perm)


def can_write_field(user, model, field_name, instance=None):
    """
    Checks if the user can write to a specific field.
    Requires both:
    - model-level 'change' permission
    - field-level 'change' permission
    """
    if user.is_superuser or user.is_staff:
        return True

    # Step 1: check model-level change permission
    if not can_change_model(user, model):
        return False

    # Step 2: check field-level change permission
    perm = _get_perm_codename(model, field_name, "change")
    return user.has_perm(perm)

def get_editable_fields(user, model, instance=None):
    return [
        field.name
        for field in model._meta.fields
        if can_write_field(user, model, field.name, instance)
    ]

def get_readable_fields(user, model, instance=None):
    return [
        field.name
        for field in model._meta.fields
        if can_read_field(user, model, field.name, instance)
    ]
# -------------------------------------------------------- MODEL LEVEL PERMISSIONS
def can_view_model(user, model):
    """
    Wrapper for checking if user can view this model at all.
    """
    if user.is_superuser or user.is_staff:
        return True

    app_label = model._meta.app_label
    model_name = model._meta.model_name
    perm = f"{app_label}.view_{model_name}"
    return user.has_perm(perm)


def can_add_model(user, model):
    """
    Checks if user can add new records to the model.
    """
    if user.is_superuser or user.is_staff:
        return True

    app_label = model._meta.app_label
    model_name = model._meta.model_name
    perm = f"{app_label}.add_{model_name}"
    return user.has_perm(perm)


def can_change_model(user, model):
    """
    Checks if user can generally change records for this model.
    """
    if user.is_superuser or user.is_staff:
        return True

    app_label = model._meta.app_label
    model_name = model._meta.model_name
    perm = f"{app_label}.change_{model_name}"
    return user.has_perm(perm)


def can_delete_model(user, model):
    """
    Checks if user can delete records from this model.
    """
    if user.is_superuser or user.is_staff:
        return True

    app_label = model._meta.app_label
    model_name = model._meta.model_name
    perm = f"{app_label}.delete_{model_name}"
    return user.has_perm(perm)

# -------------------------------------------------------- INSTANCE LEVEL PERMISSIONS
def can_delete_instance(user, instance):
    """
    Checks if user is allowed to delete a specific instance.
    Extend this with custom rules such as:
    - Only the creator can delete
    - Cannot delete if instance is 'locked' or 'approved'
    """
    if user.is_superuser or user.is_staff:
        return True

    model = type(instance)
    if not can_delete_model(user, model):
        return False

    # TODO: Add custom logic, e.g.
    # if hasattr(instance, "created_by") and instance.created_by != user:
    #     return False

    return True
