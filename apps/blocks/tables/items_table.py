from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.blocks.specs import BlockSpec, Services
from apps.blocks.filters import (
    item_choices,
    item_group_choices,
    item_type_choices,
    multiselect_filter,
    text_filter,
)
from apps.blocks.models.item import Item
from apps.blocks.policy import PolicyService
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
        id="items.table",
        name="Items",
        kind="table",
        template="blocks/table/table.html",
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
    return render(request, "blocks/table/table.html", ctx)
