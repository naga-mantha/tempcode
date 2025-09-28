from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from apps_v2.blocks.controller import BlockController
from apps_v2.blocks.registry import get_registry
from apps_v2.blocks.register import load_specs
from apps_v2.policy.service import PolicyService
from django.http import JsonResponse
from django.core.cache import cache
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
import json
from apps_v2.blocks.configs import get_block_for_spec
from apps_v2.blocks.options import merge_table_options
from apps_v2.blocks.services.field_catalog import build_field_catalog
from io import StringIO, BytesIO
import csv
from django.http import HttpResponse
from datetime import datetime
try:
    from openpyxl import Workbook
except Exception:  # pragma: no cover
    Workbook = None


@login_required
def hello(request: HttpRequest) -> HttpResponse:
    """Minimal V2 hello block render to prove the mount works."""
    ctx = {
        "title": "Hello Block (V2)",
        "message": "V2 scaffolding is wired — hello from Blocks V2!",
    }
    return render(request, "v2/blocks/hello.html", ctx)


@login_required
def render_spec(request: HttpRequest, spec_id: str) -> HttpResponse:
    """Render a block partial for HTMX refresh by spec id.

    For tables, returns the card+table fragment so the caller can replace
    the existing block with `hx-swap="outerHTML"`.
    """
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    if not spec:
        raise Http404("Unknown block spec")
    ctx = BlockController(spec, PolicyService()).build_context(request)
    # Choose partial template by kind
    template = spec.template
    if spec.kind == "table":
        template = "v2/blocks/table/table_card.html"
    return render(request, template, ctx)


