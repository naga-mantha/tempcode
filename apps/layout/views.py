from __future__ import annotations

from typing import Any, Dict, List

from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from apps.accounts.models.custom_user import CustomUser
from apps.blocks.controller import BlockController
from apps.blocks.models.block import Block
from apps.blocks.register import load_specs
from apps.blocks.registry import get_registry
from apps.blocks.services.model_table import prune_filter_schema
from apps.layout.models import Layout, LayoutBlock
from apps.policy.service import PolicyService


def _group_layouts_for_sidebar(user) -> Dict[str, List[Layout]]:
    private_qs = Layout.objects.filter(user=user, visibility=Layout.VISIBILITY_PRIVATE).order_by("name")
    public_qs = Layout.objects.filter(visibility=Layout.VISIBILITY_PUBLIC).order_by("name")
    return {
        "private_layouts": list(private_qs),
        "public_layouts": list(public_qs),
    }


def _serialize_layout_block(
    lb: LayoutBlock,
    request: HttpRequest,
    registry=None,
    policy: PolicyService | None = None,
) -> Dict[str, Any]:
    """Return a serializable dict (including rendered HTML) for a layout block."""

    reg = registry or get_registry()
    policy = policy or PolicyService()
    block_spec = None
    if lb and lb.block:
        try:
            block_spec = reg.get(lb.block.code)
        except Exception:
            block_spec = None

    pref_filter_name = getattr(lb, "preferred_filter_name", "") or ""
    pref_setting_name = getattr(lb, "preferred_setting_name", "") or ""
    pref_pivot_name = ""
    try:
        if isinstance(getattr(lb, "settings", None), dict):
            pref_pivot_name = lb.settings.get("preferred_pivot_name", "") or ""
    except Exception:
        pref_pivot_name = ""

    block_kind = getattr(block_spec, "kind", "") if block_spec else ""
    ctx: Dict[str, Any] | None = None
    html = "<div class=\"text-muted small\">Unknown block</div>"
    if block_spec is not None:
        try:
            ctx = BlockController(block_spec, policy).build_context(
                request,
                dom_ns=f"lb{lb.id}",
                preferred_filter_name=pref_filter_name,
                preferred_setting_name=pref_setting_name,
                preferred_pivot_name=pref_pivot_name,
            )
            template = getattr(block_spec, "template", None) or ""
            if getattr(block_spec, "kind", "") == "table":
                template = "blocks/table/table_card.html"
            elif getattr(block_spec, "kind", "") == "pivot":
                template = "blocks/pivot/pivot_card.html"
            html = render_to_string(template, ctx, request=request)
        except Exception:
            html = "<div class=\"text-muted small\">Unable to render block</div>"

    dom_id = ""
    if isinstance(ctx, dict):
        dom_id = str(ctx.get("dom_id") or "")

    return {
        "id": lb.id,
        "x": lb.x or 0,
        "y": lb.y or 0,
        "w": lb.w or 4,
        "h": lb.h or 2,
        "title": lb.title or (lb.block.name if lb and lb.block else ""),
        "code": lb.block.code if lb and lb.block else "",
        "note": lb.note or "",
        "is_spacer": bool(getattr(lb, "is_spacer", False)),
        "preferred_filter_name": pref_filter_name,
        "preferred_setting_name": pref_setting_name,
        "preferred_pivot_name": pref_pivot_name,
        "dom_id": dom_id,
        "kind": block_kind,
        "html": html,
    }


@login_required
def layout_list(request: HttpRequest) -> HttpResponse:
    ctx: Dict[str, Any] = {
        **_group_layouts_for_sidebar(request.user),
    }
    return render(request, "layout/layout_list.html", ctx)


