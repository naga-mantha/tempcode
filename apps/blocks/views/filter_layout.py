from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
import json as pyjson

from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_layout import BlockFilterLayout
from apps.blocks.models.config_templates import BlockFilterLayoutTemplate
from apps.blocks.registry import block_registry
from apps.blocks.block_types.table.filter_utils import FilterResolutionMixin


class FilterLayoutForm(forms.Form):
    layout = forms.CharField(widget=forms.Textarea(attrs={"rows": 18, "class": "form-control"}), required=False)
    action = forms.ChoiceField(choices=(("save", "save"), ("clear", "clear"), ("load_default", "load_default")))


class FilterLayoutView(LoginRequiredMixin, View):
    template_name = "blocks/filter_layout_view.html"

    def get(self, request, block_name):
        block = get_object_or_404(Block, code=block_name)
        user_layout = BlockFilterLayout.objects.filter(block=block, user=request.user).first()
        admin_layout = BlockFilterLayoutTemplate.objects.filter(block=block).first()
        layout_obj = {}
        if user_layout and isinstance(user_layout.layout, dict):
            layout_obj = user_layout.layout
        elif admin_layout and isinstance(admin_layout.layout, dict):
            layout_obj = admin_layout.layout
        # Build available fields from the block filter schema
        block_impl = block_registry.get(block_name)
        if not block_impl:
            raise Http404("Invalid block")
        try:
            raw_schema = block_impl.get_filter_schema(request)
        except TypeError:
            raw_schema = block_impl.get_filter_schema(request.user)
        schema = FilterResolutionMixin._resolve_filter_schema(raw_schema, request.user)
        available = []
        for k, cfg in (schema or {}).items():
            available.append({
                "key": str(k),
                "label": str(cfg.get("label", k)),
                "type": str(cfg.get("type", "text")),
            })
        # Compute display title preferring admin name; avoid generic 'content'
        disp = block.name or block.code
        try:
            if not disp or str(disp).strip().lower() == 'content':
                disp = (block.code or '').replace('_', ' ').title()
        except Exception:
            disp = block.code
        ctx = {
            "block": block,
            "block_name": block_name,
            "layout_json": pyjson.dumps(layout_obj or {}),
            "available_fields": available,
            "display_title": disp,
            "admin_mode": False,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, block_name):
        block = get_object_or_404(Block, code=block_name)
        action = request.POST.get("action")
        if action == "load_default":
            # No change persisted; just re-render with admin default and full context
            admin_layout = BlockFilterLayoutTemplate.objects.filter(block=block).first()
            layout_obj = admin_layout.layout if (admin_layout and isinstance(admin_layout.layout, dict)) else {}
            # Rebuild available fields (same as GET)
            block_impl = block_registry.get(block_name)
            if not block_impl:
                raise Http404("Invalid block")
            try:
                raw_schema = block_impl.get_filter_schema(request)
            except TypeError:
                raw_schema = block_impl.get_filter_schema(request.user)
            schema = FilterResolutionMixin._resolve_filter_schema(raw_schema, request.user)
            available = []
            for k, cfg in (schema or {}).items():
                available.append({
                    "key": str(k),
                    "label": str(cfg.get("label", k)),
                    "type": str(cfg.get("type", "text")),
                })
            disp = block.name or block.code
            try:
                if not disp or str(disp).strip().lower() == 'content':
                    disp = (block.code or '').replace('_', ' ').title()
            except Exception:
                disp = block.code
            ctx = {
                "block": block,
                "block_name": block_name,
                "layout_json": pyjson.dumps(layout_obj or {}),
                "available_fields": available,
                "display_title": disp,
                "admin_mode": False,
            }
            return render(request, self.template_name, ctx)
        # save
        text = request.POST.get("layout") or "{}"
        try:
            parsed = pyjson.loads(text)
        except Exception:
            parsed = {}
        obj, _ = BlockFilterLayout.objects.update_or_create(block=block, user=request.user, defaults={"layout": parsed})
        return redirect("filter_layout_view", block_name=block_name)


class AdminFilterLayoutView(LoginRequiredMixin, View):
    template_name = "blocks/filter_layout_view.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def _build_context(self, request, block_name, layout_obj):
        block = get_object_or_404(Block, code=block_name)
        # Compute title
        disp = block.name or block.code
        try:
            if not disp or str(disp).strip().lower() == 'content':
                disp = (block.code or '').replace('_', ' ').title()
        except Exception:
            disp = block.code
        # Available fields from schema
        block_impl = block_registry.get(block_name)
        if not block_impl:
            raise Http404("Invalid block")
        try:
            raw_schema = block_impl.get_filter_schema(request)
        except TypeError:
            raw_schema = block_impl.get_filter_schema(request.user)
        schema = FilterResolutionMixin._resolve_filter_schema(raw_schema, request.user)
        available = []
        for k, cfg in (schema or {}).items():
            available.append({
                "key": str(k),
                "label": str(cfg.get("label", k)),
                "type": str(cfg.get("type", "text")),
            })
        return {
            "block": block,
            "block_name": block_name,
            "layout_json": pyjson.dumps(layout_obj or {}),
            "available_fields": available,
            "display_title": disp,
            "admin_mode": True,
        }

    def get(self, request, block_name):
        block = get_object_or_404(Block, code=block_name)
        tpl = BlockFilterLayoutTemplate.objects.filter(block=block).first()
        layout_obj = tpl.layout if (tpl and isinstance(tpl.layout, dict)) else {}
        ctx = self._build_context(request, block_name, layout_obj)
        return render(request, self.template_name, ctx)

    def post(self, request, block_name):
        block = get_object_or_404(Block, code=block_name)
        action = request.POST.get("action")
        if action == "load_default":
            # Admin default page: load existing template again
            tpl = BlockFilterLayoutTemplate.objects.filter(block=block).first()
            layout_obj = tpl.layout if (tpl and isinstance(tpl.layout, dict)) else {}
            ctx = self._build_context(request, block_name, layout_obj)
            return render(request, self.template_name, ctx)
        # save
        text = request.POST.get("layout") or "{}"
        try:
            parsed = pyjson.loads(text)
        except Exception:
            parsed = {}
        tpl, _ = BlockFilterLayoutTemplate.objects.update_or_create(block=block, defaults={"layout": parsed})
        return redirect("admin_filter_layout_view", block_name=block_name)
