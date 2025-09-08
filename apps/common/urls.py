from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('todos/', todo_list, name='todo_list'),
    path('todos/reorder/', todo_reorder, name='todo_reorder'),
]
