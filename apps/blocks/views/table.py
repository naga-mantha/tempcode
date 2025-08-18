from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from apps.blocks.registry import block_registry
from apps.blocks.models.block import Block
from apps.blocks.models.block_filter_config import BlockFilterConfig


def render_table_block(request, block_name):
    block = block_registry.get(block_name)
    if not block:
        raise Http404(f"Block '{block_name}' not found in registry.")
    return block.render(request)


def _get_db_block_or_404(block_name):
    # Use 'code' as the stable identifier
    return get_object_or_404(Block, code=block_name)


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
