from django.urls import path

from apps.layout import views

urlpatterns = [
    path("layouts/", views.LayoutListView.as_view(), name="layout_list"),
    path("layouts/create/", views.LayoutCreateView.as_view(), name="layout_create"),
    path("layouts/<slug:slug>/", views.LayoutDetailView.as_view(), name="layout_detail"),
    path("layouts/<slug:slug>/delete/", views.LayoutDeleteView.as_view(), name="layout_delete"),
    path("layouts/<slug:slug>/add-block/", views.AddBlockView.as_view(), name="layout_add_block"),
    path(
        "layouts/<slug:slug>/filters/",
        views.LayoutFilterConfigView.as_view(),
        name="layout_filter_config",
    ),
]