@login_required
def data_spec(request: HttpRequest, spec_id: str) -> HttpResponse:
    """JSON data endpoint for Tabulator remote pagination/sorting."""
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    if not spec:
        raise Http404("Unknown block spec")

    services = spec.services or None
    policy = PolicyService()

    # Resolve filters + merge saved filter config
    if services and services.filter_resolver:
        try:
            resolver = services.filter_resolver(spec)
        except TypeError:
            resolver = services.filter_resolver()
        filters = resolver.resolve(request)
    else:
        filters = {}
    from apps_v2.blocks.configs import get_block_for_spec, choose_active_filter_config
    block_row = get_block_for_spec(spec_id)
    filt_cfg_id = request.GET.get("filter_config_id")
    try:
        filt_cfg_id_int = int(filt_cfg_id) if filt_cfg_id else None
    except ValueError:
        filt_cfg_id_int = None
    active_filter_cfg = choose_active_filter_config(block_row, request.user, filt_cfg_id_int)
    base_filter_values = getattr(active_filter_cfg, "values", {}) or {}
    if services and services.filter_resolver:
        try:
            cleaner = services.filter_resolver(spec)
        except TypeError:
            cleaner = services.filter_resolver()
        base_filter_values = cleaner.clean(base_filter_values)
    filters = {**base_filter_values, **filters}
    # Build queryset
    if services and services.query_builder:
        try:
            qb = services.query_builder(request, policy, spec)
        except TypeError:
            qb = services.query_builder(request, policy)
        qs = qb.get_queryset(filters)
    else:
        qs = []
    # Resolve columns and safe sort allowlist
    if services and services.column_resolver:
        try:
            colr = services.column_resolver(spec, policy)
        except TypeError:
            try:
                colr = services.column_resolver(spec)
            except TypeError:
                colr = services.column_resolver()
        columns = colr.get_columns(request)
    else:
        columns = []
    allowed_fields = {c.get("key") for c in columns}
    # Hint ORM to prefetch simple relations referenced by columns
    try:
        rel_prefixes = sorted({k.split("__")[0] for k in allowed_fields if "__" in (k or "")})
        if rel_prefixes:
            qs = qs.select_related(*rel_prefixes)
    except Exception:
        pass

    # Sorting (validated)
    sort = request.GET.get("sort")
    direction = request.GET.get("dir", "asc")
    if sort:
        if sort not in allowed_fields:
            return JsonResponse({"error": "Invalid sort field"}, status=400)
        if direction not in {"asc", "desc"}:
            return JsonResponse({"error": "Invalid sort direction"}, status=400)
        order = sort if direction == "asc" else f"-{sort}"
        try:
            qs = qs.order_by(order, "pk")
        except Exception:
            return JsonResponse({"error": "Unable to apply sort"}, status=400)

    # Pagination (validated)
    try:
        page = int(request.GET.get("page", "1"))
    except ValueError:
        return JsonResponse({"error": "Invalid page"}, status=400)
    try:
        size = int(request.GET.get("size", "10"))
    except ValueError:
        return JsonResponse({"error": "Invalid size"}, status=400)
    if page < 1:
        return JsonResponse({"error": "Page must be >= 1"}, status=400)
    size = max(1, min(size, 200))  # cap page size
    start = (page - 1) * size
    end = start + size
    try:
        total = qs.count()
        qs = qs[start:end]
    except Exception:
        total = 0

    # Serialize rows
    if services and services.serializer:
        try:
            ser = services.serializer(spec)
        except TypeError:
            ser = services.serializer()
        rows = list(ser.serialize_rows(qs, columns, user=request.user, policy=policy))
    else:
        rows = []
    # Include last_page for Tabulator remote pagination
    try:
        last_page = max(1, (total + size - 1) // size)
    except Exception:
        last_page = 1
    # Minimal shape; Tabulator reads `data`, and uses `last_page` if present
    return JsonResponse({
        "data": rows,
        "page": page,
        "size": size,
        "total": total,
        "last_page": last_page,
    })


@login_required
def choices_spec(request: HttpRequest, spec_id: str, field: str) -> HttpResponse:
    """Return choices for a filter field, using schema + model.

    Default behavior: for select/multiselect without explicit choices,
    return distinct DB values for the mapped model field, with dependent
    narrowing based on other active filters.
    """
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    if not spec:
        raise Http404("Unknown block spec")
    services = spec.services or None
    policy = PolicyService()
    if not (services and services.filter_resolver and services.query_builder and spec):
        return JsonResponse({"results": []})
    # Load schema
    try:
        resolver = services.filter_resolver(spec)
    except TypeError:
        resolver = services.filter_resolver()
    try:
        schema = list(resolver.schema())
    except Exception:
        schema = []
    entry = next((s for s in schema if s.get("key") == field), None)
    if not entry:
        return JsonResponse({"results": []})
    model_field = entry.get("field") or entry.get("key")
    # Min query length (default 3) to avoid expensive scans on short probes
    try:
        min_len = int(entry.get("min_query_length", 3))
    except Exception:
        min_len = 3
    q = (request.GET.get("q") or "").strip()
    if len(q) < (min_len or 0):
        return JsonResponse({"results": []})
    # Build filters and remove target field values to avoid self-filtering
    filters = resolver.resolve(request)
    filters.pop(field, None)
    # Cache key includes spec, field, query (lowercased), and a stable filter fingerprint
    try:
        filt_fp = ":".join(f"{k}={v}" for k, v in sorted(filters.items()))
    except Exception:
        filt_fp = ""
    cache_key = f"v2:choices:{spec_id}:{field}:{q.lower()}:{filt_fp}"
    cached = cache.get(cache_key)
    if cached is not None:
        return JsonResponse({"results": cached})
    # Build queryset
    try:
        try:
            qb = services.query_builder(request, policy, spec)
        except TypeError:
            qb = services.query_builder(request, policy)
        qs = qb.get_queryset(filters)
    except Exception:
        qs = []
    # Optional text search narrowing
    if q and model_field:
        try:
            qs = qs.filter(**{f"{model_field}__icontains": q})
        except Exception:
            pass
    # Return distinct values
    data = []
    try:
        values = (
            qs.exclude(**{model_field: ""})
              .values_list(model_field, flat=True)
              .distinct()
              .order_by(model_field)[:50]
        )
        data = [{"value": v, "label": v} for v in values]
    except Exception:
        data = []
    try:
        cache.set(cache_key, data, timeout=60)
    except Exception:
        pass
    return JsonResponse({"results": data})


@login_required
@require_POST
def save_table_config(request: HttpRequest, spec_id: str) -> HttpResponse:
    """Save a table config (columns + options) for this spec and user.

    For now, saves only columns from the client; options can be added later.
    """
    from apps.blocks.models.table_config import BlockTableConfig

    block = get_block_for_spec(spec_id)
    name = request.POST.get("name", "").strip()
    visibility = request.POST.get("visibility", "private")
    is_default = request.POST.get("is_default") in {"on", "true", "1"}
    try:
        cols = json.loads(request.POST.get("columns_json") or "[]")
        if not isinstance(cols, list):
            cols = []
    except Exception:
        cols = []

    # Prune columns via safe catalog (policy-checked, allowlist specific to model if needed)
    policy = PolicyService()
    load_specs()
    spec = get_registry().get(spec_id)
    model = getattr(spec, "model", None) if spec else None
    allowed_cols = set()
    mandatory_cols = set()
    if model is not None:
        catalog = build_field_catalog(
            model,
            user=request.user,
            policy=policy,
            max_depth=getattr(spec, "column_max_depth", 0) or 0,
        )
        allowed_cols = {c["key"] for c in catalog}
        mandatory_cols = {c["key"] for c in catalog if c.get("mandatory")}
    cols = [c for c in cols if c in allowed_cols]
    # Ensure mandatory fields are always included in saved configs
    for m in mandatory_cols:
        if m not in cols:
            cols.append(m)

    # Merge/clean options via allowlist
    # Per-view options disabled; keep options empty and rely on spec.table_options
    options = {}

    obj, _ = BlockTableConfig.objects.update_or_create(
        block=block, user=request.user, name=name or "Default",
        defaults={
            "columns": cols,
            "visibility": visibility if visibility in {BlockTableConfig.VISIBILITY_PRIVATE, BlockTableConfig.VISIBILITY_PUBLIC} else BlockTableConfig.VISIBILITY_PRIVATE,
            "is_default": bool(is_default),
        }
    )
    # Respond with 204 (no content); HTMX will leave UI as-is
    return HttpResponse(status=204)


@login_required
@require_POST
def save_filter_config(request: HttpRequest, spec_id: str) -> HttpResponse:
    """Save a filter config for this spec and user.

    Values are validated/pruned via the block's FilterResolver.clean().
    """
    from apps.blocks.models.block_filter_config import BlockFilterConfig

    block = get_block_for_spec(spec_id)
    name = request.POST.get("name", "").strip()
    visibility = request.POST.get("visibility", "private")
    is_default = request.POST.get("is_default") in {"on", "true", "1"}
    try:
        values = json.loads(request.POST.get("values_json") or "{}")
        if not isinstance(values, dict):
            values = {}
    except Exception:
        values = {}

    # Ensure JSON-serializable (dates → ISO strings, sets → lists)
    def _json_safe(x):
        try:
            from datetime import date, datetime
            if isinstance(x, (date, datetime)):
                return x.isoformat()
        except Exception:
            pass
        if isinstance(x, dict):
            return {k: _json_safe(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [ _json_safe(v) for v in x ]
        if isinstance(x, set):
            return [ _json_safe(v) for v in x ]
        return x
    values = _json_safe(values)

    # Use the spec's filter resolver to clean values
    load_specs()
    spec = get_registry().get(spec_id)
    services = spec.services or None
    if services and services.filter_resolver:
        try:
            cleaner = services.filter_resolver(spec)
        except TypeError:
            cleaner = services.filter_resolver()
        values = cleaner.clean(values)
    else:
        values = {}

    obj, _ = BlockFilterConfig.objects.update_or_create(
        block=block, user=request.user, name=name or "Default",
        defaults={
            "values": values,
            "visibility": visibility if visibility in {BlockFilterConfig.VISIBILITY_PRIVATE, BlockFilterConfig.VISIBILITY_PUBLIC} else BlockFilterConfig.VISIBILITY_PRIVATE,
            "is_default": bool(is_default),
        }
    )
    # For HTMX requests, return updated Saved Filters partial so the page can refresh without full reload
    if request.headers.get("HX-Request") or request.META.get("HTTP_HX_REQUEST"):
        from apps_v2.blocks.configs import get_block_for_spec, list_filter_configs
        block_row = get_block_for_spec(spec_id)
        filter_configs = list(list_filter_configs(block_row, request.user))
        ctx = {"spec_id": spec_id, "filter_configs": filter_configs, "request": request}
        from django.template.loader import render_to_string
        html = render_to_string("v2/blocks/filter/_saved_filters.html", ctx, request=request)
        return HttpResponse(html)
    return HttpResponse(status=204)


@login_required
def manage_filters(request: HttpRequest, spec_id: str) -> HttpResponse:
    """Manage Filters page (V2): list/rename/duplicate/delete/make-default filter configs.

    Also links to Filter Layout (per-user) and Default Filter Layout (admin).
    """
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    if not spec:
        raise Http404("Unknown block spec")
    from apps_v2.blocks.configs import get_block_for_spec, list_filter_configs, choose_active_filter_config
    block = get_block_for_spec(spec_id)
    # Load all user-visible filter configs
    filter_configs = list(list_filter_configs(block, request.user))
    # Active selection (optional via query param)
    had_cfg_param = "filter_config_id" in request.GET
    cfg_id = request.GET.get("filter_config_id")
    try:
        cfg_id_int = int(cfg_id) if cfg_id else None
    except ValueError:
        cfg_id_int = None
    if had_cfg_param:
        active_cfg = choose_active_filter_config(block, request.user, cfg_id_int)
    else:
        active_cfg = None
    # Build filter schema (V2) for render + load per-user/default layout
    services = spec.services or None
    schema_list = []
    if services and services.filter_resolver:
        try:
            resolver = services.filter_resolver(spec)
        except TypeError:
            resolver = services.filter_resolver()
        try:
            schema_list = list(resolver.schema())
        except Exception:
            schema_list = []
    # Build mapping for template include (key -> cfg)
    filter_schema = {s.get("key"): s for s in schema_list if isinstance(s, dict) and s.get("key")}
    # Load user/default filter layout (if any)
    from apps.blocks.models.block_filter_layout import BlockFilterLayout
    from apps.blocks.models.config_templates import BlockFilterLayoutTemplate
    user_layout = BlockFilterLayout.objects.filter(block=block, user=request.user).first()
    admin_layout = BlockFilterLayoutTemplate.objects.filter(block=block).first()
    filter_layout = None
    if user_layout and isinstance(user_layout.layout, dict):
        filter_layout = user_layout.layout
    elif admin_layout and isinstance(admin_layout.layout, dict):
        filter_layout = admin_layout.layout

    ctx = {
        "spec": spec,
        "spec_id": spec_id,
        "filter_configs": filter_configs,
        "active_filter_config_id": getattr(active_cfg, "id", None),
        # Filter schema + layout for inline create form
        "filter_schema": filter_schema,
        "filter_layout": filter_layout,
        "initial_values": {},
    }
    return render(request, "v2/blocks/filter/manage_filters.html", ctx)


@login_required
@require_POST
def rename_filter_config(request: HttpRequest, spec_id: str, config_id: int) -> HttpResponse:
    # Guard: if not POST, just bounce back to Manage Filters (avoid 405 confusion)
    if request.method != "POST":
        return redirect("blocks_v2:manage_filters", spec_id=spec_id)

    from apps.blocks.models.block_filter_config import BlockFilterConfig
    try:
        obj = BlockFilterConfig.objects.get(pk=config_id, user=request.user)
    except BlockFilterConfig.DoesNotExist:
        return HttpResponse(status=404)
    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        return HttpResponse(status=400)
    obj.name = new_name
    obj.save(update_fields=["name"])
    if request.headers.get("HX-Request") or request.META.get("HTTP_HX_REQUEST"):
        from apps_v2.blocks.configs import get_block_for_spec, list_filter_configs
        block_row = get_block_for_spec(spec_id)
        filter_configs = list(list_filter_configs(block_row, request.user))
        from django.template.loader import render_to_string
        html = render_to_string("v2/blocks/filter/_saved_filters.html", {"spec_id": spec_id, "filter_configs": filter_configs, "request": request}, request=request)
        return HttpResponse(html)
    return HttpResponse(status=204)


@login_required
@require_POST
def duplicate_filter_config(request: HttpRequest, spec_id: str, config_id: int) -> HttpResponse:
    from apps.blocks.models.block_filter_config import BlockFilterConfig
    try:
        obj = BlockFilterConfig.objects.get(pk=config_id)
    except BlockFilterConfig.DoesNotExist:
        return HttpResponse(status=404)
    copy = BlockFilterConfig(
        block=obj.block,
        user=request.user,
        name=f"{obj.name} (copy)",
        values=dict(obj.values or {}),
        visibility=BlockFilterConfig.VISIBILITY_PRIVATE,
        is_default=False,
    )
    copy.save()
    if request.headers.get("HX-Request") or request.META.get("HTTP_HX_REQUEST"):
        from apps_v2.blocks.configs import get_block_for_spec, list_filter_configs
        block_row = get_block_for_spec(spec_id)
        filter_configs = list(list_filter_configs(block_row, request.user))
        from django.template.loader import render_to_string
        html = render_to_string("v2/blocks/filter/_saved_filters.html", {"spec_id": spec_id, "filter_configs": filter_configs, "request": request}, request=request)
        return HttpResponse(html)
    return HttpResponse(status=204)


@login_required
@require_POST
def delete_filter_config(request: HttpRequest, spec_id: str, config_id: int) -> HttpResponse:
    from apps.blocks.models.block_filter_config import BlockFilterConfig
    try:
        obj = BlockFilterConfig.objects.get(pk=config_id, user=request.user)
    except BlockFilterConfig.DoesNotExist:
        return HttpResponse(status=404)
    obj.delete()
    if request.headers.get("HX-Request") or request.META.get("HTTP_HX_REQUEST"):
        from apps_v2.blocks.configs import get_block_for_spec, list_filter_configs
        block_row = get_block_for_spec(spec_id)
        filter_configs = list(list_filter_configs(block_row, request.user))
        from django.template.loader import render_to_string
        html = render_to_string("v2/blocks/filter/_saved_filters.html", {"spec_id": spec_id, "filter_configs": filter_configs, "request": request}, request=request)
        return HttpResponse(html)
    return HttpResponse(status=204)


@login_required
@require_POST
def make_default_filter_config(request: HttpRequest, spec_id: str, config_id: int) -> HttpResponse:
    from apps.blocks.models.block_filter_config import BlockFilterConfig
    try:
        obj = BlockFilterConfig.objects.get(pk=config_id, user=request.user)
    except BlockFilterConfig.DoesNotExist:
        return HttpResponse(status=404)
    obj.is_default = True
    obj.save(update_fields=["is_default"])  # model enforces single default
    if request.headers.get("HX-Request") or request.META.get("HTTP_HX_REQUEST"):
        from apps_v2.blocks.configs import get_block_for_spec, list_filter_configs
        block_row = get_block_for_spec(spec_id)
        filter_configs = list(list_filter_configs(block_row, request.user))
        from django.template.loader import render_to_string
        html = render_to_string("v2/blocks/filter/_saved_filters.html", {"spec_id": spec_id, "filter_configs": filter_configs, "request": request}, request=request)
        return HttpResponse(html)
    return HttpResponse(status=204)


@login_required
def export_spec(request: HttpRequest, spec_id: str, fmt: str) -> HttpResponse:
    """Server-side export for tables: csv or xlsx. PDF not implemented here."""
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    if not spec:
        raise Http404("Unknown block spec")
    services = spec.services or None
    if not services:
        raise Http404("Spec has no services")

    policy = PolicyService()
    # Resolve filters and queryset
    if services.filter_resolver:
        try:
            resolver = services.filter_resolver(spec)
        except TypeError:
            resolver = services.filter_resolver()
        filters = resolver.resolve(request)
    else:
        filters = {}
    if services.query_builder:
        try:
            qb = services.query_builder(request, policy, spec)
        except TypeError:
            qb = services.query_builder(request, policy)
        qs = qb.get_queryset(filters)
    else:
        qs = []

    # Columns with active view ordering
    if services.column_resolver:
        try:
            colr = services.column_resolver(spec, policy)
        except TypeError:
            try:
                colr = services.column_resolver(spec)
            except TypeError:
                colr = services.column_resolver()
        columns = colr.get_columns(request)
    else:
        columns = []
    allowed_fields = {c.get("key") for c in columns}
    # Hint ORM to prefetch simple relations referenced by columns
    try:
        rel_prefixes = sorted({k.split("__")[0] for k in allowed_fields if "__" in (k or "")})
        if rel_prefixes:
            qs = qs.select_related(*rel_prefixes)
    except Exception:
        pass

    # View config ordering
    from apps_v2.blocks.configs import get_block_for_spec, choose_active_table_config
    block_row = get_block_for_spec(spec_id)
    cfg_id = request.GET.get("config_id")
    try:
        cfg_id_int = int(cfg_id) if cfg_id else None
    except ValueError:
        cfg_id_int = None
    active_cfg = choose_active_table_config(block_row, request.user, cfg_id_int)
    if active_cfg and active_cfg.columns:
        ordered = [k for k in (active_cfg.columns or []) if k in allowed_fields]
        ordered += [k for k in (c.get("key") for c in columns) if k not in ordered]
        key_to_col = {c.get("key"): c for c in columns}
        columns = [key_to_col[k] for k in ordered if k in key_to_col]

    # Optional ExportOptions hook: allow spec to transform columns before serialization
    from apps_v2.blocks.services.export_options import DefaultExportOptions
    try:
        exopts = services.export_options(spec) if getattr(services, "export_options", None) else DefaultExportOptions()
    except TypeError:
        exopts = services.export_options() if getattr(services, "export_options", None) else DefaultExportOptions()
    try:
        columns = list(exopts.transform_columns(columns, request=request, filters=filters, spec=spec))
    except Exception:
        pass

    # Sorting (optional)
    sort = request.GET.get("sort")
    direction = request.GET.get("dir", "asc")
    if sort in allowed_fields:
        order = sort if direction == "asc" else f"-{sort}"
        try:
            qs = qs.order_by(order)
        except Exception:
            pass

    # Row cap
    cap = int(request.GET.get("max", "10000")) if str(request.GET.get("max", "")).isdigit() else 10000
    cap = max(1, min(cap, 50000))
    try:
        qs = qs[:cap]
    except Exception:
        pass

    # Serialize rows
    if services.serializer:
        try:
            ser = services.serializer(spec)
        except TypeError:
            ser = services.serializer()
        rows = list(ser.serialize_rows(qs, columns, user=request.user, policy=policy))
    else:
        rows = []

    # Allow ExportOptions to transform rows (formatting/mapping) after serialization
    try:
        rows = list(exopts.transform_rows(rows, columns, request=request, filters=filters, spec=spec))
    except Exception:
        pass

    # Build filename
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    # Filename via export options (fallback to default)
    try:
        opt_name = exopts.filename(spec, fmt, request, filters)  # type: ignore[arg-type]
    except Exception:
        opt_name = None
    base = (opt_name or spec_id).replace(".", "_")

    if fmt == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        header = [c.get("label") for c in columns]
        writer.writerow(header)
        keys = [c.get("key") for c in columns]
        for r in rows:
            writer.writerow([r.get(k, "") for k in keys])
        data = buf.getvalue().encode("utf-8-sig")
        resp = HttpResponse(data, content_type="text/csv")
        resp["Content-Disposition"] = f"attachment; filename=\"{base}_{ts}.csv\""
        return resp
    elif fmt == "xlsx":
        if Workbook is None:
            return HttpResponse("XLSX export not available", status=501)
        wb = Workbook()
        ws = wb.active
        try:
            sheet = exopts.sheet_name(spec)
        except Exception:
            sheet = None
        ws.title = (sheet or spec.name)[:31]
        header = [c.get("label") for c in columns]
        ws.append(header)
        keys = [c.get("key") for c in columns]
        for r in rows:
            ws.append([r.get(k, "") for k in keys])
        out = BytesIO()
        wb.save(out)
        out.seek(0)
        resp = HttpResponse(out.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f"attachment; filename=\"{base}_{ts}.xlsx\""
        return resp
    elif fmt == "pdf":
        return HttpResponse("PDF export not implemented", status=501)
    else:
        return HttpResponse("Unsupported format", status=400)


@login_required
def manage_columns(request: HttpRequest, spec_id: str) -> HttpResponse:
    """Manage Columns page (V2) using SortableJS.

    Shows available fields (policy-pruned) and selected fields (current view).
    """
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    if not spec:
        raise Http404("Unknown block spec")
    services = spec.services or None
    if not services:
        raise Http404("Spec has no services")

    # Available columns via field catalog; depth comes from spec setting
    depth = int(getattr(spec, "column_max_depth", 0) or 0)
    policy = PolicyService()
    # Use the spec's model and column controls
    model = getattr(spec, "model", None)
    if model is None:
        raise Http404("Spec has no model for column management")
    available_cols = build_field_catalog(
        model,
        user=request.user,
        policy=policy,
        max_depth=depth,
    )
    key_to_meta = {c.get("key"): c for c in available_cols}

    # Active view selection
    from apps_v2.blocks.configs import get_block_for_spec, list_table_configs, choose_active_table_config
    block_row = get_block_for_spec(spec_id)
    had_cfg_param = "config_id" in request.GET
    cfg_id = request.GET.get("config_id")
    try:
        cfg_id_int = int(cfg_id) if cfg_id else None
    except ValueError:
        cfg_id_int = None
    table_configs = list(list_table_configs(block_row, request.user))
    if had_cfg_param:
        active_cfg = choose_active_table_config(block_row, request.user, cfg_id_int)
    else:
        # Explicit "New (default)" selection: do not fall back to default view
        active_cfg = None
    # Default behavior for new views: show all fields on the left (Available)
    # and none on the right (Selected). If a config exists with columns,
    # use that list.
    if active_cfg and active_cfg.columns:
        selected_keys = list(active_cfg.columns)
        # Ensure any newly-mandatory fields are present
        mandatory_keys = [c.get("key") for c in available_cols if c.get("mandatory")]
        for mk in mandatory_keys:
            if mk not in selected_keys:
                selected_keys.append(mk)
    else:
        # New view: preselect mandatory fields
        selected_keys = [c.get("key") for c in available_cols if c.get("mandatory")]

    # Partition available/selected lists
    selected_set = set(selected_keys)
    available_only = [k for k in key_to_meta.keys() if k not in selected_set]

    selected_meta = []
    for k in selected_keys:
        meta = key_to_meta.get(k)
        if meta:
            selected_meta.append(meta)
        # If a key is no longer in the catalog (e.g., newly excluded), drop it silently

    ctx = {
        "spec": spec,
        "spec_id": spec_id,
        "available": [key_to_meta.get(k) for k in available_only],
        "selected": selected_meta,
        "table_configs": table_configs,
        "active_table_config_id": getattr(active_cfg, "id", None),
    }
    return render(request, "v2/blocks/table/manage_columns.html", ctx)


@login_required
@require_POST
def rename_table_config(request: HttpRequest, spec_id: str, config_id: int) -> HttpResponse:
    from apps.blocks.models.table_config import BlockTableConfig
    try:
        obj = BlockTableConfig.objects.get(pk=config_id, user=request.user)
    except BlockTableConfig.DoesNotExist:
        return HttpResponse(status=404)
    new_name = (request.POST.get("name") or "").strip()
    if not new_name:
        return HttpResponse(status=400)
    obj.name = new_name
    obj.save(update_fields=["name"])
    return HttpResponse(status=204)


@login_required
@require_POST
def duplicate_table_config(request: HttpRequest, spec_id: str, config_id: int) -> HttpResponse:
    from apps.blocks.models.table_config import BlockTableConfig
    try:
        obj = BlockTableConfig.objects.get(pk=config_id)
    except BlockTableConfig.DoesNotExist:
        return HttpResponse(status=404)
    copy = BlockTableConfig(
        block=obj.block,
        user=request.user,
        name=f"{obj.name} (copy)",
        columns=list(obj.columns or []),
        visibility=BlockTableConfig.VISIBILITY_PRIVATE,
        is_default=False,
    )
    copy.save()
    return HttpResponse(status=204)


@login_required
@require_POST
def delete_table_config(request: HttpRequest, spec_id: str, config_id: int) -> HttpResponse:
    from apps.blocks.models.table_config import BlockTableConfig
    try:
        obj = BlockTableConfig.objects.get(pk=config_id, user=request.user)
    except BlockTableConfig.DoesNotExist:
        return HttpResponse(status=404)
    obj.delete()
    return HttpResponse(status=204)


@login_required
@require_POST
def make_default_table_config(request: HttpRequest, spec_id: str, config_id: int) -> HttpResponse:
    from apps.blocks.models.table_config import BlockTableConfig
    try:
        obj = BlockTableConfig.objects.get(pk=config_id, user=request.user)
    except BlockTableConfig.DoesNotExist:
        return HttpResponse(status=404)
    obj.is_default = True
    obj.save(update_fields=["is_default"])  # model enforces single default
    return HttpResponse(status=204)


# Removed toggle_visibility endpoint per updated UX (visibility changes not supported here)


@login_required
def manage_filter_layout(request: HttpRequest, spec_id: str) -> HttpResponse:
    """V2-native Filter Layout (per-user) for a spec.

    Uses V2 filter schema as the available fields source.
    """
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    if not spec:
        raise Http404("Unknown block spec")
    # Resolve available fields from spec's filter schema
    services = spec.services or None
    schema = []
    if services and services.filter_resolver:
        try:
            resolver = services.filter_resolver(spec)
        except TypeError:
            resolver = services.filter_resolver()
        try:
            schema = list(resolver.schema())
        except Exception:
            schema = []
    available = []
    for f in (schema or []):
        if not isinstance(f, dict):
            continue
        key = f.get("key")
        if not key:
            continue
        available.append({
            "key": str(key),
            "label": str(f.get("label") or key),
            "type": str(f.get("type") or "text"),
        })
    # Load saved user layout or fallback to admin default
    from apps_v2.blocks.configs import get_block_for_spec
    from apps.blocks.models.block_filter_layout import BlockFilterLayout
    from apps.blocks.models.config_templates import BlockFilterLayoutTemplate
    block = get_block_for_spec(spec_id)
    user_layout = BlockFilterLayout.objects.filter(block=block, user=request.user).first()
    admin_layout = BlockFilterLayoutTemplate.objects.filter(block=block).first()
    layout_obj = {}
    if user_layout and isinstance(user_layout.layout, dict):
        layout_obj = user_layout.layout
    elif admin_layout and isinstance(admin_layout.layout, dict):
        layout_obj = admin_layout.layout
    ctx = {
        "spec": spec,
        "spec_id": spec_id,
        "available_fields": available,
        "layout_json": json.dumps(layout_obj or {}),
        "admin_mode": False,
    }
    return render(request, "v2/blocks/filter/filter_layout.html", ctx)


@login_required
def manage_filter_layout_default(request: HttpRequest, spec_id: str) -> HttpResponse:
    """V2-native Default Filter Layout (admin-only) for a spec."""
    if not request.user.is_staff:
        raise Http404()
    load_specs()
    reg = get_registry()
    spec = reg.get(spec_id)
    if not spec:
        raise Http404("Unknown block spec")
    services = spec.services or None
    schema = []
    if services and services.filter_resolver:
        try:
            resolver = services.filter_resolver(spec)
        except TypeError:
            resolver = services.filter_resolver()
        try:
            schema = list(resolver.schema())
        except Exception:
            schema = []
    available = []
    for f in (schema or []):
        if not isinstance(f, dict):
            continue
        key = f.get("key")
        if not key:
            continue
        available.append({
            "key": str(key),
            "label": str(f.get("label") or key),
            "type": str(f.get("type") or "text"),
        })
    from apps_v2.blocks.configs import get_block_for_spec
    from apps.blocks.models.config_templates import BlockFilterLayoutTemplate
    block = get_block_for_spec(spec_id)
    tpl = BlockFilterLayoutTemplate.objects.filter(block=block).first()
    layout_obj = tpl.layout if (tpl and isinstance(tpl.layout, dict)) else {}
    ctx = {
        "spec": spec,
        "spec_id": spec_id,
        "available_fields": available,
        "layout_json": json.dumps(layout_obj or {}),
        "admin_mode": True,
    }
    return render(request, "v2/blocks/filter/filter_layout.html", ctx)


@login_required
@require_POST
def save_filter_layout(request: HttpRequest, spec_id: str) -> HttpResponse:
    """Save per-user Filter Layout for a spec (V2)."""
    from apps_v2.blocks.configs import get_block_for_spec
    from apps.blocks.models.block_filter_layout import BlockFilterLayout
    block = get_block_for_spec(spec_id)
    text = request.POST.get("layout") or "{}"
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {}
    BlockFilterLayout.objects.update_or_create(block=block, user=request.user, defaults={"layout": parsed})
    return HttpResponse(status=204)


@login_required
@require_POST
def save_filter_layout_default(request: HttpRequest, spec_id: str) -> HttpResponse:
    """Save default Filter Layout (admin-only) for a spec (V2)."""
    if not request.user.is_staff:
        return HttpResponse(status=403)
    from apps_v2.blocks.configs import get_block_for_spec
    from apps.blocks.models.config_templates import BlockFilterLayoutTemplate
    block = get_block_for_spec(spec_id)
    text = request.POST.get("layout") or "{}"
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {}
    BlockFilterLayoutTemplate.objects.update_or_create(block=block, defaults={"layout": parsed})
    return HttpResponse(status=204)
