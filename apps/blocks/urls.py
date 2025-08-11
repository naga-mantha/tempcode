from django.urls import path
import apps.blocks.blocks.table.views as table_views

urlpatterns = [
    path("table/<str:block_name>/", table_views.render_table_block, name="render_table_block"),
    path("table/<str:block_name>/edit/", table_views.inline_edit, name="inline_edit"),
    path("table/<str:block_name>/columns/", table_views.column_config_view, name="column_config_view"),
path(
        "table/<str:block_name>/filters/",
        table_views.filter_config_view,
        name="table_filter_config",
    ),
    path(
        "table/<str:block_name>/filters/<int:config_id>/delete/",
        table_views.filter_delete_view,
        name="table_filter_delete",
    ),
]