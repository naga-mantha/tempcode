from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.apps import apps
from django.http import JsonResponse
import json
from apps.layout.models import TableViewConfig, UserColumnConfig, FieldDisplayRule, UserFilterConfig
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from apps.layout.filter_registry import get_filter_schema

def table_by_name(request, table_name):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    app_label, model_name = config.model_label.split('.')
    model = apps.get_model(app_label, model_name)

    # -----------------------------
    # COLUMN CONFIG
    user_configs = UserColumnConfig.objects.filter(user=request.user, table_config=config)
    selected_config_id = request.GET.get("config")
    selected_config = (
        user_configs.filter(id=selected_config_id).first() if selected_config_id
        else user_configs.filter(is_default=True).first()
    )
    if not selected_config and user_configs.exists():
        selected_config = user_configs.first()

    # Get field names and flatten
    all_fields = get_flat_fields(model)
    selected_names = selected_config.fields if selected_config else [f["name"] for f in all_fields]
    fields = [f for name in selected_names for f in all_fields if f["name"] == name]
    fields.insert(0, {"name": "id", "label": "ID", "editable": False})

    # -----------------------------
    # FILTER CONFIG
    filter_configs = UserFilterConfig.objects.filter(user=request.user, table_config=config)
    selected_filter_id = request.GET.get("filter")
    selected_filter = (
        filter_configs.filter(id=selected_filter_id).first() if selected_filter_id
        else filter_configs.filter(is_default=True).first()
    )
    filter_schema = get_filter_schema(table_name)

    return render(request, "table_view/table.html", {
        "app_label": app_label,
        "model_name": model_name,
        "table_name": table_name,
        "fields": fields,
        "title": config.title or model.__name__,
        "tabulator_options": config.tabulator_options,

        # column config
        "user_configs": user_configs,
        "active_config_id": selected_config.id if selected_config else None,

        # filter config
        "filter_configs": filter_configs,
        "active_filter_id": selected_filter.id if selected_filter else None,
        "filter_schema": filter_schema,
        "selected_filter_values": selected_filter.values if selected_filter else {},
    })


@login_required
def table_data_by_name(request, table_name):
    # 1) Resolve the table & model
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    app_label, model_name = config.model_label.split('.')
    model = apps.get_model(app_label, model_name)

    # Start with full queryset
    qs = model.objects.all()

    # 2) Load saved filter values (if any)
    filters = {}
    if (fid := request.GET.get("filter")) and request.user.is_authenticated:
        ufc = get_object_or_404(
            UserFilterConfig,
            id=fid,
            user=request.user,
            table_config=config
        )
        filters.update(ufc.values)

    # 3) Merge dynamic filters from the query string
    for key, val in request.GET.items():
        if key in ("filter", "config") or not val:
            continue
        filters[key] = val

    # 4) Apply each registered filter handler
    schema = get_filter_schema(table_name)
    for key, val in filters.items():
        entry = schema.get(key)
        if entry and callable(entry.get("handler")):
            qs = entry["handler"](qs, val)

    # 5) Determine which fields to return (column config)
    if (cid := request.GET.get("config")) and request.user.is_authenticated:
        ucc = get_object_or_404(
            UserColumnConfig,
            id=cid,
            user=request.user,
            table_config=config
        )
        field_names = ucc.fields
    else:
        # fallback: include all fields (except excluded) + id
        from apps.layout.views import get_flat_fields  # or import at top
        field_names = [f["name"] for f in get_flat_fields(model)]
    # ensure “id” is always first
    if "id" not in field_names:
        field_names.insert(0, "id")

    # 6) Return JSON
    data = list(qs.values(*field_names))
    return JsonResponse(data, safe=False)


def table_update_by_name(request, table_name, pk):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model = apps.get_model(*config.model_label.split('.'))
    obj = get_object_or_404(model, pk=pk)
    data = json.loads(request.body)
    for k, v in data.items():
        setattr(obj, k, v)
    obj.save()
    return JsonResponse({'success': True})

def get_flat_fields(model):
    model_label = f"{model._meta.app_label}.{model.__name__}"
    rules = FieldDisplayRule.objects.filter(model_label=model_label)
    rule_map = {r.field_name: r for r in rules}

    fields = []
    for field in model._meta.fields:
        rule = rule_map.get(field.name)
        if rule and rule.is_excluded:
            continue  # Skip excluded fields

        if isinstance(field, models.ForeignKey):
            rel_model = field.remote_field.model
            rel_label = f"{rel_model._meta.app_label}.{rel_model.__name__}"
            rel_rules = FieldDisplayRule.objects.filter(model_label=rel_label)
            rel_rule_map = {r.field_name: r for r in rel_rules}

            for subfield in rel_model._meta.fields:
                if subfield.name == "id":
                    continue
                rel_rule = rel_rule_map.get(subfield.name)
                if rel_rule and rel_rule.is_excluded:
                    continue

                fields.append({
                    "name": f"{field.name}__{subfield.name}",
                    "label": f"{field.verbose_name.title()} → {subfield.verbose_name.title()}",
                    "mandatory": rel_rule.is_mandatory if rel_rule else False,
                    "editable": False
                })
        else:
            fields.append({
                "name": field.name,
                "label": field.verbose_name.title(),
                "mandatory": rule.is_mandatory if rule else False,
                "editable": True
            })
    return fields

