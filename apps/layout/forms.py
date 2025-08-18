from django import forms

from apps.layout.models import Layout, LayoutBlock
from apps.blocks.registry import block_registry


class LayoutForm(forms.ModelForm):
    class Meta:
        model = Layout
        fields = ["name", "visibility"]


class AddBlockForm(forms.ModelForm):
    block = forms.ChoiceField()

    class Meta:
        model = LayoutBlock
        fields = ["block", "row", "col", "width", "height"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [(name, name) for name in block_registry.all().keys()]
        self.fields["block"].choices = choices


class LayoutFilterConfigForm(forms.Form):
    id = forms.IntegerField(required=False)
    name = forms.CharField()
    is_default = forms.BooleanField(required=False)

    def __init__(self, *args, filter_schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_schema = filter_schema
