from django.urls import path
from .views import *
from .tables import *

urlpatterns = [
    path('', home, name='home'),
    path('todos/', todo_list, name='todo_list'),
    path('todos/reorder/', todo_reorder, name='todo_reorder'),
    path('roadmap/', roadmap_list, name='roadmap_list'),

    path('roadmap/', roadmap_list, name='roadmap_list'),
    path('blocks/table/items', render_items_table, name='table_items'),
]
