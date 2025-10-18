from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.layout.models import Layout
from apps.blocks.specs import BlockSpec, Services
from apps.blocks.policy import PolicyService
from apps.blocks.controller import BlockController
from apps.blocks.services.model_table import (
    SchemaFilterResolver,
    ModelQueryBuilder,
    ModelColumnResolver,
    ModelSerializer,
)
from apps.blocks.services.export_options import DefaultExportOptions
from apps.common.filters.schemas import text_filter, multiselect_filter


"""V2 Layouts table spec using schema-driven services (no hard-coded filters).

This file defines only the spec and the demo render view.
"""


@dataclass(frozen=True)
class LayoutsTableSpec:
    spec = BlockSpec(
        id="layouts.table",
        name="Layouts",
        kind="table",
        template="blocks/table/table.html",
        supported_features=("filters",),
        services=Services(
            filter_resolver=SchemaFilterResolver,
            column_resolver=ModelColumnResolver,
            query_builder=ModelQueryBuilder,
            serializer=ModelSerializer,
            export_options=DefaultExportOptions,
        ),
        category="System",
        description="User's layouts listing (V2 table via schema-driven services).",
        model=Layout,
        filter_schema=[
            {"key": "visibility", "field": "visibility", "type": "select", "choices": [
                {"value": Layout.VISIBILITY_PRIVATE, "label": "Private"},
                {"value": Layout.VISIBILITY_PUBLIC, "label": "Public"},
            ]},
            dict({"key": "name"}, **text_filter("name", label="Name")),
            dict({"key": "category"}, **text_filter("category", label="Category")),
            dict({"key": "categories"}, **multiselect_filter("category", label="Categories")),
            {"key": "created_from", "field": "created_at__date", "type": "date", "lookups": {"created_from": "created_at__date__gte"}},
            {"key": "created_to", "field": "created_at__date", "type": "date", "lookups": {"created_to": "created_at__date__lte"}},
        ],
        column_max_depth=0,
        table_options={
            "pagination": True,
            "paginationMode": "remote",
            "paginationSize": 10,
            "paginationSizeSelector": [10, 25, 50, 100],
            "movableColumns": True,
            "layout": "fitColumns",
        },
        download_options={
            "excel": {
                "filename": "layouts.xlsx",
                "sheetName": "Layouts",
            },
            "pdf": {
                "filename": "layouts.pdf",
                "orientation": "portrait",
                "title": "Layouts",
            },
        },
    )


@login_required
def render_layouts_table(request: HttpRequest) -> HttpResponse:
    policy = PolicyService()
    controller = BlockController(LayoutsTableSpec.spec, policy)
    ctx = controller.build_context(request)
    # Customize title for demo clarity
    ctx["title"] = "Layouts (V2 Table)"
    return render(request, "blocks/table/table.html", ctx)
