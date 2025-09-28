from __future__ import annotations

from django.urls import path

from . import views
from apps_v2.blocks.tables.layouts_table import render_layouts_table
from apps_v2.blocks.tables.items_table import render_items_table


app_name = "blocks_v2"

urlpatterns = [
    path("hello", views.hello, name="hello"),
    path("render/<str:spec_id>", views.render_spec, name="render_spec"),
    path("data/<str:spec_id>", views.data_spec, name="data_spec"),
    path("choices/<str:spec_id>/<str:field>", views.choices_spec, name="choices_spec"),
    path("export/<str:spec_id>.<str:fmt>", views.export_spec, name="export_spec"),
    path("config/save/<str:spec_id>", views.save_table_config, name="save_table_config"),
    # Manage Filters
    path("manage-filters/<str:spec_id>", views.manage_filters, name="manage_filters"),
    path("filter/rename/<str:spec_id>/<int:config_id>", views.rename_filter_config, name="rename_filter_config"),
    path("filter/duplicate/<str:spec_id>/<int:config_id>", views.duplicate_filter_config, name="duplicate_filter_config"),
    path("filter/delete/<str:spec_id>/<int:config_id>", views.delete_filter_config, name="delete_filter_config"),
    path("filter/make_default/<str:spec_id>/<int:config_id>", views.make_default_filter_config, name="make_default_filter_config"),
    path("config/rename/<str:spec_id>/<int:config_id>", views.rename_table_config, name="rename_table_config"),
    path("config/duplicate/<str:spec_id>/<int:config_id>", views.duplicate_table_config, name="duplicate_table_config"),
    path("config/delete/<str:spec_id>/<int:config_id>", views.delete_table_config, name="delete_table_config"),
    path("config/make_default/<str:spec_id>/<int:config_id>", views.make_default_table_config, name="make_default_table_config"),
    path("filter/save/<str:spec_id>", views.save_filter_config, name="save_filter_config"),
    # Filter Layout (V2-native)
    path("filter-layout/<str:spec_id>", views.manage_filter_layout, name="manage_filter_layout"),
    path("filter-layout/default/<str:spec_id>", views.manage_filter_layout_default, name="manage_filter_layout_default"),
    path("filter-layout/save/<str:spec_id>", views.save_filter_layout, name="save_filter_layout"),
    path("filter-layout/save-default/<str:spec_id>", views.save_filter_layout_default, name="save_filter_layout_default"),
    path("manage/<str:spec_id>", views.manage_columns, name="manage_columns"),
    # Demo table block (V2)
    path("table/layouts", render_layouts_table, name="table_layouts"),
    path("table/items", render_items_table, name="table_items"),
]