@login_required
def column_config_view(request, table_name):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model = apps.get_model(*config.model_label.split('.'))
    all_fields = get_flat_fields(model)

    user_configs = UserColumnConfig.objects.filter(user=request.user, table_config=config)

    raw_id = request.GET.get("config") or request.POST.get("config_id")
    selected_config_id = raw_id if raw_id not in [None, "", "None"] else None
    selected_config = user_configs.filter(id=selected_config_id).first() if selected_config_id else None

    if request.method == "POST":
        selected_fields = request.POST.getlist("field_order[]")
        name = request.POST.get("name", "Unnamed").strip()
        is_default = request.POST.get("is_default") == "on"

        if selected_config:
            selected_config.fields = selected_fields
            selected_config.name = name
            selected_config.is_default = is_default
            selected_config.save()
        else:
            selected_config = UserColumnConfig.objects.create(
                user=request.user,
                table_config=config,
                name=name,
                fields=selected_fields,
                is_default=is_default
            )

        return redirect("layout_table_by_name", table_name=table_name)

    selected_fields = selected_config.fields if selected_config else [f["name"] for f in all_fields]

    return render(request, "table_view/column_config.html", {
        "table_name": table_name,
        "all_fields": all_fields,
        "selected_fields": selected_fields,
        "user_configs": user_configs,
        "selected_config_id": selected_config.id if selected_config else "",
    })

@require_POST
@login_required
def delete_column_config(request, table_name, config_id):
    config = get_object_or_404(UserColumnConfig, id=config_id, user=request.user)
    config.delete()
    return redirect("layout_column_config", table_name=table_name)


@login_required
@require_POST
def save_filter_by_name(request, table_name):
    """
    Expects JSON body { name: str, values: dict }.
    Creates a new UserFilterConfig for the current user/table.
    Returns { id, name } on success or { error } on failure.
    """
    # 1) Parse JSON
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name   = payload.get("name", "").strip()
    values = payload.get("values")
    if not name or not isinstance(values, dict):
        return JsonResponse({"error": "Must include non-empty 'name' and 'values' dict"}, status=400)

    # 2) Lookup table config
    config = get_object_or_404(TableViewConfig, table_name=table_name)

    # 3) Create (or you could update if name exists)
    ufc = UserFilterConfig.objects.create(
        user=request.user,
        table_config=config,
        name=name,
        values=values,
        is_default=False,
    )

    # 4) Return the new ID & name
    return JsonResponse({"id": ufc.id, "name": ufc.name})

@login_required
def filter_config_view(request, table_name):
    """
    List + create / edit one UserFilterConfig for this user + table.
    """
    # 1) Lookup the table config & filter‐schema metadata
    table_conf    = get_object_or_404(TableViewConfig, table_name=table_name)
    schema        = get_filter_schema(table_name)
    user_filters  = UserFilterConfig.objects.filter(
        user=request.user,
        table_config=table_conf
    )

    # 2) Are we editing an existing one?
    editing_id = request.GET.get("id") or request.POST.get("id")
    editing = user_filters.filter(id=editing_id).first() if editing_id else None

    if request.method == "POST":
        # 3) Parse POSTed form
        name       = request.POST.get("name","").strip()
        is_default = bool(request.POST.get("is_default"))
        # Gather only schema keys:
        values = {
            k: request.POST[k]
            for k in schema.keys()
            if request.POST.get(k)
        }

        # 4) If marking default, clear prior defaults
        if is_default:
            user_filters.update(is_default=False)

        if editing:
            editing.name       = name
            editing.values     = values
            editing.is_default = is_default
            editing.save()
        else:
            editing = UserFilterConfig.objects.create(
                user=request.user,
                table_config=table_conf,
                name=name,
                values=values,
                is_default=is_default,
            )

        return redirect("layout_filter_config", table_name=table_name)

    # 5) Prepare initial values for the form
    initial = editing.values if editing else {}
    return render(request, "table_view/filter_config.html", {
        "table_name":        table_name,
        "filter_schema":     schema,
        "user_filters":      user_filters,
        "editing":           editing,
        "initial_values":    initial,
    })


@login_required
@require_POST
def delete_filter_config(request, table_name, config_id):
    """
    Deletes one saved filter and redirects back to the config list.
    """
    ufc = get_object_or_404(
        UserFilterConfig,
        id=config_id,
        user=request.user,
        table_config__table_name=table_name
    )
    ufc.delete()
    return redirect("layout_filter_config", table_name=table_name)