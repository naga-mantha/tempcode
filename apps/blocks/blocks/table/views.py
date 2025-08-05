import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from apps.blocks.registry import get_block
from apps.workflow.permissions import can_write_field_state
from django.shortcuts import render, redirect
from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from django.http import Http404
from apps.blocks.registry import BLOCK_REGISTRY
from apps.blocks.helpers.field_rules import get_flat_fields
@csrf_exempt
@require_POST
@login_required
def inline_edit(request, block_name):
    try:
        data = json.loads(request.body)
        obj_id = data.get("id")
        field = data.get("field")
        value = data.get("value")

        block = get_block(block_name)
        if not block:
            return JsonResponse({"success": False, "error": "Invalid block"})

        model = block["model"]
        instance = model.objects.get(id=obj_id)

        if not can_write_field_state(request.user, model, field, instance):
            return JsonResponse({"success": False, "error": "Permission denied"})

        setattr(instance, field, value)
        instance.save()

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def column_config_view(request, block_name):
    block = Block.objects.get(name=block_name)
    user = request.user
    configs = BlockColumnConfig.objects.filter(block=block, user=user)

    block_instance = get_block(block_name)
    if not block_instance:
        raise Http404(f"Block '{block_name}' not found.")
    model = block_instance.get_model()

    fields_metadata = get_flat_fields(model, user)

    if request.method == "POST":
        action = request.POST.get("action")
        config_id = request.POST.get("config_id")
        name = request.POST.get("name")
        fields = request.POST.getlist("fields")

        if action == "create":
            fields = request.POST.get("fields", "")
            field_list = [f.strip() for f in fields.split(",") if f.strip()]

            existing = BlockColumnConfig.objects.filter(block=block, user=user, name=name).first()
            if existing:
                existing.fields = field_list
                existing.save()
            else:
                BlockColumnConfig.objects.create(
                    block=block, user=user, name=name, fields=field_list
                )

        elif action == "delete":
            BlockColumnConfig.objects.get(id=config_id, user=user, block=block).delete()

        elif action == "set_default":
            config = BlockColumnConfig.objects.get(id=config_id, user=user, block=block)
            config.is_default = True
            config.save()

        return redirect("column_config_view", block_name=block_name)

    return render(request, "blocks/table/column_config_view.html", {
        "block": block,
        "configs": configs,
        "fields_metadata": fields_metadata,
    })

@login_required
def filter_config_view(request, block_name):
    block = Block.objects.get(name=block_name)
    user = request.user
    configs = BlockFilterConfig.objects.filter(block=block, user=user)

    if request.method == "POST":
        action = request.POST.get("action")
        config_id = request.POST.get("config_id")
        name = request.POST.get("name")
        values_raw = request.POST.get("values", "{}")

        try:
            values = json.loads(values_raw)
        except json.JSONDecodeError:
            values = {}

        if action == "create":
            values_raw = request.POST.get("values", "{}")
            try:
                values = json.loads(values_raw)
            except json.JSONDecodeError:
                values = {}  # Optional: flash an error message instead
            BlockFilterConfig.objects.create(block=block, user=user, name=name, values=values)
        elif action == "delete":
            BlockFilterConfig.objects.get(id=config_id, user=user, block=block).delete()
        elif action == "set_default":
            config = BlockFilterConfig.objects.get(id=config_id, user=user, block=block)
            config.is_default = True
            config.save()

        return redirect("filter_config_view", block_name=block_name)

    return render(request, "blocks/table/filter_config_view.html", {
        "block": block,
        "configs": configs
    })

def render_table_block(request, block_name):
    block = BLOCK_REGISTRY.get(block_name)
    if not block:
        raise Http404(f"Block '{block_name}' not found in registry.")
    return block.render(request)