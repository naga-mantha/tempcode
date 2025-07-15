import json
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.apps import apps
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from apps.layout.models import TableViewConfig, UserColumnConfig, FieldDisplayRule, UserFilterConfig
from apps.layout.filter_registry import get_filter_schema
from apps.workflow.views.permissions import can_read_field
from apps.workflow.models.workflow_model import WorkflowModel
from apps.layout.helpers.get_model_from_table import get_model_from_table
from apps.layout.helpers.get_column_labels import get_column_labels
from apps.layout.helpers.api_helpers import get_filtered_queryset

def _collect_filters(request, config):
    filters = {}

    if fid := request.GET.get("filter"):
        ufc = get_object_or_404(UserFilterConfig, id=fid, user=request.user, table_config=config)
        filters.update(ufc.values)

    # Merge in any other non-empty GET params (excluding filter+config)
    for k, v in request.GET.items():
        if k in ("filter", "config") or not v:
            continue
        filters[k] = v

    return filters

def _select_item(queryset, selected_id, fallback=None):
    """
    Given a queryset and a selected_id, returns:
      - the object with that id, if present
      - else the first where is_default=True
      - else the provided fallback
    Special: if selected_id is None or empty-string, immediately return fallback.
    """
    # Blank or missing selection → new config
    if selected_id in (None, ""):
        return fallback

    # Try to load what user asked for
    try:
        obj = queryset.get(id=int(selected_id))
        return obj
    except (ValueError, queryset.model.DoesNotExist):
        pass

    # They asked for something invalid → fall back to your “default” config, if any
    default = queryset.filter(is_default=True).first()
    if default:
        return default

    # No default either → truly new
    return fallback

@login_required
def table_by_name(request, table_name):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model = get_model_from_table(table_name)

    # --- Column config ---
    col_qs = UserColumnConfig.objects.filter(user=request.user, table_config=config)
    # find your “default” view (or None)
    default_col = col_qs.filter(is_default=True).first()
    # if no ?config=… then _select_item will return default_col
    col = _select_item(col_qs, request.GET.get("config"), fallback=default_col)

    all_fields = get_flat_fields(model, user=request.user)
    # — overwrite each "label" with our verbose/unique names —
    field_names = [f["name"] for f in all_fields]
    labels_map  = get_column_labels(model, field_names)
    for f in all_fields:
        f["label"] = labels_map[f["name"]]

    # Safely pick the names to render
    if col and col.fields:
        selected_names = col.fields
    else:
        # no saved config → render every field
        selected_names = [f["name"] for f in all_fields]

    # Build your ordered field list
    fields = [
        f
        for name in selected_names
        for f in all_fields
        if f["name"] == name
    ]

    # --- Filter config (explicit empty = no filter, else default fallback) ---
    filt_qs = UserFilterConfig.objects.filter(user=request.user, table_config=config)
    default_filt = filt_qs.filter(is_default=True).first()
    raw_filter = request.GET.get("filter")
    if raw_filter == "":  # user explicitly chose “None”
        filt = None
    else:
        # no param (None) or invalid ID → fallback to default_filt
        filt = _select_item(filt_qs, raw_filter, fallback=default_filt)

    filter_schema = get_filter_schema(table_name, user=request.user)
    selected_values = filt.values if filt else {}

    return render(request, "table_view/table.html", {
        "app_label": config.model_label.split(".")[0],
        "model_name": config.model_label.split(".")[1],
        "table_name": table_name,
        "fields": fields,
        "title": config.title or model.__name__,
        "tabulator_options": config.tabulator_options,

        # column config
        "user_configs": col_qs,
        "active_config_id": col.id if col else None,

        # filter config
        "filter_configs": filt_qs,
        "active_filter_id": filt.id if filt else None,
        "filter_schema": filter_schema,
        "selected_filter_values": selected_values,
    })
