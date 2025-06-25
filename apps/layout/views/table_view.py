from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.apps import apps
from django.http import JsonResponse
import json
from apps.layout.models import TableViewConfig, UserColumnConfig, FieldDisplayRule, UserFilterConfig
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from apps.layout.filter_registry import get_filter_schema
from apps.workflow.views.permissions import can_read_field
from apps.layout.helpers.get_model_from_table import get_model_from_table
from apps.layout.helpers.api_helpers import get_filtered_queryset

def _collect_filters(request, config):
    # Start with any saved filter-values
    filters = {}
    if fid := request.GET.get("filter"):
        ufc = get_object_or_404(
            UserFilterConfig,
            id=fid, user=request.user, table_config=config
        )
        filters.update(ufc.values)
    # Merge in any other non-empty GET params (excluding filter+config)
    for k, v in request.GET.items():
        if k in ("filter", "config") or not v:
            continue
        filters[k] = v
    return filters

def _select_item(queryset, selected_id, default_field="is_default", fallback=None):
    """
    Given a queryset and a selected_id, returns:
      - the object with that id, if present
      - else the first where default_field=True
      - else the provided fallback
    """
    if selected_id:
        obj = queryset.filter(id=selected_id).first()
        if obj:
            return obj
    default = queryset.filter(is_default=True).first()
    return default or fallback

@login_required
def table_by_name(request, table_name):
    # 1) Resolve table & model
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model  = get_model_from_table(table_name)

    # 2) Column config
    col_qs    = UserColumnConfig.objects.filter(user=request.user, table_config=config)
    col       = _select_item(col_qs, request.GET.get("config"))
    all_fields = get_flat_fields(model, user=request.user)
    # only include those that the selected config lists, in order
    fields    = [f for name in col.fields for f in all_fields if f["name"] == name]

    # 3) Filter config
    filt_qs   = UserFilterConfig.objects.filter(user=request.user, table_config=config)
    filt      = _select_item(filt_qs, request.GET.get("filter"))
    filter_schema = get_filter_schema(table_name, user=request.user)
    selected_values = filt.values if filt else {}

    return render(request, "table_view/table.html", {
        "app_label":            config.model_label.split(".")[0],
        "model_name":           config.model_label.split(".")[1],
        "table_name":           table_name,
        "fields":               fields,
        "title":                config.title or model.__name__,
        "tabulator_options":    config.tabulator_options,

        # column config
        "user_configs":         col_qs,
        "active_config_id":     col.id if col else None,

        # filter config
        "filter_configs":       filt_qs,
        "active_filter_id":     filt.id if filt else None,
        "filter_schema":        filter_schema,
        "selected_filter_values": selected_values,
    })


@login_required
def table_data_by_name(request, table_name):
    # 1) Resolve table, model & config
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model  = get_model_from_table(table_name)

    # 2) Build the filters dict
    filters = _collect_filters(request, config)

    # 3) Delegate model-+field-perm checks and filter application
    qs, allowed_fields = get_filtered_queryset(
        user=request.user,
        model=model,
        table_name=table_name,
        filters=filters,
    )

    # 4) Apply user-chosen column config (if any)
    if cid := request.GET.get("config"):
        ucc = get_object_or_404(
            UserColumnConfig,
            id=cid, user=request.user, table_config=config
        )
        allowed_fields = [f for f in ucc.fields if f in allowed_fields]

    # 5) Return only those columns
    return JsonResponse(list(qs.values(*allowed_fields)), safe=False)

def table_update_by_name(request, table_name, pk):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model = apps.get_model(*config.model_label.split('.'))
    obj = get_object_or_404(model, pk=pk)
    data = json.loads(request.body)
    for k, v in data.items():
        setattr(obj, k, v)
    obj.save()
    return JsonResponse({'success': True})

def get_flat_fields(model, user):
    """
    Returns a list of dicts describing every non-excluded DB field on `model`,
    expanding FK→subfields. If `user` is provided, only includes fields
    they have `view_<model>_<field>` permission on.
    """
    model_label = f"{model._meta.app_label}.{model.__name__}"
    rules = FieldDisplayRule.objects.filter(model_label=model_label)
    rule_map = {r.field_name: r for r in rules}

    # dummy instance for permission checks
    instance = model()

    fields = []
    for field in model._meta.fields:
        # 1) skip excluded by your FieldDisplayRule
        rule = rule_map.get(field.name)
        if rule and rule.is_excluded:
            continue

        # 2) skip if user lacks read-perm
        if user and not can_read_field(user, instance, field.name):
            continue

        if isinstance(field, models.ForeignKey):
            # expand FK subfields
            rel_model   = field.remote_field.model
            rel_label   = f"{rel_model._meta.app_label}.{rel_model.__name__}"
            rel_rules   = FieldDisplayRule.objects.filter(model_label=rel_label)
            rel_rmap    = {r.field_name: r for r in rel_rules}
            rel_instance = rel_model()

            for sub in rel_model._meta.fields:
                if sub.name == "id":
                    continue

                # skip excluded
                rel_rule = rel_rmap.get(sub.name)
                if rel_rule and rel_rule.is_excluded:
                    continue

                # skip if user lacks perm on this subfield
                sub_field_name = f"{field.name}__{sub.name}"
                if user and not can_read_field(user, rel_instance, sub.name):
                    continue

                fields.append({
                    "name":      sub_field_name,
                    "label":     f"{field.verbose_name.title()} → {sub.verbose_name.title()}",
                    "mandatory": rel_rule.is_mandatory if rel_rule else False,
                    "editable":  False,
                })
        else:
            # normal field
            fields.append({
                "name":      field.name,
                "label":     field.verbose_name.title(),
                "mandatory": rule.is_mandatory if rule else False,
                "editable":  True,
            })

    return fields

