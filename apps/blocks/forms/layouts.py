"""Forms for managing layout and layout block records."""

from __future__ import annotations

from typing import Any

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout as CrispyLayout, Row
from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.blocks.models.layout import Layout, VisibilityChoices, validate_public_visibility
from apps.blocks.models.layout_block import LayoutBlock


class LayoutForm(forms.ModelForm):
    """Model form used to manage :class:`~apps.blocks.models.layout.Layout` records."""

    helper: FormHelper

    class Meta:
        model = Layout
        fields = ["name", "slug", "description", "visibility", "is_default"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args: Any, user=None, **kwargs: Any) -> None:
        self.user = user
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True  # handled by outer form when rendered in templates
        self.helper.layout = CrispyLayout(
            Fieldset(
                "Layout Details",
                Row(
                    Column("name", css_class="col-md-6"),
                    Column("slug", css_class="col-md-6"),
                ),
                "description",
            ),
            Fieldset(
                "Visibility",
                Row(
                    Column("visibility", css_class="col-md-6"),
                    Column("is_default", css_class="col-md-6"),
                ),
            ),
        )

    def clean_visibility(self) -> str:
        visibility = self.cleaned_data.get("visibility")
        owner = getattr(self.instance, "owner", None)
        acting_user = self.user or owner
        if visibility == VisibilityChoices.PUBLIC:
            validate_public_visibility(acting_user, model_label="layout")
        return visibility

    def save(self, commit: bool = True) -> Layout:
        instance: Layout = super().save(commit=False)
        if not instance.pk and self.user is not None:
            instance.owner = self.user
        if commit:
            instance.save()
        return instance


class LayoutBlockForm(forms.ModelForm):
    """Inline form for :class:`~apps.blocks.models.layout_block.LayoutBlock`."""

    helper: FormHelper

    class Meta:
        model = LayoutBlock
        fields = [
            "block",
            "slug",
            "title",
            "configuration",
            "row_index",
            "column_index",
            "order",
        ]
        widgets = {
            "configuration": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        self.helper.layout = CrispyLayout(
            Fieldset(
                "Block",
                Row(
                    Column("block", css_class="col-md-6"),
                    Column("slug", css_class="col-md-6"),
                ),
                Row(
                    Column("title", css_class="col-md-6"),
                    Column("order", css_class="col-md-3"),
                    Column("row_index", css_class="col-md-3"),
                    Column("column_index", css_class="col-md-3"),
                ),
                "configuration",
            ),
        )


class BaseLayoutBlockFormSet(BaseInlineFormSet):
    """Inline formset helper that passes layout owner context to forms."""

    def __init__(self, *args: Any, user=None, **kwargs: Any) -> None:
        self.user = user
        super().__init__(*args, **kwargs)
        for form in self.forms:
            if hasattr(form, "helper"):
                form.helper.form_tag = False

    def save(self, commit: bool = True):
        instances = super().save(commit=False)
        if commit:
            for instance in instances:
                instance.save()
            for obj in self.deleted_objects:
                obj.delete()
        return instances


LayoutBlockFormSet = inlineformset_factory(
    Layout,
    LayoutBlock,
    form=LayoutBlockForm,
    formset=BaseLayoutBlockFormSet,
    extra=0,
    can_delete=True,
)
