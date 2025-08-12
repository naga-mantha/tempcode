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
    fields = forms.CharField(required=False)


class ColumnConfigView(LoginRequiredMixin, FormView):
    template_name = "blocks/table/column_config_view.html"
    form_class = ColumnConfigForm

    def dispatch(self, request, block_name, *args, **kwargs):
        self.block = get_object_or_404(Block, name=block_name)
        self.block_instance = block_registry.get(block_name)
        if not self.block_instance:
            raise Http404(f"Block '{block_name}' not found.")
        self.user = request.user
        return super().dispatch(request, block_name, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = self.block_instance.get_model()
        configs = BlockColumnConfig.objects.filter(block=self.block, user=self.user)
        fields_metadata = get_model_fields_for_column_config(model, self.user)
        context.update({
            "block": self.block,
            "configs": configs,
            "fields_metadata": fields_metadata,
        })
        return context

    def form_valid(self, form):
        action = form.cleaned_data["action"]
        config_id = form.cleaned_data.get("config_id")
        name = form.cleaned_data.get("name")

        if action == "create":
            fields = form.cleaned_data.get("fields") or ""
            field_list = [f.strip() for f in fields.split(",") if f.strip()]
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
        return redirect("column_config_view", block_name=self.block.name)
