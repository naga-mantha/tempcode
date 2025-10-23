from django.urls import path
from django_bi.blocks.views import table as table_views
from django_bi.blocks.views import chart as chart_views
from django_bi.blocks.views import pivot as pivot_views
from django_bi.blocks.views.pivot_config import PivotConfigView
from django_bi.blocks.views.pivot_filter_config import PivotFilterConfigView
from django_bi.blocks.views.inline_edit import InlineEditView
from django_bi.blocks.views.column_config import ColumnConfigView
from django_bi.blocks.views.filter_config import FilterConfigView, ChartFilterConfigView
from django_bi.blocks.views.filter_choices import FilterChoicesView
from django_bi.blocks.views.filter_layout import FilterLayoutView, AdminFilterLayoutView

app_name = "blocks"

urlpatterns = [
    path("table/<str:block_name>/", table_views.render_table_block, name="render_table_block"),
    path("table/<str:block_name>/edit/", InlineEditView.as_view(), name="inline_edit"),
    path("table/<str:block_name>/columns/", ColumnConfigView.as_view(), name="column_config_view"),
    path("table/<str:block_name>/filters/", FilterConfigView.as_view(), name="table_filter_config"),
    path(
        "table/<str:block_name>/filters/<int:config_id>/delete/",
        table_views.filter_delete_view,
        name="table_filter_delete",
    ),
    path("chart/<str:block_name>/", chart_views.render_chart_block, name="render_chart_block"),
    path(
        "chart/<str:block_name>/filters/",
        ChartFilterConfigView.as_view(),
        name="chart_filter_config",
    ),
    path(
        "chart/<str:block_name>/filters/<int:config_id>/delete/",
        chart_views.filter_delete_view,
        name="chart_filter_delete",
    ),
    path(
        "filter-options/<str:block_name>/<str:key>/",
        FilterChoicesView.as_view(),
        name="block_filter_choices",
    ),
    path("pivot/<str:block_name>/", pivot_views.render_pivot_block, name="render_pivot_block"),
    path(
        "pivot/<str:block_name>/settings/",
        PivotConfigView.as_view(),
        name="pivot_config_view",
    ),
    path(
        "pivot/<str:block_name>/filters/",
        PivotFilterConfigView.as_view(),
        name="pivot_filter_config",
    ),
    # Filter layout (per-user)
    path(
        "filter-layout/<str:block_name>/",
        FilterLayoutView.as_view(),
        name="filter_layout_view",
    ),
    path(
        "filter-layout-template/<str:block_name>/",
        AdminFilterLayoutView.as_view(),
        name="admin_filter_layout_view",
    ),
]
