from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.common.models.items import Item
from apps.common.filters.schemas import text_filter, multiselect_filter
from apps.common.filters.items import item_choices
from apps.common.filters.item_groups import item_group_choices
from apps.common.filters.item_types import item_type_choices

from apps.blocks.specs import BlockSpec, Services
from apps.blocks.controller import BlockController
from apps.blocks.services.model_table import (
    SchemaFilterResolver,
    ModelQueryBuilder,
    ModelColumnResolver,
)
from apps.blocks.services.pivot_table import DefaultPivotEngine
from apps.policy.service import PolicyService


@dataclass(frozen=True)
class ItemsPivotSpec:
    spec = BlockSpec(
        id="items.pivot",
        name="Items Pivot",
        kind="pivot",
        template="blocks/pivot/pivot.html",
        supported_features=("filters", "export"),
        services=Services(
            filter_resolver=SchemaFilterResolver,
            column_resolver=ModelColumnResolver,
            query_builder=ModelQueryBuilder,
            pivot_engine=DefaultPivotEngine,
        ),
        category="Master Data",
        description="Pivot view over items with saved schemas and filters.",
        model=Item,
        filter_schema=[
            dict({"key": "code"}, **{**multiselect_filter("code", label="Item Codes", choices_func=item_choices), "min_query_length": 0}),
            dict({"key": "description"}, **text_filter("description", label="Description")),
            dict({"key": "item_group_codes"}, **{**multiselect_filter("item_group__code", label="Item Groups", choices_func=item_group_choices), "min_query_length": 0}),
            dict({"key": "item_type_codes"}, **{**multiselect_filter("type__code", label="Item Types", choices_func=item_type_choices), "min_query_length": 0}),
        ],
        column_max_depth=2,
        table_options={
            "layout": "fitDataFill",
            "pagination": True,
            "paginationMode": "local",
            "paginationSize": 20,
            "paginationSizeSelector": [10, 20, 50, 100],
        },
        download_options={
            "excel": {
                "filename": "items-pivot.xlsx",
                "sheetName": "Pivot",
            },
            "pdf": {
                "filename": "items-pivot.pdf",
                "orientation": "landscape",
                "title": "Items Pivot",
            },
        },
    )


@login_required
def render_items_pivot(request: HttpRequest) -> HttpResponse:
    policy = PolicyService()
    controller = BlockController(ItemsPivotSpec.spec, policy)
    ctx = controller.build_context(request)
    ctx["title"] = "Items Pivot (V2)"
    return render(request, "blocks/pivot/pivot.html", ctx)

