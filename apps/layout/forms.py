from django import forms

from apps.layout.models import Layout, LayoutBlock
from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.layout.constants import ALLOWED_COLS, RESPONSIVE_COL_FIELDS


class LayoutForm(forms.ModelForm):
    class Meta:
        model = Layout
        fields = ["name", "visibility", "description"]

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = self._inherit_choice + [(c, str(c)) for c in ALLOWED_COLS]
        widget = forms.Select(attrs={"class": "form-select form-select-sm w-100"})
        coerce = lambda v: int(v) if str(v).isdigit() else None  # noqa: E731
        for name in RESPONSIVE_COL_FIELDS:
            self.fields[name] = forms.TypedChoiceField(
                required=False,
                choices=choices,
                coerce=coerce,
                widget=widget,
            )
        # Ensure title and note span full column width with Bootstrap styles
        if "title" in self.fields:
            self.fields["title"].widget.attrs.update({
                "class": "form-control form-control-sm w-100",
            })
        if "note" in self.fields:
            self.fields["note"].widget.attrs.update({
                "class": "form-control form-control-sm w-100",
                "rows": 2,
            })

    class Meta:
        model = LayoutBlock
        # Allow editing responsive cols and display metadata; ordering is via drag/drop.
        fields = list(RESPONSIVE_COL_FIELDS) + ["title", "note", "preferred_filter_name"]

    def clean(self):
        cleaned = super().clean()
        for key in RESPONSIVE_COL_FIELDS:
            v = cleaned.get(key)
            cleaned[key] = v if isinstance(v, int) else None
        return cleaned


class LayoutFilterConfigForm(forms.Form):
    name = forms.CharField()
    is_default = forms.BooleanField(required=False)

    def __init__(self, *args, filter_schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_schema = filter_schema
