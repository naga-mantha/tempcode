from __future__ import annotations

from typing import Any, Dict, List
from django.db import models

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string

from apps.accounts.models.custom_user import CustomUser
from apps.layout.models import Layout, LayoutBlock
from apps.blocks.models.block import Block

from apps_v2.blocks.register import load_specs
from apps_v2.blocks.registry import get_registry
from apps_v2.blocks.controller import BlockController
from apps_v2.policy.service import PolicyService
from apps_v2.blocks.services.model_table import prune_filter_schema
from apps_v2.blocks.registry import get_registry
from apps_v2.blocks.register import load_specs


def _group_layouts_for_sidebar(user) -> Dict[str, List[Layout]]:
    private_qs = Layout.objects.filter(user=user, visibility=Layout.VISIBILITY_PRIVATE).order_by("name")
    public_qs = Layout.objects.filter(visibility=Layout.VISIBILITY_PUBLIC).order_by("name")
    return {
        "private_layouts": list(private_qs),
        "public_layouts": list(public_qs),
    }


@login_required
def layout_list(request: HttpRequest) -> HttpResponse:
    # Delegate to v1: keep a single, stable layout UX
    from django.shortcuts import redirect as _redirect
    return _redirect("layout_list")


@login_required
def layout_detail(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    # Delegate to v1 detail page
    from django.shortcuts import redirect as _redirect
    return _redirect("layout_detail", username=username, slug=slug)

def ping(_request: HttpRequest) -> HttpResponse:
    return HttpResponse("layouts v2 ok", content_type="text/plain")


@login_required
def layout_create(request: HttpRequest) -> HttpResponse:
    from django.shortcuts import redirect as _redirect
    return _redirect("layout_create")


@login_required
def rename_layout_filter_config(request: HttpRequest, username: str, slug: str, config_id: int) -> HttpResponse:
    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("layout_v2:layout_manage_filters_v2", username=username, slug=slug)
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    from apps.layout.models import LayoutFilterConfig
    try:
        obj = LayoutFilterConfig.objects.get(pk=config_id, layout=layout, user=request.user)
    except LayoutFilterConfig.DoesNotExist:
        return HttpResponse(status=404)
    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        return HttpResponse(status=400)
    obj.name = new_name
    obj.save(update_fields=["name"])
    return _render_saved_filters_partial(request, layout)


@login_required
def delete_layout_filter_config(request: HttpRequest, username: str, slug: str, config_id: int) -> HttpResponse:
    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("layout_v2:layout_manage_filters_v2", username=username, slug=slug)
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    from apps.layout.models import LayoutFilterConfig
    try:
        obj = LayoutFilterConfig.objects.get(pk=config_id, layout=layout, user=request.user)
    except LayoutFilterConfig.DoesNotExist:
        return HttpResponse(status=404)
    obj.delete()
    return _render_saved_filters_partial(request, layout)


@login_required
def make_default_layout_filter_config(request: HttpRequest, username: str, slug: str, config_id: int) -> HttpResponse:
    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("layout_v2:layout_manage_filters_v2", username=username, slug=slug)
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    from apps.layout.models import LayoutFilterConfig
    try:
        obj = LayoutFilterConfig.objects.get(pk=config_id, layout=layout, user=request.user)
    except LayoutFilterConfig.DoesNotExist:
        return HttpResponse(status=404)
    obj.is_default = True
    obj.save(update_fields=["is_default"])
    return _render_saved_filters_partial(request, layout)


@login_required
def duplicate_layout_filter_config(request: HttpRequest, username: str, slug: str, config_id: int) -> HttpResponse:
    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("layout_v2:layout_manage_filters_v2", username=username, slug=slug)
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    from apps.layout.models import LayoutFilterConfig
    try:
        obj = LayoutFilterConfig.objects.get(pk=config_id, layout=layout)
    except LayoutFilterConfig.DoesNotExist:
        return HttpResponse(status=404)
    new_obj = LayoutFilterConfig(
        layout=layout,
        user=request.user,
        name=f"{obj.name} (copy)",
        values=dict(obj.values or {}),
        visibility=LayoutFilterConfig.VISIBILITY_PRIVATE,
        is_default=False,
    )
    new_obj.save()
    return _render_saved_filters_partial(request, layout)


# ---------- Grid/Block management (V2) ----------

@login_required
def layout_design(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    if not (request.user.is_staff or request.user.id == layout.user_id):
        raise Http404()
    load_specs()
    reg = get_registry()
    # Build block HTML and metadata
    policy = PolicyService()
    blocks = []
    blocks_meta = []
    for lb in LayoutBlock.objects.filter(layout=layout).order_by("position", "id"):
        spec = reg.get(lb.block.code) if lb and lb.block else None
        html = "<div class=\"text-muted small\">Unknown block</div>"
        if spec:
            ctx = BlockController(spec, policy).build_context(request, dom_ns=f"lb{lb.id}")
            template = spec.template
            if spec.kind == "table":
                template = "v2/blocks/table/table_card.html"
            elif spec.kind == "pivot":
                template = "v2/blocks/pivot/pivot_card.html"
            html = render_to_string(template, ctx, request=request)
        blocks.append({
            "id": lb.id,
            "x": lb.x or 0,
            "y": lb.y or 0,
            "w": lb.w or 4,
            "h": lb.h or 2,
            "html": html,
            "title": lb.title or (lb.block.name if lb.block else ""),
            "code": lb.block.code if lb and lb.block else "",
            "note": lb.note or "",
        })
        blocks_meta.append({
            "id": lb.id,
            "x": lb.x or 0,
            "y": lb.y or 0,
            "w": lb.w or 4,
            "h": lb.h or 2,
            "title": lb.title or (lb.block.name if lb.block else ""),
            "note": lb.note or "",
        })
    # Available specs (V2)
    available_specs = []
    try:
        for code, spec in reg.items():
            available_specs.append({"id": code, "name": getattr(spec, "name", code), "kind": getattr(spec, "kind", "")})
        available_specs.sort(key=lambda x: (x.get("kind") or "", x.get("name") or ""))
    except Exception:
        available_specs = []
    ctx = {
        "layout": layout,
        "blocks": blocks,
        "blocks_meta": blocks_meta,
        "available_specs": available_specs,
    }
    return render(request, "v2/layout/layout_design.html", ctx)


@login_required
def layout_grid_update_v2(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    if request.method != "POST":
        raise Http404()
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    if not (request.user.is_staff or request.user.id == layout.user_id):
        raise Http404()
    try:
        import json as _json
        payload = _json.loads(request.body.decode("utf-8") or "{}")
        items = payload.get("items") or []
    except Exception:
        items = []
    id_to_item = {}
    order = []
    for it in items:
        try:
            lb_id = int(it.get("id"))
            id_to_item[lb_id] = it
            order.append(lb_id)
        except Exception:
            continue
    # Update grid attrs
    qs = LayoutBlock.objects.filter(layout=layout, id__in=id_to_item.keys())
    for lb in qs:
        it = id_to_item.get(lb.id) or {}
        try:
            lb.x = int(it.get("x", lb.x))
            lb.y = int(it.get("y", lb.y))
            lb.w = int(it.get("w", lb.w))
            lb.h = int(it.get("h", lb.h))
        except Exception:
            pass
        lb.save(update_fields=["x", "y", "w", "h"])
    # Update positions by current order
    for idx, lb_id in enumerate(order):
        try:
            LayoutBlock.objects.filter(layout=layout, id=lb_id).update(position=idx)
        except Exception:
            continue
    return HttpResponse(status=204)


@login_required
def layout_block_add_v2(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    if request.method != "POST":
        raise Http404()
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    if not (request.user.is_staff or request.user.id == layout.user_id):
        raise Http404()
    spec_id = (request.POST.get("spec_id") or "").strip()
    if not spec_id:
        return HttpResponse(status=400)
    from apps_v2.blocks.configs import get_block_for_spec
    block = get_block_for_spec(spec_id)
    # Place at next position and default size, append to bottom of current grid
    next_pos = (LayoutBlock.objects.filter(layout=layout).aggregate(m=models.Max("position")).get("m") or 0) + 1
    existing = list(LayoutBlock.objects.filter(layout=layout).values("x", "y", "h"))
    try:
        bottom_y = max(int((e.get("y") or 0)) + int((e.get("h") or 1)) for e in existing) if existing else 0
    except Exception:
        bottom_y = 0
    lb = LayoutBlock.objects.create(layout=layout, block=block, position=next_pos, x=0, y=bottom_y, w=4, h=2)
    from django.urls import reverse
    from django.shortcuts import redirect
    return redirect("layout_v2:layout_design_v2", username=layout.user.username, slug=layout.slug)


@login_required
def layout_block_delete_v2(request: HttpRequest, username: str, slug: str, lb_id: int) -> HttpResponse:
    if request.method != "POST":
        raise Http404()
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    if not (request.user.is_staff or request.user.id == layout.user_id):
        raise Http404()
    try:
        LayoutBlock.objects.get(layout=layout, id=lb_id).delete()
    except LayoutBlock.DoesNotExist:
        return HttpResponse(status=404)
    return HttpResponse(status=204)


@login_required
def layout_block_render_v2(request: HttpRequest, username: str, slug: str, lb_id: int) -> HttpResponse:
    # Render a single block (HTML fragment) for dynamic refresh in the designer
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    lb = get_object_or_404(LayoutBlock, layout=layout, id=lb_id)
    load_specs()
    reg = get_registry()
    policy = PolicyService()
    spec = reg.get(lb.block.code) if lb and lb.block else None
    html = "<div class=\"text-muted small\">Unknown block</div>"
    if spec:
        ctx = BlockController(spec, policy).build_context(request, dom_ns=f"lb{lb.id}")
        template = spec.template
        if spec.kind == "table":
            template = "v2/blocks/table/table_card.html"
        elif spec.kind == "pivot":
            template = "v2/blocks/pivot/pivot_card.html"
        html = render_to_string(template, ctx, request=request)
    import json as _json
    return HttpResponse(_json.dumps({"html": html}), content_type="application/json")


@login_required
def layout_block_update_v2(request: HttpRequest, username: str, slug: str, lb_id: int) -> HttpResponse:
    if request.method != "POST":
        raise Http404()
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    if not (request.user.is_staff or request.user.id == layout.user_id):
        raise Http404()
    lb = get_object_or_404(LayoutBlock, layout=layout, id=lb_id)
    title = (request.POST.get("title") or "").strip()
    note = (request.POST.get("note") or "").strip()
    try:
        import json as _json
        settings = _json.loads(request.POST.get("settings_json") or "null")
    except Exception:
        settings = None
    # Optional defaults for table/pivot
    pref_cols = (request.POST.get("preferred_column_config_name") or "").strip()
    pref_filt = (request.POST.get("preferred_filter_name") or "").strip()
    pref_pivot = (request.POST.get("preferred_pivot_name") or "").strip()
    lb.title = title
    lb.note = note
    if isinstance(settings, dict):
        lb.settings = settings
    if pref_cols:
        lb.preferred_column_config_name = pref_cols
    if pref_filt:
        lb.preferred_filter_name = pref_filt
    if pref_pivot:
        try:
            tmp = dict(lb.settings or {})
            tmp["preferred_pivot_name"] = pref_pivot
            lb.settings = tmp
        except Exception:
            pass
    lb.save(update_fields=["title", "note", "settings", "preferred_column_config_name", "preferred_filter_name"])
    return HttpResponse(status=204)


@login_required
def layout_block_configs_v2(request: HttpRequest, username: str, slug: str, lb_id: int) -> HttpResponse:
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    lb = get_object_or_404(LayoutBlock, layout=layout, id=lb_id)
    from apps_v2.blocks.configs import (
        list_table_configs,
        list_filter_configs,
        list_pivot_configs,
    )
    block = lb.block
    spec_id = getattr(block, "code", "")
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    kind = getattr(spec, "kind", "") if spec else ""
    data = {
        "kind": kind,
        "columns": [],
        "filters": [],
        "pivots": [],
        "selected": {
            "column": getattr(lb, "preferred_column_config_name", "") or "",
            "filter": getattr(lb, "preferred_filter_name", "") or "",
            "pivot": (lb.settings or {}).get("preferred_pivot_name", "") if isinstance(lb.settings, dict) else "",
        },
    }
    try:
        tbl = [c.name for c in list_table_configs(block, request.user)]
    except Exception:
        tbl = []
    try:
        fil = [c.name for c in list_filter_configs(block, request.user)]
    except Exception:
        fil = []
    try:
        piv = [c.name for c in list_pivot_configs(block, request.user)]
    except Exception:
        piv = []
    if kind == "table":
        data["columns"] = tbl
        data["filters"] = fil
    elif kind == "pivot":
        data["filters"] = fil
        data["pivots"] = piv
    else:
        data["filters"] = fil
    import json as _json
    return HttpResponse(_json.dumps(data), content_type="application/json")


@login_required
def manage_layout_filters(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    from apps.layout.models import LayoutFilterConfig
    from django.db.models import Q, Case, When, IntegerField
    qs = LayoutFilterConfig.objects.filter(layout=layout).filter(Q(user=request.user) | Q(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC))
    qs = qs.annotate(
        _vis_order=Case(
            When(visibility=LayoutFilterConfig.VISIBILITY_PRIVATE, then=0),
            default=1,
            output_field=IntegerField()
        )
    ).order_by("_vis_order", "name")
    filter_configs = list(qs)
    ctx: Dict[str, Any] = {"layout": layout, "filter_configs": filter_configs}
    return render(request, "v2/layout/filter/manage.html", ctx)


def _render_saved_filters_partial(request: HttpRequest, layout: Layout) -> HttpResponse:
    from django.template.loader import render_to_string
    from apps.layout.models import LayoutFilterConfig
    from django.db.models import Q, Case, When, IntegerField
    qs = LayoutFilterConfig.objects.filter(layout=layout).filter(Q(user=request.user) | Q(visibility=LayoutFilterConfig.VISIBILITY_PUBLIC))
    qs = qs.annotate(
        _vis_order=Case(
            When(visibility=LayoutFilterConfig.VISIBILITY_PRIVATE, then=0),
            default=1,
            output_field=IntegerField()
        )
    ).order_by("_vis_order", "name")
    html = render_to_string("v2/layout/filter/_saved_filters.html", {"layout": layout, "filter_configs": list(qs), "request": request}, request=request)
    return HttpResponse(html)


@login_required
def save_layout_filter_config(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    """Save a LayoutFilterConfig selected from the offcanvas panel."""
    if request.method != "POST":
        raise Http404()
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    if not (request.user.is_staff or request.user.id == layout.user_id):
        raise Http404()
    from apps.layout.models import LayoutFilterConfig
    name = (request.POST.get("name") or "").strip() or "Default"
    visibility = (request.POST.get("visibility") or LayoutFilterConfig.VISIBILITY_PRIVATE).strip()
    is_default = request.POST.get("is_default") in {"on", "true", "1"}
    try:
        import json as _json
        values = _json.loads(request.POST.get("values_json") or "{}")
        if not isinstance(values, dict):
            values = {}
    except Exception:
        values = {}
    if visibility not in {LayoutFilterConfig.VISIBILITY_PRIVATE, LayoutFilterConfig.VISIBILITY_PUBLIC}:
        visibility = LayoutFilterConfig.VISIBILITY_PRIVATE

    obj, _ = LayoutFilterConfig.objects.update_or_create(
        layout=layout, user=request.user, name=name,
        defaults={
            "values": values,
            "visibility": visibility,
            "is_default": bool(is_default),
        },
    )
    from django.urls import reverse
    from django.shortcuts import redirect
    url = reverse("layout_v2:layout_detail_v2", kwargs={"username": layout.user.username, "slug": layout.slug})
    if "?" in url:
        url = url + "&layout_filter_config_id=" + str(obj.id)
    else:
        url = url + "?layout_filter_config_id=" + str(obj.id)
    return redirect(url)


@login_required
def layout_edit(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    from django.shortcuts import redirect as _redirect
    return _redirect("layout_edit", username=username, slug=slug)
