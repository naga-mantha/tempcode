from django.urls import path

from apps.layout import views

urlpatterns = [
    path("layout_list", views.LayoutListView.as_view(), name="layout_list"),
    path("<str:username>/<slug:slug>/", views.LayoutDetailView.as_view(), name="layout_detail"),
    path("<str:username>/<slug:slug>/rename/", views.LayoutRenameView.as_view(), name="layout_rename"),
    path("<str:username>/<slug:slug>/delete/", views.LayoutDeleteView.as_view(), name="layout_delete"),
    path("<str:username>/<slug:slug>/edit/", views.LayoutEditView.as_view(), name="layout_edit"),
    path("<str:username>/<slug:slug>/filters/", views.LayoutFilterConfigView.as_view(), name="layout_filter_config"),
    path("<str:username>/<slug:slug>/reorder/", views.LayoutReorderView.as_view(), name="layout_reorder"),
    path("<str:username>/<slug:slug>/grid/update/", views.LayoutGridUpdateView.as_view(), name="layout_grid_update"),
    path("<str:username>/<slug:slug>/block/<int:id>/update/", views.LayoutBlockUpdateView.as_view(), name="layout_block_update"),
    path("<str:username>/<slug:slug>/block/<int:id>/delete/", views.LayoutBlockDeleteView.as_view(), name="layout_block_delete"),
    path("<str:username>/<slug:slug>/block/add/", views.LayoutBlockAddView.as_view(), name="layout_block_add"),
]
