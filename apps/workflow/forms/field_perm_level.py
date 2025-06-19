# apps/workflow/forms.py

from django import forms
from dal import autocomplete
from django.contrib.contenttypes.models import ContentType

from apps.workflow.models import FieldPermLevel

class FieldPermLevelForm(forms.ModelForm):
    class Meta:
        model  = FieldPermLevel
        fields = ['content_type', 'field_name', 'permlevel']
        widgets = {
            'content_type': autocomplete.ModelSelect2(
                url='workflow:contenttype-autocomplete',
                attrs={'data-placeholder': 'Model…', 'data-minimum-input-length': 1}
            ),
            'field_name': autocomplete.ListSelect2(
                url='workflow:fieldname-autocomplete',
                forward=['content_type'],
                attrs={'data-placeholder': 'Field…', 'data-minimum-input-length': 0}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If we're editing an existing FieldPermLevel, make sure
        # the current field_name appears as a choice so Select2 can
        # display its label.
        if self.instance and self.instance.pk:
            current = self.instance.field_name
            # set the initial value
            self.fields['field_name'].initial = current
            # give the widget one choice that matches it
            self.fields['field_name'].widget.choices = [(current, current)]
