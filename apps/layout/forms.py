from django import forms

from apps.layout.models import Layout, LayoutBlock
from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.layout.constants import GRID_MAX_COL_SPAN, GRID_MAX_ROW_SPAN


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
        qs = Block.objects.filter(code__in=valid_codes)
        field.queryset = qs
        # Build sorted choices by (app_name, block name) for display
        blocks = list(qs)
        def _app(obj: Block) -> str:
            meta = block_registry.metadata(obj.code) or {}
            return (meta.get("app_name") or "").strip()
        blocks.sort(key=lambda b: (_app(b).lower(), (b.name or "").lower()))
        # ModelChoiceField uses to_field_name='code', so values must be block.code
        field.widget.choices = [
            (b.code, f"{_app(b)}>{b.name}") for b in blocks
        ]

    # No responsive fields on add; all inherit by default


class LayoutBlockForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        span_choices = [(i, str(i)) for i in range(1, GRID_MAX_COL_SPAN + 1)]
        row_choices = [(i, str(i)) for i in range(1, GRID_MAX_ROW_SPAN + 1)]
        self.fields["col_span"] = forms.TypedChoiceField(
            required=True,
            choices=span_choices,
            coerce=int,
            widget=forms.Select(attrs={"class": "form-select form-select-sm w-100"}),
            initial=1,
            label="Column span",
        )
        self.fields["row_span"] = forms.TypedChoiceField(
            required=True,
            choices=row_choices,
            coerce=int,
            widget=forms.Select(attrs={"class": "form-select form-select-sm w-100"}),
            initial=1,
            label="Row span",
        )
        # Ensure title and note styling
        if "title" in self.fields:
            self.fields["title"].widget.attrs.update({"class": "form-control form-control-sm w-100"})
        if "note" in self.fields:
            self.fields["note"].widget.attrs.update({"class": "form-control form-control-sm w-100", "rows": 2})

    class Meta:
        model = LayoutBlock
        # Allow editing responsive cols and display metadata; ordering is via drag/drop.
        fields = [
            "col_span",
            "row_span",
            "title",
            "note",
            "preferred_filter_name",
            "preferred_column_config_name",
        ]



class LayoutFilterConfigForm(forms.Form):
    ACTIONS = (
        ("create", "create"),
        ("delete", "delete"),
        ("set_default", "set_default"),
    )
    action = forms.ChoiceField(choices=ACTIONS)
    config_id = forms.IntegerField(required=False)
    name = forms.CharField(required=False)

    def __init__(self, *args, filter_schema=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filter_schema = filter_schema
