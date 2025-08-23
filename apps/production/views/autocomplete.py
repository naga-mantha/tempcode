from dal_select2.views import Select2QuerySetView
from apps.common.models import Item


class ItemAutocomplete(Select2QuerySetView):
    """Autocomplete for Item model using select2."""

    def get_queryset(self):
        qs = Item.objects.all()
        if self.q:
            qs = qs.filter(code__icontains=self.q)
        return qs