@login_required
def layout_detail(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)

    # Layout-level saved filters (private/public)
    from django.db.models import Q, Case, When, IntegerField
    cfg_qs = layout.filter_configs.filter(Q(user=request.user) | Q(visibility=layout.filter_configs.model.VISIBILITY_PUBLIC))
    cfg_qs = cfg_qs.annotate(
        _vis_order=Case(
            When(visibility=layout.filter_configs.model.VISIBILITY_PRIVATE, then=0),
            default=1,
            output_field=IntegerField(),
        )
    ).order_by("_vis_order", "name")
    layout_filter_configs = list(cfg_qs)
    # Choose active by param or default
    cfg_id = request.GET.get("layout_filter_config_id")
    try:
        cfg_id_int = int(cfg_id) if cfg_id else None
    except ValueError:
        cfg_id_int = None
    active_layout_cfg = None
    if cfg_id_int:
        active_layout_cfg = next((c for c in layout_filter_configs if c.id == cfg_id_int), None)
    if not active_layout_cfg:
        active_layout_cfg = (
            next((c for c in layout_filter_configs if c.user_id == request.user.id and c.is_default), None)
            or next((c for c in layout_filter_configs if c.visibility == layout.filter_configs.model.VISIBILITY_PUBLIC and c.is_default), None)
            or next((c for c in layout_filter_configs if c.user_id == request.user.id), None)
            or next((c for c in layout_filter_configs if c.visibility == layout.filter_configs.model.VISIBILITY_PUBLIC), None)
        )

    # Build layout-level filter schema by union of block schemas (dedup by key)
    load_specs()
    reg = get_registry()
    policy = PolicyService()
    layout_filter_schema: Dict[str, Dict[str, Any]] = {}
    try:
        from django.urls import reverse as _reverse
        for lb in LayoutBlock.objects.filter(layout=layout).order_by("position", "id"):
            spec = reg.get(lb.block.code) if lb and lb.block else None
            services = getattr(spec, "services", None) if spec else None
            if not (spec and services and getattr(services, "filter_resolver", None)):
                continue
            try:
                resolver = services.filter_resolver(spec)
            except TypeError:
                resolver = services.filter_resolver()
            try:
                raw_schema = list(resolver.schema())
            except Exception:
                raw_schema = []
            raw_schema = prune_filter_schema(
                raw_schema,
                model=getattr(spec, "model", None),
                user=request.user,
                policy=policy,
            )
            for entry in (raw_schema or []):
                if not isinstance(entry, dict):
                    continue
                key = entry.get("key")
                if not key or key in layout_filter_schema:
                    continue
                e = dict(entry)
                typ = e.get("type")
                if typ in {"select", "multiselect"}:
                    try:
                        e["choices_url"] = _reverse("blocks:choices_spec", args=[spec.id, key])
                    except Exception:
                        pass
                layout_filter_schema[str(key)] = e
    except Exception:
        layout_filter_schema = {}

    # Build block HTML server-side (cards)
    blocks: List[Dict[str, Any]] = []
    rendered_blocks: List[Dict[str, Any]] = []
    for lb in LayoutBlock.objects.filter(layout=layout).order_by("position", "id"):
        data = _serialize_layout_block(lb, request, registry=reg, policy=policy)
        blocks.append(data)
        rendered_blocks.append({"id": data["id"], "html": data.get("html", "")})

    active_badges: List[Dict[str, str]] = []
    try:
        vals = dict(getattr(active_layout_cfg, "values", {}) or {})
        for k, v in vals.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                text = ", ".join(str(x) for x in v if x not in (None, ""))
            else:
                text = str(v)
            if text:
                active_badges.append({"key": str(k), "label": str(k), "value": text})
    except Exception:
        active_badges = []

    ctx: Dict[str, Any] = {
        "layout": layout,
        **_group_layouts_for_sidebar(request.user),
        "blocks": blocks,
        "rendered_blocks": rendered_blocks,
        "layout_filter_configs": layout_filter_configs,
        "active_layout_filter_config_id": getattr(active_layout_cfg, "id", None),
        "active_layout_filter_badges": active_badges,
        "layout_filter_schema": layout_filter_schema,
        "layout_filter_initial_values": (lambda vals: (lambda out: out)(
            (lambda out: [out.__setitem__(k[8:] if k.startswith('filters.') else k, v) or None for k,v in (vals or {}).items()] or out)({})
        ))(getattr(active_layout_cfg, "values", {}) or {}),
    }
    return render(request, "layout/layout_detail.html", ctx)

def ping(_request: HttpRequest) -> HttpResponse:
    return HttpResponse("layouts v2 ok", content_type="text/plain")


