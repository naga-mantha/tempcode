from django import forms

from apps.layout.models import Layout, LayoutBlock
from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.layout.constants import ALLOWED_COLS


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

    class Meta:
        model = LayoutBlock
        # Only choose the block when adding; columns default to inherit.
        fields = ["block"]

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

    # No responsive fields on add; all inherit by default


class LayoutBlockForm(forms.ModelForm):
    _inherit_choice = [("", "— inherit —")]
    col_sm = forms.TypedChoiceField(
        required=False,
        choices=_inherit_choice + [(c, str(c)) for c in ALLOWED_COLS],
        coerce=lambda v: int(v) if str(v).isdigit() else None,
    )
    col_md = forms.TypedChoiceField(
        required=False,
        choices=_inherit_choice + [(c, str(c)) for c in ALLOWED_COLS],
        coerce=lambda v: int(v) if str(v).isdigit() else None,
    )
    col_lg = forms.TypedChoiceField(
        required=False,
        choices=_inherit_choice + [(c, str(c)) for c in ALLOWED_COLS],
        coerce=lambda v: int(v) if str(v).isdigit() else None,
    )
    col_xl = forms.TypedChoiceField(
        required=False,
        choices=_inherit_choice + [(c, str(c)) for c in ALLOWED_COLS],
        coerce=lambda v: int(v) if str(v).isdigit() else None,
    )
    col_xxl = forms.TypedChoiceField(
        required=False,
        choices=_inherit_choice + [(c, str(c)) for c in ALLOWED_COLS],
        coerce=lambda v: int(v) if str(v).isdigit() else None,
    )

    class Meta:
        model = LayoutBlock
        # Allow editing base and responsive cols; ordering is via drag/drop.
        fields = ["col_sm", "col_md", "col_lg", "col_xl", "col_xxl"]

    # Explicitly normalize optional responsive cols: '' -> None
    def clean_col_sm(self):
        v = self.cleaned_data.get("col_sm")
        return v if isinstance(v, int) else None

    def clean_col_md(self):
        v = self.cleaned_data.get("col_md")
        return v if isinstance(v, int) else None

    def clean_col_lg(self):
        v = self.cleaned_data.get("col_lg")
        return v if isinstance(v, int) else None

    def clean_col_xl(self):
        v = self.cleaned_data.get("col_xl")
        return v if isinstance(v, int) else None

    def clean_col_xxl(self):
        v = self.cleaned_data.get("col_xxl")
        return v if isinstance(v, int) else None


class LayoutFilterConfigForm(forms.Form):
    name = forms.CharField()
    is_default = forms.BooleanField(required=False)

    def __init__(self, *args, filter_schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_schema = filter_schema
