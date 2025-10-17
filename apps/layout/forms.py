from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, HTML

from apps.layout.models import Layout, LayoutBlock
from apps.blocks.models.block import Block
from apps.layout.constants import GRID_MAX_COL_SPAN, GRID_MAX_ROW_SPAN


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
        # Limit selectable blocks to runtime v2 specs only.
        field = self.fields["block"]
        field.widget.attrs.update({"class": "form-select"})

        # v2 specs → ensure Block rows exist, collect codes
        try:
            from apps.blocks.register import load_specs
            from apps.blocks.registry import get_registry
            from apps.blocks.configs import get_block_for_spec
            load_specs()
            reg = get_registry()
            v2_objs = []
            for code, spec in reg.items():
                try:
                    obj = get_block_for_spec(code)
                    # set friendly name on first sync (if empty)
                    if not obj.name:
                        obj.name = getattr(spec, "name", code)
                        obj.save(update_fields=["name"])  # best-effort
                    v2_objs.append(obj)
                except Exception:
                    continue
        except Exception:
            v2_objs = []

        # De-duplicate by code
        seen = set()
        unique_objs = []
        for o in v2_objs:
            if o.code in seen:
                continue
            seen.add(o.code)
            unique_objs.append(o)
        field.queryset = Block.objects.filter(code__in=[o.code for o in unique_objs])
        # Build display choices
        choices = [("", "-- Select a block --")]
        v2_list = sorted(unique_objs, key=lambda b: (b.name or b.code).lower())
        choices.extend((b.code, f"{b.name or b.code}") for b in v2_list)
        field.widget.choices = choices

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
            "preferred_setting_name",
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
