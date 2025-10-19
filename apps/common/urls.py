from django.urls import path

from .tables import render_items_table
from .views import home, roadmap_list, todo_list, todo_reorder

urlpatterns = [
    path('', home, name='home'),
    path('todos/', todo_list, name='todo_list'),
    path('todos/reorder/', todo_reorder, name='todo_reorder'),
    path('roadmap/', roadmap_list, name='roadmap_list'),
    path('blocks/table/items', render_items_table, name='table_items'),
]
