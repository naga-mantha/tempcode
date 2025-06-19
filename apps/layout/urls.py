from django.urls import path
from .views import *

urlpatterns = [
    path('table/<str:table_name>/', table_by_name, name='layout_table_by_name'),
    path('table/<str:table_name>/data/', table_data_by_name, name='layout_table_data_by_name'),
    path('table/<str:table_name>/update/<int:pk>/', table_update_by_name, name='layout_table_update_by_name'),
    path('table/<str:table_name>/columns/', column_config_view, name='layout_column_config'),
    path("table/<str:table_name>/columns/delete/<int:config_id>/", delete_column_config, name="delete_column_config"),
    path("table/<str:table_name>/save_filter/",   save_filter_by_name,   name="layout_save_filter"),
    path("table/<str:table_name>/filters/",       filter_config_view,    name="layout_filter_config"),
    path("table/<str:table_name>/filters/<int:config_id>/delete/", delete_filter_config, name="layout_filter_delete"),
]
