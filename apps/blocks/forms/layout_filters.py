"""Forms for managing layout filter configurations."""

from __future__ import annotations

import json
from typing import Any

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError

from apps.blocks.models.layout import Layout, VisibilityChoices, validate_public_visibility
from apps.blocks.services.layout_filters import (
    clean_layout_filter_values,
    save_layout_filter_config,
)


class LayoutFilterConfigForm(forms.Form):
    """Form used to persist :class:`~apps.blocks.models.layout_filter_config.LayoutFilterConfig`."""

    name = forms.CharField(max_length=255)
    visibility = forms.ChoiceField(choices=VisibilityChoices.choices)
    is_default = forms.BooleanField(required=False)
    values_json = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args: Any, layout: Layout, acting_user, **kwargs: Any) -> None:
        self.layout = layout
        self.acting_user = acting_user
        super().__init__(*args, **kwargs)

    def clean_name(self) -> str:
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("A name is required for the saved filter.")
        return name

    def clean_visibility(self) -> str:
        value = self.cleaned_data.get("visibility") or VisibilityChoices.PRIVATE
        if value not in VisibilityChoices.values:
            value = VisibilityChoices.PRIVATE
        if value == VisibilityChoices.PUBLIC:
            validate_public_visibility(
                self.layout.owner,
                model_label="layout filter config",
            )
        return value

    def clean_values_json(self) -> dict[str, Any]:
        raw = self.cleaned_data.get("values_json")
        if raw in (None, ""):
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise forms.ValidationError("Invalid filter payload.") from exc
        if not isinstance(parsed, dict):
            raise forms.ValidationError("Invalid filter payload.")
        return parsed

    def save(self):
        if not self.is_valid():  # pragma: no cover - guard against misuse
            raise ValueError("Cannot save an invalid LayoutFilterConfigForm")
        cleaned_values = clean_layout_filter_values(
            self.layout,
            self.cleaned_data["values_json"],
            user=self.acting_user,
        )
        try:
            return save_layout_filter_config(
                self.layout,
                name=self.cleaned_data["name"],
                visibility=self.cleaned_data["visibility"],
                is_default=self.cleaned_data.get("is_default") or False,
                values=cleaned_values,
                acting_user=self.acting_user,
            )
        except ValidationError as exc:
            raise forms.ValidationError(exc.message_dict or exc.messages) from exc
        except PermissionDenied as exc:
            raise forms.ValidationError(str(exc)) from exc

