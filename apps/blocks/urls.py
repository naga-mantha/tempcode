from __future__ import annotations

from django.urls import path

from . import views
from .views import layouts as layout_views

app_name = "blocks"

urlpatterns = [
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
    # Filter Layout
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
urlpatterns += [
    # Layouts
    path(
        "layouts/",
        layout_views.LayoutListView.as_view(),
        name="layout_list",
    ),
    path(
        "layouts/create/",
        layout_views.LayoutCreateView.as_view(),
        name="layout_create",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/",
        layout_views.LayoutDetailView.as_view(),
        name="layout_detail",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/edit/",
        layout_views.LayoutEditView.as_view(),
        name="layout_edit",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/delete/",
        layout_views.LayoutDeleteView.as_view(),
        name="layout_delete",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/filters/manage/",
        layout_views.LayoutFilterManageView.as_view(),
        name="layout_manage_filters",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/filters/save/",
        layout_views.LayoutFilterConfigSaveView.as_view(),
        name="layout_filter_config_save",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/filters/<int:config_id>/rename/",
        layout_views.LayoutFilterConfigRenameView.as_view(),
        name="layout_filter_config_rename",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/filters/<int:config_id>/duplicate/",
        layout_views.LayoutFilterConfigDuplicateView.as_view(),
        name="layout_filter_config_duplicate",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/filters/<int:config_id>/delete/",
        layout_views.LayoutFilterConfigDeleteView.as_view(),
        name="layout_filter_config_delete",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/filters/<int:config_id>/make-default/",
        layout_views.LayoutFilterConfigMakeDefaultView.as_view(),
        name="layout_filter_config_make_default",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/filters/panel/",
        layout_views.LayoutFilterPanelView.as_view(),
        name="layout_filter_panel",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/blocks/add/",
        layout_views.LayoutBlockAddView.as_view(),
        name="layout_block_add",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/blocks/update/",
        layout_views.LayoutBlockUpdateView.as_view(),
        name="layout_block_update",
    ),
    path(
        "layouts/<str:username>/<slug:slug>/blocks/<slug:block_slug>/remove/",
        layout_views.LayoutBlockRemoveView.as_view(),
        name="layout_block_remove",
    ),
]
