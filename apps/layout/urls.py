from django.urls import path
from .views import *

urlpatterns = [
    path('table/<str:table_name>/', table_by_name, name='layout_table_by_name'),
    path('table/<str:table_name>/data/', table_data_by_name, name='layout_table_data_by_name'),
    path('table/<str:table_name>/update/<int:pk>/', table_update_by_name, name='layout_table_update_by_name'),
    path('table/<str:table_name>/columns/', column_config_view, name='layout_column_config'),
    path("table/<str:table_name>/columns/delete/<int:config_id>/", delete_column_config, name="delete_column_config"),
]