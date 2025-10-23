from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, HTML

from django_bi.layout.models import Layout, LayoutBlock
from django_bi.blocks.registry import block_registry
from django_bi.blocks.models.block import Block
from django_bi.layout.constants import GRID_MAX_COL_SPAN, GRID_MAX_ROW_SPAN


class LayoutForm(forms.ModelForm):
    class Meta:
        model = Layout
        fields = ["name", "visibility", "category", "description"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Bootstrap classes for widgets
        if "name" in self.fields:
            self.fields["name"].widget.attrs.update({"class": "form-control"})
        if "visibility" in self.fields:
            self.fields["visibility"].widget.attrs.update({"class": "form-select"})
        if "category" in self.fields:
            self.fields["category"].widget.attrs.update({"class": "form-control"})
        if "description" in self.fields:
            self.fields["description"].widget.attrs.update({"class": "form-control", "rows": 3})
        # Only staff/admin can change visibility; others see it disabled
        if user is not None and not getattr(user, "is_staff", False):
            vis = self.fields.get("visibility")
            if vis is not None:
                # Show current/default value but prevent editing
                vis.disabled = True
                vis.widget.attrs.update({"disabled": "disabled"})
                # Optional: hint that privacy is enforced
                vis.help_text = (vis.help_text or "") + ""
        # Crispy helper for Bootstrap layout
        self.helper = FormHelper()
        self.helper.form_tag = False  # outer form tag is in template
        # Hide description label; we'll render it as a separate row header
        if "description" in self.fields:
            self.fields["description"].label = ""
        # Build rows dynamically based on visibility presence
        has_visibility = "visibility" in self.fields
        if has_visibility:
            top_row = Row(
                Column(Field("name"), css_class="col-md-4"),
                Column(Field("visibility"), css_class="col-md-4"),
                Column(Field("category"), css_class="col-md-4"),
            )
        else:
            top_row = Row(
                Column(Field("name"), css_class="col-12"),
            )
            # Show category on its own row when visibility is hidden
            cat_row = Row(Column(Field("category"), css_class="col-12"))
        desc_label_row = Row(HTML('<label class="form-label">Description</label>'))
        desc_field_row = Row(Column(Field("description"), css_class="col-12"))
        if has_visibility:
            self.helper.layout = Layout(top_row, desc_label_row, desc_field_row)
        else:
            self.helper.layout = Layout(top_row, cat_row, desc_label_row, desc_field_row)


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
        field.widget.attrs.update({"class": "form-select"})
        # Build sorted choices by (app_name, block name) for display
        blocks = list(qs)
        def _app(obj: Block) -> str:
            meta = block_registry.metadata(obj.code) or {}
            return (meta.get("app_name") or "").strip()
        blocks.sort(key=lambda b: (_app(b).lower(), (b.name or "").lower()))
        # ModelChoiceField uses to_field_name='code', so values must be block.code
        # Prepend an empty placeholder so the first real option isn't preselected.
        field.widget.choices = [("", "-- Select a block --")] + [
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
