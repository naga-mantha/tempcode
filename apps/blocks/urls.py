from django.urls import path
import apps.blocks.blocks.table.views as table_views
from apps.blocks.views.inline_edit import InlineEditView
from apps.blocks.views.column_config import ColumnConfigView
from apps.blocks.views.filter_config import FilterConfigView

urlpatterns = [
    path("table/<str:block_name>/", table_views.render_table_block, name="render_table_block"),
    path("table/<str:block_name>/edit/", InlineEditView.as_view(), name="inline_edit"),
    path("table/<str:block_name>/columns/", ColumnConfigView.as_view(), name="column_config_view"),
    path(
        "table/<str:block_name>/filters/",
        FilterConfigView.as_view(),
        name="table_filter_config",
    ),
    path(
        "table/<str:block_name>/filters/<int:config_id>/delete/",
        table_views.filter_delete_view,
        name="table_filter_delete",
    ),
]
