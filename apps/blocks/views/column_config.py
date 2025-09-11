from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.helpers.column_config import get_model_fields_for_column_config
from apps.blocks.registry import block_registry


class ColumnConfigForm(forms.Form):
    ACTIONS = (
        ("create", "create"),
        ("delete", "delete"),
        ("set_default", "set_default"),
    )
    action = forms.ChoiceField(choices=ACTIONS)
    config_id = forms.IntegerField(required=False)
    name = forms.CharField(required=False)
    fields = forms.MultipleChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop("fields_choices", [])
        self.readable_fields = set(kwargs.pop("readable_fields", []))
        super().__init__(*args, **kwargs)
        self.fields["fields"].choices = choices

    def clean_fields(self):
        fields = self.cleaned_data.get("fields") or []
        invalid = [f for f in fields if f not in self.readable_fields]
        if invalid:
            raise forms.ValidationError("Invalid fields selected.")
        return fields


class ColumnConfigView(LoginRequiredMixin, FormView):
    template_name = "blocks/table/column_config_view.html"
    form_class = ColumnConfigForm

    def dispatch(self, request, block_name, *args, **kwargs):
        # block_name in URL represents the Block.code
        self.block = get_object_or_404(Block, code=block_name)
        self.block_instance = block_registry.get(block_name)
        if not self.block_instance:
            raise Http404(f"Block '{block_name}' not found.")
        self.user = request.user
        self.model = self.block_instance.get_model()
        # Respect blocks that expose curated Manage Views fields
        allowed = None
        if hasattr(self.block_instance, "get_manageable_fields"):
            try:
                allowed = set(self.block_instance.get_manageable_fields(self.user) or [])
            except Exception:
                allowed = None
        # Allow per-block control of traversal depth
        try:
            max_depth = int(getattr(self.block_instance, "get_column_config_max_depth")())
        except Exception:
            max_depth = 10
        all_fields = get_model_fields_for_column_config(self.model, self.user, max_depth=max_depth)
        if allowed:
            self.fields_metadata = [f for f in all_fields if f.get("name") in allowed]
        else:
            self.fields_metadata = all_fields
        return super().dispatch(request, block_name, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configs = BlockColumnConfig.objects.filter(block=self.block, user=self.user)
        context.update({
            "block": self.block,
            "block_title": getattr(self.block, "name", ""),
            "configs": configs,
            "fields_metadata": self.fields_metadata,
        })
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "fields_choices": [
                    (f["name"], f["label"]) for f in self.fields_metadata
                ],
                "readable_fields": {f["name"] for f in self.fields_metadata},
            }
        )
        return kwargs

    def form_valid(self, form):
        action = form.cleaned_data["action"]
        config_id = form.cleaned_data.get("config_id")
        name = form.cleaned_data.get("name")

        if action == "create":
            field_list = form.cleaned_data.get("fields") or []
            existing = BlockColumnConfig.objects.filter(block=self.block, user=self.user, name=name).first()
            if existing:
                existing.fields = field_list
                existing.save()
            else:
                BlockColumnConfig.objects.create(block=self.block, user=self.user, name=name, fields=field_list)
        elif action == "delete" and config_id:
            BlockColumnConfig.objects.get(id=config_id, user=self.user, block=self.block).delete()
        elif action == "set_default" and config_id:
            config = BlockColumnConfig.objects.get(id=config_id, user=self.user, block=self.block)
            config.is_default = True
            config.save()
        return redirect("column_config_view", block_name=self.block.code)
