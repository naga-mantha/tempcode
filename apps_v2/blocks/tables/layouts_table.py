from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.layout.models import Layout
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


"""V2 Layouts table spec using schema-driven services (no hard-coded filters).

This file defines only the spec and the demo render view.
"""


@dataclass(frozen=True)
class LayoutsTableSpec:
    spec = BlockSpec(
        id="v2.layouts.table",
        name="Layouts",
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
        category="System",
        description="User's layouts listing (V2 table via schema-driven services).",
        model=Layout,
        filter_schema=[
            {"key": "visibility", "field": "visibility", "type": "select", "choices": [
                {"value": Layout.VISIBILITY_PRIVATE, "label": "Private"},
                {"value": Layout.VISIBILITY_PUBLIC, "label": "Public"},
            ]},
            {"key": "name", "field": "name", "type": "text", "lookup": "icontains"},
            {"key": "category", "field": "category", "type": "text", "lookup": "icontains"},
            {"key": "categories", "field": "category", "type": "multiselect"},
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
    )


@login_required
def render_layouts_table(request: HttpRequest) -> HttpResponse:
    policy = PolicyService()
    controller = BlockController(LayoutsTableSpec.spec, policy)
    ctx = controller.build_context(request)
    # Customize title for demo clarity
    ctx["title"] = "Layouts (V2 Table)"
    return render(request, "v2/blocks/table/table.html", ctx)
