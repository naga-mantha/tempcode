from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView

from django_bi.blocks.models.block import Block
from django_bi.blocks.models.block_column_config import BlockColumnConfig
from django_bi.blocks.services.column_config import get_model_fields_for_column_config
from django_bi.blocks.registry import block_registry


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
    visibility = forms.ChoiceField(required=False, choices=[
        ("private", "Private"), ("public", "Public")
    ])

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
        # Fallback: if no fields are visible due to strict permissions, show full list
        # (table rendering still masks unreadable fields at runtime)
        if not self.fields_metadata:
            try:
                self.fields_metadata = get_model_fields_for_column_config(self.model, None, max_depth=max_depth)
            except Exception:
                self.fields_metadata = []
        return super().dispatch(request, block_name, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Q, Case, When, IntegerField
        # Visible to user (including admins): own private + all public
        qs = BlockColumnConfig.objects.filter(block=self.block).filter(
            Q(user=self.user) | Q(visibility=BlockColumnConfig.VISIBILITY_PUBLIC)
        )
        configs = qs.annotate(
            _vis_order=Case(
                When(visibility=BlockColumnConfig.VISIBILITY_PRIVATE, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by("_vis_order", "name")
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
        visibility = (form.cleaned_data.get("visibility") or "private").lower()
        if not self.request.user.is_staff:
            visibility = "private"  # Non-admins can only create private

        if action == "create":
            field_list = form.cleaned_data.get("fields") or []
            # If editing an existing config (via config_id), update with permission checks
            if config_id:
                cfg = BlockColumnConfig.objects.filter(id=config_id, block=self.block).first()
                if not cfg:
                    return redirect("blocks:column_config_view", block_name=self.block.code)
                if not self.request.user.is_staff and (cfg.visibility != BlockColumnConfig.VISIBILITY_PRIVATE or cfg.user_id != self.user.id):
                    # Non-admins cannot edit public or others' privates
                    return redirect("blocks:column_config_view", block_name=self.block.code)
                # Admins may edit any; update fields and (optionally) visibility
                cfg.fields = field_list
                if self.request.user.is_staff and visibility in dict(BlockColumnConfig.VISIBILITY_CHOICES):
                    cfg.visibility = visibility
                cfg.save()
            else:
                # Create new (admin may choose visibility; non-admin forced private)
                BlockColumnConfig.objects.create(
                    block=self.block, user=self.user, name=name, fields=field_list, visibility=visibility
                )
        elif action == "delete" and config_id:
            # Allow delete if owner of a private config, or admin deleting a public config
            cfg = BlockColumnConfig.objects.filter(id=config_id, block=self.block).first()
            if not cfg:
                return redirect("blocks:column_config_view", block_name=self.block.code)
            can_delete = (
                (cfg.visibility == BlockColumnConfig.VISIBILITY_PRIVATE and cfg.user_id == self.user.id)
                or (self.request.user.is_staff and cfg.visibility == BlockColumnConfig.VISIBILITY_PUBLIC)
            )
            if can_delete:
                cfg.delete()
        elif action == "set_default" and config_id:
            cfg = BlockColumnConfig.objects.filter(id=config_id, block=self.block).first()
            if not cfg:
                return redirect("blocks:column_config_view", block_name=self.block.code)
            # Admin can set default on any PUBLIC config (global fallback), or on their own private
            if self.request.user.is_staff and cfg.visibility == BlockColumnConfig.VISIBILITY_PUBLIC:
                # Demote other public defaults for this block
                BlockColumnConfig.objects.filter(block=self.block, visibility=BlockColumnConfig.VISIBILITY_PUBLIC).exclude(id=cfg.id).update(is_default=False)
                cfg.is_default = True
                cfg.save()
            elif cfg.user_id == self.user.id and cfg.visibility == BlockColumnConfig.VISIBILITY_PRIVATE:
                cfg.is_default = True
                cfg.save()
        return redirect("blocks:column_config_view", block_name=self.block.code)