@login_required
def table_data_by_name(request, table_name):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model  = get_model_from_table(table_name)

    # apply filters
    filters = _collect_filters(request, config)
    qs, _ = get_filtered_queryset(
        user=request.user,
        model=model,
        table_name=table_name,
        filters=filters,
    )

    # build the full list of FK‐expanded field paths
    all_fields  = get_flat_fields(model, user=request.user)
    field_paths = [f["name"] for f in all_fields]

    # **ensure the PK is always present in your JSON**
    pk_name = model._meta.pk.name
    if pk_name not in field_paths:
        field_paths.insert(0, pk_name)

    # pick user's saved config or use all fields
    cid = request.GET.get("config")
    if cid:
        ucc = get_object_or_404(
            UserColumnConfig,
            id=cid,
            user=request.user,
            table_config=config
        )
        # filter to only valid paths, but keep the PK
        selected_paths = [p for p in ucc.fields if p in field_paths]
        if pk_name not in selected_paths:
            selected_paths.insert(0, pk_name)
    else:
        selected_paths = field_paths

    # now every row dict will include {'id': ..., <other fields>: ...}
    return JsonResponse(list(qs.values(*selected_paths)), safe=False)


import logging
logger = logging.getLogger(__name__)

@login_required
@require_POST
def table_update_by_name(request, table_name, pk):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model  = apps.get_model(*config.model_label.split('.'))
    obj    = get_object_or_404(model, pk=pk)

    # record-level permission
    if hasattr(obj, "can_edit") and not obj.can_edit(request.user):
        return JsonResponse({
            "success": False,
            "error": "You don’t have permission to edit this record."
        }, status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError as e:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON payload"
        }, status=400)

    # field-level checks
    for field_name, new_value in payload.items():
        if hasattr(obj, "can_edit_field") and not obj.can_edit_field(request.user, field_name):
            return JsonResponse({
                "success": False,
                "error": f"You cannot edit '{field_name}' in this state."
            }, status=403)
        setattr(obj, field_name, new_value)

    # attempt save and catch *any* exception
    try:
        obj.save()
    except Exception as e:
        logger.exception("Error saving model in inline edit")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)

    return JsonResponse({"success": True})
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
        rule = rule_map.get(field.name)
        if rule and rule.is_excluded:
            continue

        if user and not can_read_field(user, instance, field.name):
            continue

        if isinstance(field, models.ForeignKey):
            # expand FK subfields
            rel_model = field.remote_field.model
            rel_label = f"{rel_model._meta.app_label}.{rel_model.__name__}"
            rel_rules = FieldDisplayRule.objects.filter(model_label=rel_label)
            rel_rmap = {r.field_name: r for r in rel_rules}
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
                    "name": sub_field_name,
                    "label": f"{sub.verbose_name}",
                    "mandatory": rel_rule.is_mandatory if rel_rule else False,
                    "editable": False,
                })
        else:
            # normal field
            fields.append({
                "name": field.name,
                "label": field.verbose_name.title(),
                "mandatory": rule.is_mandatory if rule else False,
                "editable": True,
            })

    return fields

@login_required
def column_config_view(request, table_name):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model = get_model_from_table(table_name)
    all_fields = get_flat_fields(model, user=request.user)
    # — make our UI‐friendly labels —
    field_names = [f["name"] for f in all_fields]
    labels_map  = get_column_labels(model, field_names)
    for f in all_fields:
        f["label"] = labels_map[f["name"]]


    qs = UserColumnConfig.objects.filter(user=request.user, table_config=config)

    # Pick the config (from GET or POST)
    config_id = request.POST.get("config_id") or request.GET.get("config") or None
    selected = _select_item(qs, config_id)

    if request.method == "POST":
        name = request.POST.get("name").strip()
        if name == "":
            messages.error(request,  "Name is mandatory"
            )
            return redirect("layout_column_config", table_name=table_name)


        # Gather posted data
        data = {
            "fields": request.POST.getlist("field_order[]"),
            "name": name,
            "is_default": bool(request.POST.get("is_default")),
        }
        # Update or create
        if selected:
            for k, v in data.items():
                setattr(selected, k, v)
            selected.save()
        else:
            UserColumnConfig.objects.create(user=request.user, table_config=config, **data)

        return redirect("layout_table_by_name", table_name=table_name)

    # Set up context for GET
    # selected_fields = selected.fields if selected else [f["name"] for f in all_fields]
    if selected:
        selected_fields = selected.fields
    else:
        # pre-select only the mandatory ones
        selected_fields = [
            f["name"]
            for f in all_fields
            if f.get("mandatory")
        ]

    ordered_fields = [
                         f for name in selected_fields
                         for f in all_fields
                         if f["name"] == name
                     ] + [
                         f for f in all_fields
                         if f["name"] not in selected_fields
                     ]

    instructions = [
        "Choose an existing view to modify it or select 'New View' to create a new one.",
        "Choose the columns that you would like to be displayed in the table.",
        "Drag and drop the columns in the desired order.",
        "Some fields are mandatory for the app to work. These fields are marked as (mandatory) and cannot be unselected. However the order can be changed.",
        "Choose 'Set as Default' at the bottom of the page, if you would like this to be the default view for the table"
    ]

    return render(request, "table_view/column_config.html", {
        "table_name": table_name,
        "all_fields": ordered_fields,
        "selected_fields": selected_fields,
        "user_configs": qs,
        "selected_config_id": selected.id if selected else "",
        "title": config.title,
        "instructions": instructions
    })

