from django import forms
from apps.permissions.checks import can_read_field, can_write_field

class PermissionFormMixin:
    """
    A mixin that filters form fields based on user permissions:
    - Removes fields the user cannot read
    - Disables fields the user cannot write
    """

    def __init__(self, *args, user=None, instance=None, **kwargs):
        super().__init__(*args, **kwargs)

        if not user:
            raise ValueError("PermissionFormMixin requires a 'user' argument")

        self._permission_user = user
        model = self._meta.model
        instance = instance or getattr(self, 'instance', None)

        fields_to_remove = []
        for name, field in self.fields.items():
            if not can_read_field(user, model, name, instance):
                fields_to_remove.append(name)
            elif not can_write_field(user, model, name, instance):
                field.disabled = True

        for name in fields_to_remove:
            del self.fields[name]
