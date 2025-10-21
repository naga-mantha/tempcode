from apps.django_bi.permissions.checks import get_editable_fields, get_readable_fields

class PermissionFormMixin:
    """
    A mixin that filters form fields based on user permissions:
    - Removes fields the user cannot read
    - Disables fields the user cannot write
    """

    def __init__(self, *args, user=None, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)

        if not user:
            raise ValueError("PermissionFormMixin requires a 'user' argument")
        model = self._meta.model
        instance = instance or getattr(self, 'instance', None)

        readable = set(get_readable_fields(user, model, instance))
        editable = set(get_editable_fields(user, model, instance))

        for name in list(self.fields.keys()):
            field = self.fields[name]
            if name not in readable:
                del self.fields[name]
            elif name not in editable:
                field.disabled = True
                # Disabled fields must not be required so form validation passes
                field.required = False
