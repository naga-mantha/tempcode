from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.common.models.items import Item
from apps_v2.blocks.specs import BlockSpec, Services
from apps_v2.policy.service import PolicyService
from apps_v2.blocks.controller import BlockController
from apps_v2.blocks.services.model_table import (
    SchemaFilterResolver,
    ModelQueryBuilder,
    ModelColumnResolver,
    ModelSerializer,
)
from apps_v2.blocks.services.export_options import DefaultExportOptions


@dataclass(frozen=True)
class ItemsTableSpec:
    spec = BlockSpec(
        id="v2.items.table",
        name="Items",
        kind="table",
        template="v2/blocks/table/table.html",
        supported_features=("filters",),
        services=Services(
            filter_resolver=SchemaFilterResolver,
            column_resolver=ModelColumnResolver,
            query_builder=ModelQueryBuilder,
            serializer=ModelSerializer,
            export_options=DefaultExportOptions,
        ),
        category="Master Data",
        description="Items listing (V2 table via schema-driven services).",
        model=Item,
        filter_schema=[
            {"key": "code", "field": "code", "type": "text", "lookup": "icontains", "label": "Code"},
            {"key": "description", "field": "description", "type": "text", "lookup": "icontains", "label": "Description"},
            {"key": "item_group_codes", "field": "item_group__code", "type": "multiselect", "label": "Item Groups"},
            {"key": "item_type_codes", "field": "type__code", "type": "multiselect", "label": "Item Types"},
        ],
        column_max_depth=20,
        table_options={
            "pagination": True,
            "paginationMode": "remote",
            "paginationSize": 10,
            "paginationSizeSelector": [10, 25, 50, 100],
            "movableColumns": True,
            "layout": "fitColumns",
            "placeholder": "No items",
        },
    )


@login_required
def render_items_table(request: HttpRequest) -> HttpResponse:
    policy = PolicyService()
    controller = BlockController(ItemsTableSpec.spec, policy)
    ctx = controller.build_context(request)
    ctx["title"] = "Items (V2 Table)"
    return render(request, "v2/blocks/table/table.html", ctx)