@login_required
def layout_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        visibility = (request.POST.get("visibility") or Layout.VISIBILITY_PRIVATE).strip()
        category = (request.POST.get("category") or "").strip()
        description = (request.POST.get("description") or "").strip()
        error = None
        if not name:
            error = "Name is required."
        elif visibility not in {Layout.VISIBILITY_PRIVATE, Layout.VISIBILITY_PUBLIC}:
            error = "Invalid visibility."
        if not error:
            try:
                layout = Layout.objects.create(
                    name=name,
                    user=request.user,
                    visibility=visibility,
                    category=category,
                    description=description,
                )
                return redirect("layout:layout_detail", username=layout.user.username, slug=layout.slug)
            except Exception:
                error = "Unable to create layout (name may already exist)."
        ctx: Dict[str, Any] = {
            "mode": "create",
            "error": error,
            "form": {
                "name": name,
                "visibility": visibility,
                "category": category,
                "description": description,
            },
            **_group_layouts_for_sidebar(request.user),
        }
        return render(request, "layout/layout_form.html", ctx)

    ctx: Dict[str, Any] = {
        "mode": "create",
        "form": {
            "name": "",
            "visibility": Layout.VISIBILITY_PRIVATE,
            "category": "",
            "description": "",
        },
        **_group_layouts_for_sidebar(request.user),
    }
    return render(request, "layout/layout_form.html", ctx)


