from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.common.models.items import Item
from apps.blocks.specs import BlockSpec, Services
from apps.common.filters.schemas import text_filter, multiselect_filter
from apps.common.filters.item_groups import item_group_choices
from apps.common.filters.item_types import item_type_choices
from apps.common.filters.items import item_choices
from apps.policy.service import PolicyService
from apps.blocks.controller import BlockController
from apps.blocks.services.model_table import (
    SchemaFilterResolver,
    ModelQueryBuilder,
    ModelColumnResolver,
    ModelSerializer,
)
from apps.blocks.services.export_options import DefaultExportOptions
from apps.blocks.services.model_table import ModelQueryBuilder as BaseQueryBuilder

# This class is used to pre-filter the queryset if needed. For ex: Open PO only
class ActiveItemsQueryBuilder(BaseQueryBuilder):
    def get_queryset(self, filters):
        qs = super().get_queryset(filters)
        return qs.filter(code='MS15795-817B')  # or whatever condition you need
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
            # query_builder=ActiveItemsQueryBuilder,  # Use the custom query builder, in case we have to pre-filter
            serializer=ModelSerializer,
            export_options=DefaultExportOptions,
        ),
        category="Master Data",
        description="Items listing (V2 table via schema-driven services).",
        model=Item,
        filter_schema=[
            dict({"key": "code"}, **{**multiselect_filter("code", label="Item Codes", choices_func=item_choices), "min_query_length": 0}),
            dict({"key": "description"}, **text_filter("description", label="Description")),
            dict({"key": "item_group_codes"}, **{**multiselect_filter("item_group__code", label="Item Groups", choices_func=item_group_choices), "min_query_length": 0}),
            dict({"key": "item_type_codes"}, **{**multiselect_filter("type__code", label="Item Types", choices_func=item_type_choices), "min_query_length": 0}),
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
        download_options={
            "excel": {
                "filename": "items.xlsx",
                "sheetName": "Items",
            },
            "pdf": {
                "filename": "items.pdf",
                "orientation": "landscape",
                "title": "Items",
            },
        },
    )


@login_required
def render_items_table(request: HttpRequest) -> HttpResponse:
    policy = PolicyService()
    controller = BlockController(ItemsTableSpec.spec, policy)
    ctx = controller.build_context(request)
    ctx["title"] = "Items (V2 Table)"
    return render(request, "v2/blocks/table/table.html", ctx)