@require_POST
@login_required
def delete_column_config(request, table_name, config_id):
    table_cfg = get_object_or_404(TableViewConfig, table_name=table_name)
    qs = UserColumnConfig.objects.filter(
        user=request.user,
        table_config=table_cfg
    )
    cfg = get_object_or_404(UserColumnConfig, id=config_id, user=request.user)

    if request.method == "POST":
        # If there's exactly one configuration, block deletion
        if qs.count() == 1:
            messages.error(request,
                "Atleast one view must be present. Please create a new one before deleting this one."
            )
            return redirect("layout_column_config", table_name=table_name)

        # If deleting the default and there are other configs, promote the oldest (or first) other config to default.
        if cfg.is_default:
            new_def = qs.exclude(id=cfg.id).order_by("pk").first()
            if new_def:
                new_def.is_default = True
                new_def.save()

        cfg.delete()
        messages.success(request, f"Configuration “{cfg.name}” deleted.")
        return redirect("layout_column_config", table_name=table_name)

@login_required
def filter_config_view(request, table_name):
    table_conf = get_object_or_404(TableViewConfig, table_name=table_name)
    user_filters = UserFilterConfig.objects.filter(user=request.user, table_config=table_conf)
    schema = get_filter_schema(table_name, user=request.user)

    # Pick the one we’re editing (if any)
    cfg_id = request.POST.get("id") or request.GET.get("id")
    editing = _select_item(user_filters, cfg_id)

    if request.method == "POST":
        # Gather form data
        data = {
            "name": request.POST.get("name", "").strip() or "Unnamed",
            "is_default": bool(request.POST.get("is_default")),
            "values": {
                k: request.POST[k]
                for k in schema.keys()
                if request.POST.get(k)
            }
        }

        # Create or update
        if editing:
            for attr, val in data.items():
                setattr(editing, attr, val)
            editing.save()
        else:
            UserFilterConfig.objects.create(user=request.user, table_config=table_conf, **data)

        return redirect("layout_filter_config", table_name=table_name)

    instructions = [
        "Choose an existing filter to modify it or select 'New Filter' to create a new one",
        "Click on the 'Filter Conditions' panel to open up the available filter fields.",
        "Enter desired values in the fields (Leave blank if a field doesnt need to be filtered)",
        "Choose 'Set as Default' if you would like this to be the default filter for the table"
    ]

    # Render with initial values
    return render(request, "table_view/filter_config.html", {
        "table_name": table_name,
        "filter_schema": schema,
        "user_filters": user_filters,
        "editing": editing,
        "initial_values": editing.values if editing else {},
        "title": table_conf.title,
        "instructions": instructions
    })

@login_required
@require_POST
def delete_filter_config(request, table_name, config_id):
    """
    Deletes one saved filter and redirects back to the config list.
    """
    ufc = get_object_or_404(UserFilterConfig, id=config_id, user=request.user, table_config__table_name=table_name)
    ufc.delete()

    return redirect("layout_filter_config", table_name=table_name)