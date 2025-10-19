from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec

from django.urls import path

from . import views

app_name = "blocks"

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
    path("pivot/manage/<str:spec_id>", views.manage_pivot_configs, name="manage_pivot_configs"),
    path("pivot/save/<str:spec_id>", views.save_pivot_config, name="save_pivot_config"),
    path("pivot/rename/<str:spec_id>/<int:config_id>", views.rename_pivot_config, name="rename_pivot_config"),
    path("pivot/duplicate/<str:spec_id>/<int:config_id>", views.duplicate_pivot_config, name="duplicate_pivot_config"),
    path("pivot/delete/<str:spec_id>/<int:config_id>", views.delete_pivot_config, name="delete_pivot_config"),
    path("pivot/make_default/<str:spec_id>/<int:config_id>", views.make_default_pivot_config, name="make_default_pivot_config"),
]

# _OPTIONAL_ROUTES = (
#     ("apps.layout.tables.layouts_table", "render_layouts_table", "table/layouts", "table_layouts"),
#     ("apps.common.tables.items_table", "render_items_table", "table/items", "table_items"),
#     ("apps.common.pivots.items_pivot", "render_items_pivot", "pivot/items", "pivot_items"),
# )
#
# for module_path, attr_name, route, name in _OPTIONAL_ROUTES:
#     if find_spec(module_path) is None:
#         continue
#     module = import_module(module_path)
#     view = getattr(module, attr_name, None)
#     if view is None:
#         continue
#     urlpatterns.append(path(route, view, name=name))
