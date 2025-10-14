from __future__ import annotations

from django.urls import path
from . import views


app_name = "layout_v2"

urlpatterns = [
    path("ping", views.ping, name="ping"),
    path("", views.layout_list, name="layout_list_v2"),  # redirects to v1
    path("<str:username>/<slug:slug>/", views.layout_detail, name="layout_detail_v2"),  # redirects to v1
    path("create", views.layout_create, name="layout_create_v2"),  # redirects to v1
    path("<str:username>/<slug:slug>/edit", views.layout_edit, name="layout_edit_v2"),  # redirects to v1
    path("<str:username>/<slug:slug>/filters/save", views.save_layout_filter_config, name="layout_save_filter_v2"),
    path("<str:username>/<slug:slug>/filters/manage", views.manage_layout_filters, name="layout_manage_filters_v2"),
    path("<str:username>/<slug:slug>/filters/rename/<int:config_id>", views.rename_layout_filter_config, name="layout_rename_filter_v2"),
    path("<str:username>/<slug:slug>/filters/duplicate/<int:config_id>", views.duplicate_layout_filter_config, name="layout_duplicate_filter_v2"),
    path("<str:username>/<slug:slug>/filters/delete/<int:config_id>", views.delete_layout_filter_config, name="layout_delete_filter_v2"),
    path("<str:username>/<slug:slug>/filters/make-default/<int:config_id>", views.make_default_layout_filter_config, name="layout_make_default_filter_v2"),
    path("<str:username>/<slug:slug>/design", views.layout_edit, name="layout_design_v2"),  # redirect to v1 edit
    path("<str:username>/<slug:slug>/grid/update", views.layout_grid_update_v2, name="layout_grid_update_v2"),
    path("<str:username>/<slug:slug>/block/add", views.layout_block_add_v2, name="layout_block_add_v2"),
    path("<str:username>/<slug:slug>/block/<int:lb_id>/delete", views.layout_block_delete_v2, name="layout_block_delete_v2"),
    path("<str:username>/<slug:slug>/block/<int:lb_id>/render", views.layout_block_render_v2, name="layout_block_render_v2"),
    path("<str:username>/<slug:slug>/block/<int:lb_id>/update", views.layout_block_update_v2, name="layout_block_update_v2"),
    path("<str:username>/<slug:slug>/block/<int:lb_id>/configs", views.layout_block_configs_v2, name="layout_block_configs_v2"),
]

