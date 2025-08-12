import json
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST, csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from apps.workflow.permissions import can_write_field_state
from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.helpers.column_config import get_model_fields_for_column_config
from .filter_utils import FilterResolutionMixin


@csrf_exempt
@require_POST
@login_required
def inline_edit(request, block_name):
    try:
        data = json.loads(request.body)
        obj_id = data.get("id")
        field = data.get("field")
        value = data.get("value")

        block = block_registry.get(block_name)
        if not block:
            return JsonResponse({"success": False, "error": "Invalid block"})

        model = block.get_model()
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

    block_instance = block_registry.get(block_name)
    if not block_instance:
        raise Http404(f"Block '{block_name}' not found.")
    model = block_instance.get_model()

    fields_metadata = get_model_fields_for_column_config(model, user)

    if request.method == "POST":
        action = request.POST.get("action")
        config_id = request.POST.get("config_id")
        name = request.POST.get("name")

        if action == "create":
            fields = request.POST.get("fields", "")
            field_list = [f.strip() for f in fields.split(",") if f.strip()]

            existing = BlockColumnConfig.objects.filter(block=block, user=user, name=name).first()
            if existing:
                existing.fields = field_list
                existing.save()
            else:
                BlockColumnConfig.objects.create(block=block, user=user, name=name, fields=field_list)

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

def render_table_block(request, block_name):
    block = block_registry.get(block_name)
    if not block:
        raise Http404(f"Block '{block_name}' not found in registry.")
    return block.render(request)



def _get_db_block_or_404(block_name):
    # If your Block model uses slug instead of name, switch to slug=block_name
    return get_object_or_404(Block, name=block_name)

@login_required
def filter_config_view(request, block_name):
    block_impl = block_registry.get(block_name)  # registry object (Python)
    if not block_impl:
        raise Http404("Invalid block")

    db_block = _get_db_block_or_404(block_name)  # DB row

    user_filters = BlockFilterConfig.objects.filter(
        block=db_block, user=request.user
    ).order_by("-is_default", "name")

    editing = None
    if request.method == "GET":
        edit_id = request.GET.get("id")
        if edit_id:
            editing = get_object_or_404(
                BlockFilterConfig, id=edit_id, block=db_block, user=request.user
            )

    raw_schema = block_impl.get_filter_schema(request)
    filter_schema = FilterResolutionMixin._resolve_filter_schema(raw_schema, request.user)

    if request.method == "POST":
        edit_id = request.POST.get("id")
        name = (request.POST.get("name") or "").strip()
        is_default = bool(request.POST.get("is_default"))
        if not name:
            messages.error(request, "Please provide a name.")
            return redirect("table_filter_config", block_name=block_name)

        values = FilterResolutionMixin._collect_filters(request.POST, filter_schema, base={})

        if edit_id:
            cfg = get_object_or_404(
                BlockFilterConfig, id=edit_id, block=db_block, user=request.user
            )
        else:
            cfg = BlockFilterConfig(block=db_block, user=request.user)  # ← use DB block

        cfg.name = name
        cfg.values = values
        cfg.is_default = is_default
        cfg.save()
        #
        # if is_default:
        #     BlockFilterConfig.objects.filter(
        #         block=db_block, user=request.user
        #     ).exclude(id=cfg.id).update(is_default=False)

        messages.success(request, "Filter saved.")
        return redirect(f"{request.path}?id={cfg.id}")

    initial_values = editing.values if editing else {}
    route_block_name = getattr(block_impl, "block_name", block_name)  # registry key you used in __init__

    return render(request, "blocks/table/filter_config_view.html", {
        "block": block_impl,
        "route_block_name": route_block_name,
        "user_filters": user_filters,
        "editing": editing,
        "filter_schema": filter_schema,
        "initial_values": initial_values,
    })

@login_required
def filter_delete_view(request, block_name, config_id):
    block_impl = block_registry.get(block_name)
    if not block_impl:
        raise Http404("Invalid block")
    db_block = _get_db_block_or_404(block_name)

    cfg = get_object_or_404(
        BlockFilterConfig, id=config_id, block=db_block, user=request.user
    )
    if request.method == "POST":
        cfg.delete()
        messages.success(request, "Filter deleted.")
        return redirect("table_filter_config", block_name=block_name)
    raise Http404()
