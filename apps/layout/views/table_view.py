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

def table_data_by_name(request, table_name):
    config = get_object_or_404(TableViewConfig, table_name=table_name)
    model = apps.get_model(*config.model_label.split('.'))
    queryset = model.objects.all()

    # -------------------------------
    # Apply filter
    filter_id = request.GET.get("filter")
    filter_obj = None
    if request.user.is_authenticated:
        filters_qs = UserFilterConfig.objects.filter(user=request.user, table_config=config)
        if filter_id:
            try:
                filter_obj = filters_qs.get(id=filter_id)
            except UserFilterConfig.DoesNotExist:
                filter_obj = None
        if not filter_obj:
            filter_obj = filters_qs.filter(is_default=True).first()

        if filter_obj:
            schema = get_filter_schema(table_name)
            for key, value in filter_obj.values.items():
                if key in schema and callable(schema[key].get("handler")):
                    queryset = schema[key]["handler"](queryset, value)

    # -------------------------------
    # Pick fields to return
    selected_config_id = request.GET.get("config")
    if selected_config_id:
        user_config = UserColumnConfig.objects.filter(
            user=request.user,
            table_config=config,
            id=selected_config_id
        ).first()
    else:
        user_config = UserColumnConfig.objects.filter(
            user=request.user,
            table_config=config,
            is_default=True
        ).first()

    if user_config:
        field_names = user_config.fields
        print(field_names)
    else:
        field_names = [f["name"] for f in get_flat_fields(model)]

    field_names = [f.replace(".", "__") for f in field_names]
    if "id" not in field_names:
        field_names.insert(0, "id")

    # DO NOT RESET queryset here — this was your issue
    data = list(queryset.values(*field_names))

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