@login_required
def column_config_view(request, table_name):
    # 1) Resolve table + model
    config      = get_object_or_404(TableViewConfig, table_name=table_name)
    model       = get_model_from_table(table_name)
    all_fields  = get_flat_fields(model, user=request.user)
    qs          = UserColumnConfig.objects.filter(user=request.user, table_config=config)

    # 2) Pick the config (from GET or POST)
    config_id   = request.POST.get("config_id") or request.GET.get("config")
    selected    = _select_item(qs, config_id)

    if request.method == "POST":
        # 3) Gather posted data
        data = {
            "fields":     request.POST.getlist("field_order[]"),
            "name":       request.POST.get("name", "Unnamed").strip(),
            "is_default": bool(request.POST.get("is_default")),
        }
        # 4) Update or create
        if selected:
            for k, v in data.items():
                setattr(selected, k, v)
            selected.save()
        else:
            UserColumnConfig.objects.create(
                user=request.user,
                table_config=config,
                **data
            )
        return redirect("layout_table_by_name", table_name=table_name)

    # 5) Set up context for GET
    selected_fields = selected.fields if selected else [f["name"] for f in all_fields]

    return render(request, "table_view/column_config.html", {
        "table_name":        table_name,
        "all_fields":        all_fields,
        "selected_fields":   selected_fields,
        "user_configs":      qs,
        "selected_config_id": selected.id if selected else "",
    })

@require_POST
@login_required
def delete_column_config(request, table_name, config_id):
    config = get_object_or_404(UserColumnConfig, id=config_id, user=request.user)
    config.delete()
    return redirect("layout_column_config", table_name=table_name)


# @login_required
# @require_POST
# def save_filter_by_name(request, table_name):
#     """
#     Expects JSON body { name: str, values: dict }.
#     Creates a new UserFilterConfig for the current user/table.
#     Returns { id, name } on success or { error } on failure.
#     """
#     # 1) Parse JSON
#     try:
#         payload = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({"error": "Invalid JSON"}, status=400)
#
#     name   = payload.get("name", "").strip()
#     print(name)
#     values = payload.get("values")
#     if not name or not isinstance(values, dict):
#         return JsonResponse({"error": "Must include non-empty 'name' and 'values' dict"}, status=400)
#
#     # 2) Lookup table config
#     config = get_object_or_404(TableViewConfig, table_name=table_name)
#
#     # 3) Create (or you could update if name exists)
#     ufc = UserFilterConfig.objects.create(
#         user=request.user,
#         table_config=config,
#         name=name,
#         values=values,
#         is_default=False,
#     )
#
#     # 4) Return the new ID & name
#     return JsonResponse({"id": ufc.id, "name": ufc.name})

@login_required
def filter_config_view(request, table_name):
    # 1) Lookup table + user’s existing filters
    table_conf   = get_object_or_404(TableViewConfig, table_name=table_name)
    user_filters = UserFilterConfig.objects.filter(
        user=request.user,
        table_config=table_conf
    )
    schema       = get_filter_schema(table_name, user=request.user)

    # 2) Pick the one we’re editing (if any)
    cfg_id  = request.POST.get("id") or request.GET.get("id")
    editing = _select_item(user_filters, cfg_id)

    if request.method == "POST":
        # 3) Gather form data
        data = {
            "name":       request.POST.get("name", "").strip() or "Unnamed",
            "is_default": bool(request.POST.get("is_default")),
            "values": {
                k: request.POST[k]
                for k in schema.keys()
                if request.POST.get(k)
            }
        }

        # 4) If new default, clear others
        if data["is_default"]:
            user_filters.update(is_default=False)

        # 5) Create or update
        if editing:
            for attr, val in data.items():
                setattr(editing, attr, val)
            editing.save()
        else:
            UserFilterConfig.objects.create(
                user=request.user,
                table_config=table_conf,
                **data
            )

        return redirect("layout_filter_config", table_name=table_name)

    # 6) Render with initial values
    return render(request, "table_view/filter_config.html", {
        "table_name":     table_name,
        "filter_schema":  schema,
        "user_filters":   user_filters,
        "editing":        editing,
        "initial_values": editing.values if editing else {},
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