from django.urls import path

from apps.layout import views

urlpatterns = [
    path("", views.LayoutListView.as_view(), name="layout_list"),
    path("create/", views.LayoutCreateView.as_view(), name="layout_create"),
    path("<str:username>/<slug:slug>/", views.LayoutDetailView.as_view(), name="layout_detail"),
    path("<str:username>/<slug:slug>/delete/", views.LayoutDeleteView.as_view(), name="layout_delete"),
    path("<str:username>/<slug:slug>/edit/", views.LayoutEditView.as_view(), name="layout_edit"),
    path("<str:username>/<slug:slug>/add-block/", views.AddBlockView.as_view(), name="layout_add_block"),
    path(
        "<str:username>/<slug:slug>/filters/",
        views.LayoutFilterConfigView.as_view(),
        name="layout_filter_config",
    ),
]
