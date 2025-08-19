from django import forms

from apps.layout.models import Layout, LayoutBlock
from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block


class LayoutForm(forms.ModelForm):
    class Meta:
        model = Layout
        fields = ["name", "visibility"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only staff/admin can choose visibility; others default to Private
        if user is not None and not getattr(user, "is_staff", False):
            self.fields.pop("visibility", None)


class AddBlockForm(forms.ModelForm):
    # Use ModelChoiceField so cleaned_data['block'] is a Block instance.
    block = forms.ModelChoiceField(queryset=Block.objects.none(), to_field_name="code")
    # Restrict allowed Bootstrap column widths
    ALLOWED_COLS = (1, 2, 3, 4, 6, 12)
    col = forms.TypedChoiceField(
        choices=[(c, str(c)) for c in ALLOWED_COLS], coerce=int
    )

    class Meta:
        model = LayoutBlock
        # Only expose block and column width; ordering is set automatically to the end.
        fields = ["block", "col"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit selectable blocks to those registered in the runtime registry.
        valid_codes = list(block_registry.all().keys())
        field = self.fields["block"]
        field.queryset = Block.objects.filter(code__in=valid_codes)
        # Label format: APPNAME>BLOCKNAME using registry metadata only
        def _label(obj: Block):
            meta = block_registry.metadata(obj.code) or {}
            app_name = meta.get("app_name") or ""
            return f"{app_name}>{obj.name}"
        field.label_from_instance = _label


class LayoutBlockForm(forms.ModelForm):
    # Reuse the same allowed column choices for editing
    ALLOWED_COLS = (1, 2, 3, 4, 6, 12)
    col = forms.TypedChoiceField(
        choices=[(c, str(c)) for c in ALLOWED_COLS], coerce=int
    )

    class Meta:
        model = LayoutBlock
        # Only allow editing of column width in the editor; ordering is via drag/drop.
        fields = ["col"]


class LayoutFilterConfigForm(forms.Form):
    name = forms.CharField()
    is_default = forms.BooleanField(required=False)

    def __init__(self, *args, filter_schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_schema = filter_schema
