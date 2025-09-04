from django.http import Http404
from django.shortcuts import render

from apps.blocks.registry import block_registry


def render_pivot_block(request, block_name):
    block = block_registry.get(block_name)
    if not block:
        raise Http404(f"Block '{block_name}' not found in registry.")
    if request.GET.get("embedded"):
        return block.render(request)
    config = block.get_config(request)
    data = block.get_data(request)
    context = {}
    if isinstance(config, dict):
        context.update(config)
    if isinstance(data, dict):
        context.update(data)
    return render(request, "blocks/pivot/pivot_block_page.html", context)