@login_required
def rename_layout_filter_config(request: HttpRequest, username: str, slug: str, config_id: int) -> HttpResponse:
    if request.method != "POST":
        from django.shortcuts import redirect
        return redirect("layout:layout_manage_filters", username=username, slug=slug)
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
        return redirect("layout:layout_manage_filters", username=username, slug=slug)
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
        return redirect("layout:layout_manage_filters", username=username, slug=slug)
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
        return redirect("layout:layout_manage_filters", username=username, slug=slug)
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
        data = _serialize_layout_block(lb, request, registry=reg, policy=policy)
        blocks.append(data)
        blocks_meta.append({
            "id": data["id"],
            "x": data["x"],
            "y": data["y"],
            "w": data["w"],
            "h": data["h"],
            "title": data.get("title", ""),
            "note": data.get("note", ""),
            "code": data.get("code", ""),
            "preferred_filter_name": data.get("preferred_filter_name", ""),
            "preferred_setting_name": data.get("preferred_setting_name", ""),
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
    return render(request, "layout/layout_design.html", ctx)


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
    payload: Dict[str, Any] = {}
    if request.content_type == "application/json":
        try:
            import json as _json

            payload = _json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            payload = {}
    if not payload:
        payload = request.POST

    spec_id = (payload.get("spec_id") or payload.get("block") or "").strip()
    if not spec_id:
        return JsonResponse({"ok": False, "error": "Missing block identifier."}, status=400)

    from apps.blocks.configs import get_block_for_spec

    try:
        block = get_block_for_spec(spec_id)
    except Exception:
        return JsonResponse({"ok": False, "error": "Unknown block."}, status=404)

    next_pos = (LayoutBlock.objects.filter(layout=layout).aggregate(m=models.Max("position")).get("m") or 0) + 1
    existing = list(LayoutBlock.objects.filter(layout=layout).values("x", "y", "h"))
    try:
        bottom_y = (
            max(int((e.get("y") or 0)) + int((e.get("h") or 1)) for e in existing)
            if existing
            else 0
        )
    except Exception:
        bottom_y = 0

    lb = LayoutBlock.objects.create(
        layout=layout,
        block=block,
        position=next_pos,
        x=0,
        y=bottom_y,
        w=4,
        h=2,
    )

    load_specs()
    reg = get_registry()
    policy = PolicyService()
    data = _serialize_layout_block(lb, request, registry=reg, policy=policy)

    if request.headers.get("x-requested-with", "").lower() != "xmlhttprequest" and request.content_type != "application/json":
        return redirect("layout:layout_design", username=layout.user.username, slug=layout.slug)

    return JsonResponse({"ok": True, "block": data})


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
    data = _serialize_layout_block(lb, request, registry=reg, policy=policy)
    import json as _json

    return HttpResponse(_json.dumps({"html": data.get("html", ""), "block": data}), content_type="application/json")


@login_required
def layout_block_update_v2(request: HttpRequest, username: str, slug: str, lb_id: int) -> HttpResponse:
    if request.method != "POST":
        raise Http404()
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    if not (request.user.is_staff or request.user.id == layout.user_id):
        raise Http404()
    lb = get_object_or_404(LayoutBlock, layout=layout, id=lb_id)
    title_raw = request.POST.get("title")
    note_raw = request.POST.get("note")
    try:
        import json as _json

        settings_payload = _json.loads(request.POST.get("settings_json") or "null")
    except Exception:
        settings_payload = None
    # Optional defaults for per-block selections
    pref_setting_raw = request.POST.get("preferred_setting_name")
    pref_filter_raw = request.POST.get("preferred_filter_name")
    pref_pivot_raw = request.POST.get("preferred_pivot_name")
    pref_setting = (pref_setting_raw or "").strip() if pref_setting_raw is not None else None
    pref_filter = (pref_filter_raw or "").strip() if pref_filter_raw is not None else None
    pref_pivot = (pref_pivot_raw or "").strip() if pref_pivot_raw is not None else None
    update_fields: List[str] = []
    if title_raw is not None:
        lb.title = (title_raw or "").strip()
        update_fields.append("title")
    if note_raw is not None:
        lb.note = (note_raw or "").strip()
        update_fields.append("note")
    settings_updated = False
    if isinstance(settings_payload, dict):
        lb.settings = settings_payload
        settings_updated = True
    if pref_setting_raw is not None:
        lb.preferred_setting_name = pref_setting or ""
        update_fields.append("preferred_setting_name")
    if pref_filter_raw is not None:
        lb.preferred_filter_name = pref_filter or ""
        update_fields.append("preferred_filter_name")
    if pref_pivot_raw is not None:
        try:
            base_settings = dict(lb.settings or {}) if isinstance(lb.settings, dict) else {}
            if pref_pivot:
                base_settings["preferred_pivot_name"] = pref_pivot
            else:
                base_settings.pop("preferred_pivot_name", None)
            lb.settings = base_settings
            settings_updated = True
        except Exception:
            pass
    if settings_updated:
        if "settings" not in update_fields:
            update_fields.append("settings")
    if update_fields:
        lb.save(update_fields=update_fields)
    return HttpResponse(status=204)


@login_required
def layout_block_configs_v2(request: HttpRequest, username: str, slug: str, lb_id: int) -> HttpResponse:
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    lb = get_object_or_404(LayoutBlock, layout=layout, id=lb_id)
    from apps.blocks.configs import (
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
        "filters": [],
        "settings": [],
        "columns": [],
        "pivots": [],
        "selected": {
            "setting": getattr(lb, "preferred_setting_name", "") or "",
            "column": getattr(lb, "preferred_setting_name", "") or "",
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
        data["settings"] = tbl
        data["columns"] = tbl
        data["filters"] = fil
    elif kind == "pivot":
        data["filters"] = fil
        data["pivots"] = piv
        data["settings"] = piv
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
    return render(request, "layout/filter/manage.html", ctx)


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
    html = render_to_string("layout/filter/_saved_filters.html", {"layout": layout, "filter_configs": list(qs), "request": request}, request=request)
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
    url = reverse("layout:layout_detail", kwargs={"username": layout.user.username, "slug": layout.slug})
    if "?" in url:
        url = url + "&layout_filter_config_id=" + str(obj.id)
    else:
        url = url + "?layout_filter_config_id=" + str(obj.id)
    return redirect(url)


@login_required
def layout_edit(request: HttpRequest, username: str, slug: str) -> HttpResponse:
    user = get_object_or_404(CustomUser, username=username)
    layout = get_object_or_404(Layout, user=user, slug=slug)
    # Basic owner check: only owner or staff can edit
    if not (request.user.is_staff or request.user.id == layout.user_id):
        raise Http404()

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        visibility = (request.POST.get("visibility") or Layout.VISIBILITY_PRIVATE).strip()
        category = (request.POST.get("category") or "").strip()
        description = (request.POST.get("description") or "").strip()
        error = None
        if not name:
            error = "Name is required."
        elif visibility not in {Layout.VISIBILITY_PRIVATE, Layout.VISIBILITY_PUBLIC}:
            error = "Invalid visibility."
        if not error:
            try:
                layout.name = name
                layout.visibility = visibility
                layout.category = category
                layout.description = description
                layout.save()
                return redirect("layout:layout_detail", username=layout.user.username, slug=layout.slug)
            except Exception:
                error = "Unable to save layout (name may conflict)."
        ctx: Dict[str, Any] = {
            "mode": "edit",
            "layout": layout,
            "error": error,
            "form": {
                "name": name,
                "visibility": visibility,
                "category": category,
                "description": description,
            },
            **_group_layouts_for_sidebar(request.user),
        }
        return render(request, "layout/layout_form.html", ctx)

    ctx: Dict[str, Any] = {
        "mode": "edit",
        "layout": layout,
        "form": {
            "name": layout.name,
            "visibility": layout.visibility,
            "category": layout.category,
            "description": layout.description,
        },
        **_group_layouts_for_sidebar(request.user),
    }
    return render(request, "layout/layout_form.html", ctx)
