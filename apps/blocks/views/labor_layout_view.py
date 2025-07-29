from django.shortcuts import render
from apps.blocks.models.labor_page_layout import LaborPageLayout
from apps.blocks.blocks.registry import BLOCK_REGISTRY

def labor_page(request):
    layout = LaborPageLayout.objects.filter(user=request.user, is_default=True).first()
    layout_items = layout.layout_json if layout else [{"id": "labor_form", "layout": "row"}, {"id": "labor_table", "layout": "row"}]

    rendered_blocks = []
    for item in layout_items:
        block = BLOCK_REGISTRY.get(item["id"])
        if block and block.has_permission(request):
            rendered_blocks.append({
                "template": block.template_name,
                "layout": item.get("layout", "row"),
                "context": block.get_context(request),
            })

    return render(request, "layouts/labor_layout.html", {"rendered_blocks": rendered_blocks})
