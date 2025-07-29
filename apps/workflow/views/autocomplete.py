# NOT NEEDED ANYMORE



from dal import autocomplete
from django.contrib.contenttypes.models import ContentType

class ContentTypeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = ContentType.objects.all()
        if self.q:
            qs = qs.filter(app_label__icontains=self.q) | qs.filter(model__icontains=self.q)
        return qs

class FieldNameAutocomplete(autocomplete.Select2ListView):
    """
    Returns a list of field-name strings for the ContentType passed via `forward`,
    *plus* the special "__model__" for doctype-level perms.
    """
    def get_list(self):
        ct_id = self.forwarded.get('content_type', None)
        if not ct_id:
            return []

        try:
            ct = ContentType.objects.get(pk=ct_id)
        except ContentType.DoesNotExist:
            return []

        model = ct.model_class()
        # real model fields (no auto-created or m2m)
        fields = [f.name for f in model._meta.get_fields() if not (f.auto_created or f.many_to_many)]

        # always allow the doctype-level "__model__"
        all_choices = ["__model__"] + fields

        if self.q:
            q = self.q.lower()
            return [f for f in all_choices if q in f.lower()]

        return all_choices